"""Match Beymen–Pozitif iPhones and compare confirmed offers."""

import argparse
import json
import re
from decimal import Decimal, InvalidOperation

import pandas as pd

from matching_rules import (
    DATA_TEAM,
    RESULTS,
    SHOPS,
    VERSION,
    THRESHOLD,
    candidate_pairs,
    hybrid_decision,
    iphone_scope,
    load_specs,
    read_csv,
    text,
)


def parse_price(value):
    """Return positive integer minor units, or None for invalid prices."""
    value = text(value)

    # Reject locale-formatted values rather than guessing their meaning.
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None

    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            return None
        return int(amount * 100)
    except InvalidOperation:
        return None


def price_text(value):
    if value is None:
        return ""
    return f"{Decimal(value) / 100:.2f}"


def load_offers(shop):
    specs = load_specs(shop)

    files = sorted(
        (DATA_TEAM / "prices").glob(f"{shop}_prices_*.csv")
    )
    if not files:
        raise FileNotFoundError(f"No price files found for {shop}")

    price_file = files[-1]
    prices = read_csv(price_file)

    required = {"listing_id", "price", "currency"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(
            f"{price_file.name}: missing columns {sorted(missing)}"
        )

    prices["listing_id"] = prices["listing_id"].map(text)
    if prices["listing_id"].eq("").any():
        raise ValueError(f"{price_file.name}: blank listing IDs")
    if prices["listing_id"].duplicated().any():
        raise ValueError(
            f"{price_file.name}: duplicate listing IDs; "
            "select one current offer per listing upstream"
        )

    price_lookup = prices.set_index("listing_id").to_dict("index")
    offers = []

    for row in specs.to_dict("records"):
        price_row = price_lookup.get(row["listing_id"], {})

        row["price_minor"] = parse_price(price_row.get("price", ""))
        row["currency"] = text(price_row.get("currency", "")).upper()
        row["price_source"] = price_file.name
        row["observed_at"] = text(price_row.get("observed_at", ""))

        # Missing prices do not prevent identity matching.
        offers.append(row)

    return offers


def comparison_row(a, b, reason):
    result = {
        "beymen_listing_id": a["listing_id"],
        "pozitif_listing_id": b["listing_id"],
        "model": a["model"],
        "storage_gb": a["storage_gb"],
        "colour": a["colour"],
        "beymen_name": a["name"],
        "pozitif_name": b["name"],
        "beymen_model_code": a["model_code"],
        "pozitif_model_code": b["model_code"],
        "beymen_price": price_text(a["price_minor"]),
        "pozitif_price": price_text(b["price_minor"]),
        "beymen_currency": a["currency"],
        "pozitif_currency": b["currency"],
        "beymen_url": a["url"],
        "pozitif_url": b["url"],
        "beymen_price_source": a["price_source"],
        "pozitif_price_source": b["price_source"],
        "beymen_observed_at": a["observed_at"],
        "pozitif_observed_at": b["observed_at"],
        "best_price": "",
        "best_price_shop": "",
        "price_difference": "",
        "price_status": "",
        "reason": reason,
        "algorithm_version": VERSION,
    }

    if a["price_minor"] is None or b["price_minor"] is None:
        result["price_status"] = "missing_or_invalid_price"
    elif not a["currency"] or a["currency"] != b["currency"]:
        result["price_status"] = "missing_or_different_currency"
    else:
        pa, pb = a["price_minor"], b["price_minor"]
        result["best_price"] = price_text(min(pa, pb))
        result["price_difference"] = price_text(abs(pa - pb))
        result["best_price_shop"] = (
            "tie" if pa == pb else "beymen" if pa < pb else "pozitif"
        )
        result["price_status"] = "comparable_recorded_prices"

    return result


def save_rows(rows, destination, columns):
    pd.DataFrame(rows, columns=columns).to_csv(
        destination, index=False, encoding="utf-8-sig"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pairs", type=int, default=100_000)
    args = parser.parse_args()

    offers = {shop: load_offers(shop) for shop in SHOPS}
    confirmed = []
    reviews = []
    matched_ids = {shop: set() for shop in SHOPS}
    candidate_count = 0
    different_count = 0

    for a, b in candidate_pairs(
        offers["beymen"],
        offers["pozitif"],
        max_pairs=args.max_pairs,
    ):
        candidate_count += 1
        decision, reason = hybrid_decision(a, b)

        if decision == "same":
            confirmed.append(comparison_row(a, b, reason))
            matched_ids["beymen"].add(a["listing_id"])
            matched_ids["pozitif"].add(b["listing_id"])
        elif decision == "review":
            reviews.append({
                "beymen_listing_id": a["listing_id"],
                "pozitif_listing_id": b["listing_id"],
                "beymen_name": a["name"],
                "pozitif_name": b["name"],
                "decision": decision,
                "reason": reason,
                "algorithm_version": VERSION,
            })
        else:
            different_count += 1

    unmatched = []
    for shop in SHOPS:
        for row in offers[shop]:
            if row["listing_id"] in matched_ids[shop]:
                continue
            eligible, reason = iphone_scope(row)
            unmatched.append({
                "shop": shop,
                "listing_id": row["listing_id"],
                "name": row["name"],
                "url": row["url"],
                "reason": (
                    "No confirmed cross-shop match"
                    if eligible else reason
                ),
            })

    RESULTS.mkdir(parents=True, exist_ok=True)

    match_columns = [
        "beymen_listing_id", "pozitif_listing_id",
        "model", "storage_gb", "colour",
        "beymen_name", "pozitif_name",
        "beymen_model_code", "pozitif_model_code",
        "beymen_price", "pozitif_price",
        "beymen_currency", "pozitif_currency",
        "beymen_url", "pozitif_url",
        "beymen_price_source", "pozitif_price_source",
        "beymen_observed_at", "pozitif_observed_at",
        "best_price", "best_price_shop", "price_difference",
        "price_status", "reason", "algorithm_version",
    ]
    save_rows(
        confirmed, RESULTS / "product_matches.csv", match_columns
    )
    save_rows(
        reviews,
        RESULTS / "matching_reviews.csv",
        [
            "beymen_listing_id", "pozitif_listing_id",
            "beymen_name", "pozitif_name",
            "decision", "reason", "algorithm_version",
        ],
    )
    save_rows(
        unmatched,
        RESULTS / "unmatched_listings.csv",
        ["shop", "listing_id", "name", "url", "reason"],
    )

    metadata = {
        "algorithm_version": VERSION,
        "algorithm": "hybrid",
        "threshold": THRESHOLD,
        "shops": list(SHOPS),
        "listings": {s: len(offers[s]) for s in SHOPS},
        "candidate_pairs": candidate_count,
        "confirmed_pairs": len(confirmed),
        "review_pairs": len(reviews),
        "different_pairs": different_count,
        "price_scope": (
            "Recorded item prices only; no shipping adjustment "
            "or availability guarantee"
        ),
    }
    (RESULTS / "matching_run.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(json.dumps(metadata, indent=2))
    print(f"\nResults saved in: {RESULTS}")


if __name__ == "__main__":
    main()