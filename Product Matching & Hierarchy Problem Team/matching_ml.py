
from pathlib import Path
from itertools import combinations

import pandas as pd
from rapidfuzz import fuzz


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "processed" / "category_12_normalized.csv"
OUTPUT = ROOT / "data" / "processed" / "category_12_matches.csv"

ANNUAL_TERMS = ("annual", "yearly", "yillik", "senelik")
CARD_TERMS = ("card", "kart", "karti", "kartinin")
FEE_TERMS = ("fee", "charge", "ucret", "aidat", "bedel")
BUSINESS_TERMS = ("business", "ticari", "kurumsal")
SUPPLEMENTARY_TERMS = (
    "ek kart",
    "additional card",
    "supplementary card",
    "extra card",
)


def contains_term(text, terms):
    words = set(str(text).split())
    return any(term in words for term in terms)


def contains_phrase(text, phrases):
    padded = f" {str(text).strip()} "
    return any(f" {phrase} " in padded for phrase in phrases)


def extract_attributes(name):
    text = str(name)

    return {
        "annual": contains_term(text, ANNUAL_TERMS),
        "card": contains_term(text, CARD_TERMS),
        "fee": contains_term(text, FEE_TERMS),
        "business": contains_term(text, BUSINESS_TERMS),
        "supplementary": contains_phrase(text, SUPPLEMENTARY_TERMS),
    }


def classify_pair(row_a, row_b):
    name_a = str(row_a["normalized_name"])
    name_b = str(row_b["normalized_name"])

    attrs_a = extract_attributes(name_a)
    attrs_b = extract_attributes(name_b)

    score = fuzz.token_sort_ratio(name_a, name_b)

    same_service_type = all(
        attrs_a[key] and attrs_b[key]
        for key in ("annual", "card", "fee")
    )

    business_conflict = (
        attrs_a["business"] != attrs_b["business"]
    )

    supplementary_conflict = (
        attrs_a["supplementary"] != attrs_b["supplementary"]
    )

    if not same_service_type:
        decision = "different_or_unverified_service"
    elif supplementary_conflict:
        decision = "different_card_fee_type"
    elif business_conflict:
        decision = "review_card_type"
    elif score >= 80:
        decision = "high_description_similarity"
    elif score >= 55:
        decision = "comparable_service"
    else:
        decision = "low_description_similarity"

    return score, decision


def main():
    print("Starting Category 12 matching...")

    df = pd.read_csv(
        INPUT,
        encoding="utf-8-sig",
        dtype={"normalized_name": str},
    ).fillna("")

    required_columns = {
        "retailer",
        "product_name",
        "normalized_name",
        "price",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing columns: {sorted(missing_columns)}"
        )

    print(f"Loaded {len(df)} records.")

    results = []

    for i, j in combinations(range(len(df)), 2):
        row_a = df.iloc[i]
        row_b = df.iloc[j]

        if row_a["retailer"] == row_b["retailer"]:
            continue

        score, decision = classify_pair(row_a, row_b)

        results.append({
            "retailer_a": row_a["retailer"],
            "product_a": row_a["product_name"],
            "price_a": row_a["price"],
            "retailer_b": row_b["retailer"],
            "product_b": row_b["product_name"],
            "price_b": row_b["price"],
            "similarity_score": round(score, 2),
            "decision": decision,
        })

    result = pd.DataFrame(results)

    if result.empty:
        print("No cross-bank pairs found.")
        return

    result = result.sort_values(
        by="similarity_score",
        ascending=False,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    result.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n========== MATCHING RESULTS ==========")
    print(f"Products analyzed: {len(df)}")
    print(f"Cross-bank pairs compared: {len(result)}")

    print("\nDecision counts:")
    print(result["decision"].value_counts())

    print("\nTop 5 most similar descriptions:")

    for _, row in result.head(5).iterrows():
        print()
        print(f"{row['retailer_a']}: {row['product_a']}")
        print(f"{row['retailer_b']}: {row['product_b']}")
        print(f"Similarity: {row['similarity_score']:.1f}")
        print(f"Decision: {row['decision']}")

    print(f"\nSaved results to: {OUTPUT}")


if __name__ == "__main__":
    main()
