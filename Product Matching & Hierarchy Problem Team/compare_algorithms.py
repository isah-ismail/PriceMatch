"""Evaluate matching methods against manually labelled iPhone pairs."""

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer

from matching_rules import (
    ROOT,
    RESULTS,
    VERSION,
    THRESHOLD,
    attribute_decision,
    clean_name,
    extract_model,
    hybrid_decision,
    load_specs,
    normalize,
    product_identity,
    read_csv,
    text,
)


DEFAULT_MANUAL = (
    ROOT / "data" / "manual" / "phone_pairs_manual.csv"
)

ALLOWED_LABELS = {
    "same",
    "different",
    "comparable",
    "unsure",
}


def load_manual(path):
    """Read the existing CSV or the Comparison sheet of an Excel file."""
    if not path.exists():
        raise FileNotFoundError(f"Manual comparison file not found: {path}")

    if path.suffix.lower() == ".xlsx":
        pairs = pd.read_excel(
            path,
            sheet_name="Comparison",
            dtype=str,
            keep_default_na=False,
        )
    else:
        pairs = read_csv(path)

    pairs = pairs.rename(columns={
        "Pair ID": "pair_id",
        "Beymen phone": "beymen_name",
        "Pozitif phone": "pozitif_name",
        "Label": "manual_label",
        "Reason": "manual_reason",
    })

    required = {
        "pair_id",
        "beymen_name",
        "pozitif_name",
        "manual_label",
    }

    missing = required - set(pairs.columns)
    if missing:
        raise ValueError(
            f"Manual file missing columns: {sorted(missing)}"
        )

    pairs["pair_id"] = pairs["pair_id"].map(text)

    if pairs["pair_id"].eq("").any():
        raise ValueError("Manual file contains blank pair IDs")

    if pairs["pair_id"].duplicated().any():
        raise ValueError("Manual pair IDs must be unique")

    pairs["manual_label"] = pairs["manual_label"].map(normalize)

    invalid = set(pairs["manual_label"]) - ALLOWED_LABELS
    if invalid:
        raise ValueError(
            f"Unknown manual labels: {sorted(invalid)}"
        )

    for column in ("beymen_name", "pozitif_name"):
        pairs[column] = pairs[column].map(text)

        if pairs[column].eq("").any():
            raise ValueError(
                f"Manual file contains blank values in {column}"
            )

    if "split" in pairs.columns:
        pairs["split"] = pairs["split"].map(normalize)

        if not set(pairs["split"]).issubset({"dev", "test"}):
            raise ValueError(
                "If present, split must contain only dev or test"
            )

    return pairs.reset_index(drop=True)


def filter_manual_scope(pairs):
    """
    Preserve non-iPhone examples separately.

    This is a title-level scope filter for the manual reference.
    Actual source listings are additionally filtered by category.
    """
    in_scope = (
        pairs["beymen_name"].map(extract_model).ne("")
        & pairs["pozitif_name"].map(extract_model).ne("")
    )

    excluded = pairs.loc[~in_scope].copy()
    excluded["exclusion_reason"] = (
        "One or both titles are not iPhones"
    )

    RESULTS.mkdir(parents=True, exist_ok=True)

    excluded.to_csv(
        RESULTS / "manual_pairs_out_of_scope.csv",
        index=False,
        encoding="utf-8-sig",
    )

    filtered = pairs.loc[in_scope].reset_index(drop=True)

    print(f"Manual pairs loaded: {len(pairs)}")
    print(f"Out-of-scope pairs saved separately: {len(excluded)}")
    print(f"In-scope iPhone pairs: {len(filtered)}")

    if filtered.empty:
        raise ValueError("No iPhone pairs remain for evaluation")

    return filtered, len(excluded)


def build_lookup(specs):
    records = specs.to_dict("records")

    by_id = {
        record["listing_id"]: record
        for record in records
    }

    by_name = {}

    for record in records:
        by_name.setdefault(
            record["name"], []
        ).append(record)

    return by_id, by_name


