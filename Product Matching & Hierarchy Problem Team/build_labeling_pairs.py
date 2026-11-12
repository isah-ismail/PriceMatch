"""
Builds the set of cross-retailer product pairs that a person labels by hand.

Input:  the Data Collection team's cleaned catalog (specs_cleaned_all.csv).
Output: data/labels/pairs_to_label.csv with an empty `label` column.

Pairs are drawn from six groups so the set holds easy and hard cases:

    same_barcode       both stores list the same barcode (likely the same product)
    same_model_code    both stores list the same manufacturer model code
    different_barcode  same brand, similar names, but different barcodes (hard negatives)
    different_model    same brand, similar names, but different model codes (hard negatives)
    similar_name       same brand, similar names, no barcode or model code to compare
    random             same category, otherwise random (easy negatives)

The barcode and model code only choose which pairs to show. They are never
given to the matching algorithms, and the label is the person's decision.
"""

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from data_normalization import normalize_text

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT.parent / "Data Collection & Processing Team" / "data" / "specs" / "specs_cleaned_all.csv"
OUTPUT = ROOT / "data" / "labels" / "pairs_to_label.csv"

SEED = 42
GROCERY = {"Hakmar", "HappyCenter", "Ideal", "Marketzade", "Sariyer"}
QUOTA = {
    "same_barcode": 120,
    "same_model_code": 60,
    "different_barcode": 80,
    "different_model": 40,
    "similar_name": 100,
    "random": 40,
}
MIN_SIMILARITY = 60
MAX_BLOCK = 1500


def load_catalog():
    df = pd.read_csv(CATALOG, dtype=str).fillna("")
    df = df.drop_duplicates("record_key").reset_index(drop=True)
    df["domain"] = np.where(df["retailer"].isin(GROCERY), "groceries", "electronics")
    df["normalized_name"] = df["original_product_name"].map(normalize_text)
    return df


def shared_key_pairs(df, key):
    """One pair per value of `key` (barcode or model) that two retailers share."""
    pairs = []
    for _, group in df[df[key] != ""].groupby(key):
        group = group.drop_duplicates("retailer")
        if len(group) > 1:
            a, b = group.index[:2]
            pairs.append((a, b, 100.0))
    return pairs


def similar_pairs(df):
    """Cross-retailer pairs of the same brand whose names are at least MIN_SIMILARITY alike."""
    pairs = []
    for _, block in df[df["brand"] != ""].groupby(["domain", "brand"]):
        by_retailer = [g for _, g in block.groupby("retailer")]
        for left, right in combinations(by_retailer, 2):
            left, right = left.head(MAX_BLOCK), right.head(MAX_BLOCK)
            scores = process.cdist(
                left["normalized_name"].tolist(),
                right["normalized_name"].tolist(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=MIN_SIMILARITY,
            )
            for i, j in zip(*np.nonzero(scores)):
                pairs.append((left.index[i], right.index[j], float(scores[i, j])))
    return pairs


def random_pairs(df, count, rng):
    pairs = []
    blocks = [g for _, g in df[df["category"] != ""].groupby("category") if g["retailer"].nunique() > 1]
    while len(pairs) < count:
        block = blocks[rng.integers(len(blocks))]
        a, b = block.index[rng.choice(len(block), size=2, replace=False)]
        if df.at[a, "retailer"] != df.at[b, "retailer"]:
            pairs.append((a, b, float(fuzz.token_sort_ratio(df.at[a, "normalized_name"], df.at[b, "normalized_name"]))))
    return pairs


def sample_across_scores(pairs, count, rng):
    """Samples evenly over similarity bands so the set is not all near-identical names."""
    if len(pairs) <= count:
        return pairs
    frame = pd.DataFrame(pairs, columns=["a", "b", "score"])
    frame["band"] = pd.cut(frame["score"], bins=[0, 70, 80, 90, 101], right=False)
    per_band = int(np.ceil(count / frame["band"].nunique()))
    picked = pd.concat(
        g.sample(min(len(g), per_band), random_state=int(rng.integers(1_000_000)))
        for _, g in frame.groupby("band", observed=True)
    )
    if len(picked) < count:
        rest = frame.drop(picked.index)
        picked = pd.concat([picked, rest.sample(count - len(picked), random_state=SEED)])
    return list(picked.head(count)[["a", "b", "score"]].itertuples(index=False, name=None))


def classify_similar(df, pairs):
    groups = {"different_barcode": [], "different_model": [], "similar_name": []}
    for a, b, score in pairs:
        row_a, row_b = df.loc[a], df.loc[b]
        if row_a["barcode"] and row_b["barcode"]:
            if row_a["barcode"] != row_b["barcode"]:
                groups["different_barcode"].append((a, b, score))
        elif row_a["model"] and row_b["model"]:
            if row_a["model"] != row_b["model"]:
                groups["different_model"].append((a, b, score))
        else:
            groups["similar_name"].append((a, b, score))
    return groups


def to_rows(df, pairs, group):
    rows = []
    for a, b, score in pairs:
        row_a, row_b = df.loc[a], df.loc[b]
        rows.append({
            "domain": row_a["domain"],
            "retailer_a": row_a["retailer"],
            "name_a": row_a["original_product_name"],
            "retailer_b": row_b["retailer"],
            "name_b": row_b["original_product_name"],
            "label": "",
            "note": "",
            "url_a": row_a["product_url"],
            "url_b": row_b["product_url"],
            "record_key_a": row_a["record_key"],
            "record_key_b": row_b["record_key"],
            "sampling_group": group,
        })
    return rows


def main():
    rng = np.random.default_rng(SEED)
    df = load_catalog()
    print(f"Catalog: {len(df)} listings from {df['retailer'].nunique()} retailers")

    candidates = {
        "same_barcode": shared_key_pairs(df, "barcode"),
        "same_model_code": shared_key_pairs(df, "model"),
        **classify_similar(df, similar_pairs(df)),
    }
    candidates["random"] = random_pairs(df, QUOTA["random"], rng)

    rows, used = [], set()
    for group, quota in QUOTA.items():
        fresh = [p for p in candidates[group] if frozenset(p[:2]) not in used]
        chosen = sample_across_scores(fresh, quota, rng)
        used.update(frozenset(p[:2]) for p in chosen)
        rows += to_rows(df, chosen, group)
        print(f"{group:18} {len(candidates[group]):6} candidates, {len(chosen):4} chosen")

    out = pd.DataFrame(rows).sample(frac=1, random_state=SEED).reset_index(drop=True)
    out.insert(0, "pair_id", [f"P{i:04d}" for i in range(1, len(out) + 1)])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\n{len(out)} pairs saved to {OUTPUT}")
    print(out["domain"].value_counts().to_string())


if __name__ == "__main__":
    main()
