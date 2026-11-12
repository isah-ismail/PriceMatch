"""
Compares every matching algorithm on the manually labeled pairs.

Protocol, identical for all algorithms:
  1. Read data/labels/pairs_labeled.csv. `same` is the positive class,
     `comparable` and `different` are negative, `unsure` is left out.
  2. Split the pairs into training (70%) and test (30%) so that no listing
     appears on both sides.
  3. Choose each algorithm's threshold, and the supervised models'
     hyperparameters, using the training pairs only.
  4. Score every algorithm once on the test pairs.

Output in data/results/:
  benchmark_metrics.csv   TP, FP, TN, FN, precision, recall, F1, accuracy and
                          the difference to the RapidFuzz baseline
  benchmark_errors.csv    every false positive and false negative on the test pairs
  matching_model.joblib   the best supervised model with its TF-IDF vectorizer and threshold
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import matchers

ROOT = Path(__file__).resolve().parent
LABELS = ROOT / "data" / "labels" / "pairs_labeled.csv"
CATALOG = ROOT.parent / "Data Collection & Processing Team" / "data" / "specs" / "specs_cleaned_all.csv"
RESULTS = ROOT / "data" / "results"

SEED = 42
TEST_SHARE = 0.3
VALID_LABELS = {"same", "comparable", "different", "unsure"}
BASELINE = "RapidFuzz"

MODELS = {
    "Logistic Regression": (
        make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)),
        {"logisticregression__C": [0.01, 0.1, 1, 10]},
    ),
    "Random Forest": (
        RandomForestClassifier(class_weight="balanced", random_state=SEED),
        {"n_estimators": [200], "max_depth": [3, 6, None], "min_samples_leaf": [1, 3, 5]},
    ),
}


def load_labels(path):
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    df["label"] = df["label"].str.strip().str.lower()
    unknown = sorted(set(df["label"]) - VALID_LABELS - {""})
    if unknown:
        raise ValueError(f"Unknown labels {unknown}; allowed: {sorted(VALID_LABELS)}")

    print(f"Pairs in file: {len(df)}")
    print(df["label"].replace("", "(not labeled yet)").value_counts().to_string())
    df = df[df["label"].isin({"same", "comparable", "different"})].reset_index(drop=True)
    df["is_match"] = (df["label"] == "same").astype(int)
    return df


def listing_groups(df):
    """Gives pairs that share a listing the same group number, so a split keeps them together."""
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for a, b in zip(df["record_key_a"], df["record_key_b"]):
        parent[find(a)] = find(b)
    return df["record_key_a"].map(find).factorize()[0]


def best_threshold(scores, truth):
    """The cut-off with the highest F1 on the training pairs."""
    candidates = np.unique(np.round(scores, 2))
    return max(candidates, key=lambda t: f1_score(truth, scores >= t, zero_division=0))


def metrics(truth, predicted):
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "precision": precision,
            "recall": recall, "f1": f1, "accuracy": (tp + tn) / len(truth)}


def main():
    parser = argparse.ArgumentParser(description="Benchmark the matching algorithms on the labeled pairs.")
    parser.add_argument("--labels", type=Path, default=LABELS)
    args = parser.parse_args()

    df = load_labels(args.labels)
    groups = listing_groups(df)
    train_idx, test_idx = next(
        GroupShuffleSplit(n_splits=1, test_size=TEST_SHARE, random_state=SEED).split(df, groups=groups)
    )
    truth = df["is_match"].to_numpy()
    print(f"\nTraining pairs: {len(train_idx)} ({truth[train_idx].sum()} matches)")
    print(f"Test pairs:     {len(test_idx)} ({truth[test_idx].sum()} matches)")

    catalog_names = pd.read_csv(CATALOG, dtype=str, usecols=["original_product_name"])["original_product_name"]
    tfidf = matchers.TfidfMatcher().fit(catalog_names.dropna())

    names = list(zip(df["name_a"], df["name_b"]))
    scores = {
        "Exact match": np.array([matchers.exact_score(a, b) for a, b in names]),
        "RapidFuzz": np.array([matchers.fuzzy_score(a, b) for a, b in names]),
        "TF-IDF cosine": np.array([tfidf.score(a, b) for a, b in names]),
        "Attribute-aware": np.array([matchers.attribute_score(a, b) for a, b in names]),
    }
    thresholds = {"Exact match": 1.0}
    for name in ("RapidFuzz", "TF-IDF cosine", "Attribute-aware"):
        thresholds[name] = best_threshold(scores[name][train_idx], truth[train_idx])

    features = pd.DataFrame([matchers.pair_features(a, b, tfidf) for a, b in names])
    folds = GroupKFold(n_splits=5)
    fitted = {}
    for name, (model, grid) in MODELS.items():
        search = GridSearchCV(model, grid, scoring="f1", cv=folds)
        search.fit(features.iloc[train_idx], truth[train_idx], groups=groups[train_idx])
        fitted[name] = search.best_estimator_
        scores[name] = search.predict_proba(features)[:, 1]
        thresholds[name] = 0.5
        print(f"{name}: best settings {search.best_params_}, cross-validated F1 {search.best_score_:.3f}")

    rows, errors = [], []
    for name, values in scores.items():
        predicted = (values >= thresholds[name]).astype(int)
        rows.append({"algorithm": name, "threshold": thresholds[name],
                     **metrics(truth[test_idx], predicted[test_idx])})
        for i in test_idx:
            if predicted[i] != truth[i]:
                errors.append({
                    "algorithm": name,
                    "error": "false positive" if predicted[i] else "false negative",
                    "pair_id": df.at[i, "pair_id"], "label": df.at[i, "label"],
                    "score": round(float(values[i]), 3),
                    "name_a": df.at[i, "name_a"], "name_b": df.at[i, "name_b"],
                })

    table = pd.DataFrame(rows).set_index("algorithm")
    base_f1 = table.at[BASELINE, "f1"]
    table["f1_diff_vs_rapidfuzz"] = table["f1"] - base_f1
    table["f1_relative_diff_pct"] = (table["f1"] - base_f1) / base_f1 * 100 if base_f1 else np.nan

    RESULTS.mkdir(parents=True, exist_ok=True)
    table.round(4).to_csv(RESULTS / "benchmark_metrics.csv", encoding="utf-8-sig")
    pd.DataFrame(errors).to_csv(RESULTS / "benchmark_errors.csv", index=False, encoding="utf-8-sig")

    best = max(fitted, key=lambda name: table.at[name, "f1"])
    joblib.dump({"model": fitted[best], "tfidf": tfidf, "threshold": thresholds[best],
                 "features": list(features.columns), "algorithm": best},
                RESULTS / "matching_model.joblib")

    print("\n========== TEST RESULTS ==========")
    print(table.round(3).to_string())
    print(f"\nSaved model: {best}")
    print(f"Results written to {RESULTS}")


if __name__ == "__main__":
    main()