def resolve_listing(pair, shop, lookup):
    """
    Prefer an explicit listing ID.

    For a name-only manual reference:
    - accept one matching listing;
    - accept equivalent duplicate listings using a reported representative;
    - reject duplicates with conflicting matching attributes.

    This affects evaluation only. Production offers remain separate.
    """
    by_id, by_name = lookup
    identifier = text(pair.get(f"{shop}_listing_id", ""))

    if identifier:
        if identifier not in by_id:
            raise ValueError(
                f"{pair['pair_id']}: {shop} ID {identifier} is not "
                "in the cleaned iPhone device dataset."
            )

        record = by_id[identifier]

        if clean_name(record["name"]) != clean_name(
            pair[f"{shop}_name"]
        ):
            raise ValueError(
                f"{pair['pair_id']}: {shop} ID/title disagree. "
                "Check the manual file and source snapshot."
            )

        return record

    matches = by_name.get(pair[f"{shop}_name"], [])

    if not matches:
        raise ValueError(
            f"{pair['pair_id']}: {shop} name was not found in "
            "the cleaned iPhone dataset. Check the title or add "
            f"{shop}_listing_id."
        )

    if len(matches) == 1:
        return matches[0]

    # Include every input used by the current matching decisions.
    comparison_fields = (
        "name",
        "brand",
        "model",
        "model_code",
        "storage_gb",
        "colour",
        "condition",
        "is_bundle",
        "source_conflict",
    )

    signatures = {
        tuple(record.get(field) for field in comparison_fields)
        for record in matches
    }

    if len(signatures) != 1:
        conflicting_fields = [
            field
            for field in comparison_fields
            if len({record.get(field) for record in matches}) > 1
        ]

        listing_ids = sorted(
            record["listing_id"] for record in matches
        )

        raise ValueError(
            f"{pair['pair_id']}: multiple {shop} listings share "
            f"this title but differ in {conflicting_fields}. "
            f"Candidates: {listing_ids}. Verify the intended "
            f"source and add {shop}_listing_id."
        )

    # Deterministic representative, used only for this name-based
    # evaluation. All candidates produce the same matching decision.
    matches = sorted(
        matches,
        key=lambda record: record["listing_id"],
    )
    representative = matches[0]

    warnings.warn(
        f"{pair['pair_id']}: equivalent {shop} listings "
        f"{[record['listing_id'] for record in matches]}; "
        f"using {representative['listing_id']} as the "
        "evaluation representative."
    )

    return representative


def resolve_pairs(pairs):
    lookups = {
        shop: build_lookup(load_specs(shop))
        for shop in ("beymen", "pozitif")
    }

    records = []

    for pair in pairs.to_dict("records"):
        a = resolve_listing(
            pair, "beymen", lookups["beymen"]
        )
        b = resolve_listing(
            pair, "pozitif", lookups["pozitif"]
        )

        records.append((a, b))

    return records


def overlap_keys(record):
    """
    Identify overlap by listing, name, code and complete attributes.

    Attribute fingerprints catch the same variant represented by a
    coded listing on one side and an uncoded listing on the other.
    """
    keys = {
        (
            "listing",
            record["shop"],
            record["listing_id"],
        ),
        (
            "name",
            record["shop"],
            clean_name(record["name"]),
        ),
        (
            "product",
            *product_identity(record),
        ),
    }

    fields = ("brand", "model", "storage_gb", "colour")

    if all(record[field] for field in fields):
        keys.add((
            "variant",
            *(record[field] for field in fields),
        ))

    return keys


def evaluation_partition(pairs, records):
    """
    Without explicit splits, report exploratory results.

    With splits, fit TF-IDF on dev and evaluate only on test.
    """
    if "split" not in pairs.columns:
        warnings.warn(
            "No dev/test split: results are exploratory, not "
            "independent test performance."
        )

        indices = list(range(len(pairs)))
        return indices, indices, "exploratory"

    dev = pairs.index[pairs["split"].eq("dev")].tolist()
    test = pairs.index[pairs["split"].eq("test")].tolist()

    if not dev or not test:
        raise ValueError(
            "Both dev and test partitions must contain iPhone pairs"
        )

    dev_keys = set()
    test_keys = set()

    for index in dev:
        for record in records[index]:
            dev_keys.update(overlap_keys(record))

    for index in test:
        for record in records[index]:
            test_keys.update(overlap_keys(record))

    if dev_keys & test_keys:
        raise ValueError(
            "Development/test overlap detected. Keep all pairs "
            "sharing a listing or product variant in the same "
            "partition."
        )

    return dev, test, "held_out"


def check_repeated_pairs(pairs, records):
    """Reject contradictory labels and identify repeated examples."""
    seen = {}
    repeats = []

    for pair, (a, b) in zip(
        pairs.to_dict("records"), records
    ):
        key = (
            clean_name(a["name"]),
            clean_name(b["name"]),
        )

        if key in seen:
            old_id, old_label, old_split = seen[key]

            if old_label != pair["manual_label"]:
                raise ValueError(
                    f"Conflicting labels for equivalent pairs: "
                    f"{old_id} and {pair['pair_id']}"
                )

            if old_split != pair.get("split", ""):
                raise ValueError(
                    f"Repeated pair crosses splits: "
                    f"{old_id} and {pair['pair_id']}"
                )

            repeats.append((old_id, pair["pair_id"]))
        else:
            seen[key] = (
                pair["pair_id"],
                pair["manual_label"],
                pair.get("split", ""),
            )

    if repeats:
        warnings.warn(
            f"{len(repeats)} repeated normalized pairs found. "
            "Equivalent pairs will count once in evaluation."
        )

    return repeats


def unique_pair_indices(records, indices):
    selected = []
    seen = set()

    for index in indices:
        a, b = records[index]

        key = (
            clean_name(a["name"]),
            clean_name(b["name"]),
        )

        if key not in seen:
            seen.add(key)
            selected.append(index)

    return selected


def tfidf_scores(records, fit_indices, evaluation_indices):
    # Fit on unique names so repeated pairs do not overweight documents.
    fit_names = sorted({
        clean_name(record["name"])
        for index in fit_indices
        for record in records[index]
    })

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
    )

    vectorizer.fit(fit_names)

    left = vectorizer.transform([
        clean_name(records[index][0]["name"])
        for index in evaluation_indices
    ])

    right = vectorizer.transform([
        clean_name(records[index][1]["name"])
        for index in evaluation_indices
    ])

    # Default TF-IDF vectors are L2-normalized.
    # Compute only corresponding pair scores, not an N-by-N matrix.
    return np.asarray(
        left.multiply(right).sum(axis=1)
    ).ravel()


def all_predictions(a, b, cosine):
    full_a = normalize(a["name"])
    full_b = normalize(b["name"])

    cleaned_a = clean_name(a["name"])
    cleaned_b = clean_name(b["name"])

    raw_score = fuzz.token_sort_ratio(
        full_a, full_b
    ) / 100

    cleaned_score = fuzz.token_sort_ratio(
        cleaned_a, cleaned_b
    ) / 100

    attribute, attribute_reason = attribute_decision(a, b)
    hybrid, hybrid_reason = hybrid_decision(a, b)

    def threshold_decision(score):
        return "same" if score >= THRESHOLD else "different"

    return {
        "Exact name": (
            "same" if full_a == full_b else "different",
            "Normalized name equality",
            float(full_a == full_b),
        ),
        "RapidFuzz": (
            threshold_decision(raw_score),
            "Token-sort similarity",
            raw_score,
        ),
        "RapidFuzz cleaned": (
            threshold_decision(cleaned_score),
            "Cleaned token-sort similarity",
            cleaned_score,
        ),
        "TF-IDF cleaned": (
            threshold_decision(cosine),
            "Character TF-IDF cosine similarity",
            float(cosine),
        ),
        "Attributes": (
            attribute,
            attribute_reason,
            None,
        ),
        "Hybrid": (
            hybrid,
            hybrid_reason,
            None,
        ),
    }


def score_predictions(group):
    """
    Operational metrics: 'same' versus 'not confirmed'.

    A review decision on a true match counts against operational recall.
    Review counts and automatic-decision coverage are also reported.
    Unresolved reference labels are excluded from these metrics.
    """
    labelled = group.loc[
        group["manual_label"].ne("unsure")
    ].copy()

    if labelled.empty:
        raise ValueError(
            "No resolved reference labels remain for evaluation"
        )

    truth = labelled["manual_label"].eq("same")
    confirmed = labelled["decision"].eq("same")
    review = labelled["decision"].eq("review")

    tp = int((truth & confirmed).sum())
    fp = int((~truth & confirmed).sum())
    fn = int((truth & ~confirmed).sum())
    tn = int((~truth & ~confirmed).sum())

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None

    f1_denominator = 2 * tp + fp + fn
    f1 = (
        2 * tp / f1_denominator
        if f1_denominator
        else None
    )

    return {
        "evaluated_pairs": len(labelled),
        "positive_pairs": int(truth.sum()),
        "negative_pairs": int((~truth).sum()),
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "F1": f1,
        "operational_accuracy": (tp + tn) / len(labelled),
        "review_count": int(review.sum()),
        "review_positive_count": int((review & truth).sum()),
        "review_negative_count": int((review & ~truth).sum()),
        "automatic_decision_coverage": float((~review).mean()),
        "unresolved_reference_pairs": int(
            group["manual_label"].eq("unsure").sum()
        ),
    }


def issue_type(row):
    if row["manual_label"] == "unsure":
        return "unresolved_reference"

    if row["decision"] == "review":
        return "review_required"

    expected_match = row["manual_label"] == "same"
    predicted_match = row["decision"] == "same"

    if predicted_match and not expected_match:
        return "false_positive"

    if expected_match and not predicted_match:
        return "false_negative"

    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manual",
        type=Path,
        default=DEFAULT_MANUAL,
    )
    args = parser.parse_args()

    original_pairs = load_manual(args.manual)
    input_count = len(original_pairs)

    pairs, excluded_count = filter_manual_scope(original_pairs)
    records = resolve_pairs(pairs)

    repeats = check_repeated_pairs(pairs, records)

    fit_indices, evaluation_indices, mode = evaluation_partition(
        pairs, records
    )

    evaluation_indices = unique_pair_indices(
        records, evaluation_indices
    )

    cosine = tfidf_scores(
        records,
        fit_indices,
        evaluation_indices,
    )

    output = []

    for index, cosine_value in zip(
        evaluation_indices, cosine
    ):
        pair = pairs.iloc[index]
        a, b = records[index]

        predictions = all_predictions(a, b, cosine_value)

        for algorithm, prediction in predictions.items():
            decision, reason, similarity = prediction

            output.append({
                "pair_id": pair["pair_id"],
                "algorithm": algorithm,
                "beymen_listing_id": a["listing_id"],
                "pozitif_listing_id": b["listing_id"],
                "beymen_name": a["name"],
                "pozitif_name": b["name"],
                "manual_label": pair["manual_label"],
                "decision": decision,
                "reason": reason,
                "similarity": similarity,
                "evaluation_mode": mode,
                "algorithm_version": VERSION,
            })

    predictions = pd.DataFrame(output)
    comparisons = []

    for algorithm, group in predictions.groupby(
        "algorithm", sort=False
    ):
        comparisons.append({
            "algorithm": algorithm,
            "evaluation_mode": mode,
            **score_predictions(group),
        })

    comparison = pd.DataFrame(comparisons)
    comparison = comparison.sort_values(
        ["F1", "precision"],
        ascending=False,
        na_position="last",
    )

    predictions["issue"] = predictions.apply(
        issue_type, axis=1
    )
    issues = predictions.loc[predictions["issue"].ne("")]

    RESULTS.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(
        RESULTS / "algorithm_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    predictions.to_csv(
        RESULTS / "algorithm_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    issues.to_csv(
        RESULTS / "algorithm_errors.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metadata = {
        "algorithm_version": VERSION,
        "manual_file": str(args.manual),
        "evaluation_mode": mode,
        "threshold": THRESHOLD,
        "input_pairs": input_count,
        "out_of_scope_pairs": excluded_count,
        "in_scope_pairs": len(pairs),
        "repeated_normalized_pairs": len(repeats),
        "unique_evaluation_pairs": len(evaluation_indices),
        "metric_policy": (
            "same versus not confirmed; review counts against "
            "positive recall and is reported separately"
        ),
        "threshold_policy": (
            "Fixed starting threshold, not claimed to be optimized"
        ),
    }

    (RESULTS / "evaluation_run.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"\nEvaluation mode: {mode}")
    print(
        comparison.round(3).to_string(index=False)
    )
    print(f"\nResults saved in: {RESULTS}")


if __name__ == "__main__":
    main()