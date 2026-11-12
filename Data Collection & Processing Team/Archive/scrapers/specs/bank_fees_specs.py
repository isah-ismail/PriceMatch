"""
Annual credit card fees (category 12) for Akbank, DenizBank and Garanti BBVA.

Makes no requests: it reads the bank fee CSVs the inflation study already
collected and splits each name into the card and the kind of fee.

    "DenizBank - Sea&Miles Bonus Gold - İlk Yıl Ek Kart Ücreti - TL - BSMV Dahil - Updated 10.03.2026"
    -> model "Sea&Miles Bonus Gold", variant "Ek Kart, İlk Yıl"

The banks give no product id, so a fee is identified by its exact name, as the
grocery stores are. `category` stays empty because the source carries no
7-digit CPI code; `category_number` is 12 as scraped.

A fee of 0 TL is a real offer (a free card) and is kept, unlike a 0 price in a shop.

Output, per bank:
    data/specs/<bank>_specs_clean.csv           same 29 columns as the other cleaned spec files
    data/prices/<bank>_prices_<YYYY-MM-DD>.csv  same 8 columns as the other price files
"""

import argparse
import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "data" / "specs"
PRICES_DIR = REPO_ROOT / "data" / "prices"
DEFAULT_RAW = REPO_ROOT.parent / "Product Matching & Hierarchy Problem Team" / "data" / "raw" / "category_12"

CLEAN_FIELDS = [
    "retailer", "offer_id", "record_key", "original_product_name", "standardized_product_name",
    "brand", "model", "category", "category_number", "sub_category_number", "variant", "capacity",
    "size", "color", "pack_quantity", "unit", "data_quality_status", "review_reason",
    "standardization_changes", "retailer_product_id", "barcode", "product_url", "image_url",
    "store_category", "condition", "is_bundle", "first_seen", "last_seen", "source_file",
]
PRICE_FIELDS = ["retailer", "retailer_product_id", "date", "price", "product_name", "brand", "model", "product_url"]

CATEGORY_NUMBER = "12"
MAIN, SUPPLEMENTARY, CLUB = "Asıl Kart", "Ek Kart", "Kulüp Üyeliği"
FIRST_YEAR, LATER_YEARS = "İlk Yıl", "İlk Yıldan Sonra"
DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.csv$")

DENIZBANK_FEES = {
    "İlk Yıl Asıl Kart Ücreti": (MAIN, FIRST_YEAR),
    "İlk Yıl Ek Kart Ücreti": (SUPPLEMENTARY, FIRST_YEAR),
    "Asıl Kart Üyelik Ücreti (ilk yıldan sonra)": (MAIN, LATER_YEARS),
    "Ek Kart Üyelik Ücreti (ilk yıldan sonra)": (SUPPLEMENTARY, LATER_YEARS),
}
GARANTI_FEES = ("Annual card fee", "Annual club membership fee")
GARANTI_NETWORKS = ("American Express", "Mastercard", "Visa", "Mastercard/Visa")
GARANTI_BOILERPLATE = ("TL", "BSMV included")
CLOSED = "Not open for applications"


def squeeze(text):
    return " ".join(str(text or "").split())


def parse_akbank(row):
    card = squeeze(row["card_name"])
    holder = SUPPLEMENTARY if re.search(r"\bEk Kart\b", card) else MAIN
    card = squeeze(re.sub(r"\b(Ek )?Kart Ücreti\b", "", card))
    return {"model": card, "variant": [holder], "store_category": squeeze(row["fee_type"]),
            "product_url": squeeze(row["source_url"]), "remarks": [], "review": []}


def parse_denizbank(row):
    parts = [squeeze(p) for p in row["product_name"].split(" - ")]
    card, fee = parts[1], parts[2]
    review = []
    if fee in DENIZBANK_FEES:
        variant = list(DENIZBANK_FEES[fee])
    else:
        variant, review = [], [f"unknown fee wording: {fee}"]
    return {"model": card, "variant": variant, "store_category": fee,
            "product_url": "", "remarks": [], "review": review}


def parse_garanti(row):
    parts = [squeeze(p) for p in row["product_name"].split(" - ")]
    card, rest = parts[1], parts[2:]

    holder = MAIN
    if card.endswith("-Ek Kart"):
        card, holder = card[: -len("-Ek Kart")], SUPPLEMENTARY
    if "Ek Kart" in rest:
        holder = SUPPLEMENTARY

    fee = next((p for p in rest if p in GARANTI_FEES), "")
    network = next((p for p in rest if p in GARANTI_NETWORKS), "")
    notes = [p for p in rest
             if p not in GARANTI_FEES + GARANTI_NETWORKS + GARANTI_BOILERPLATE and p not in ("Ek Kart", CLOSED)]

    review = []
    if not fee:
        review.append("fee kind not found in name")
    if fee == "Annual club membership fee":
        holder = CLUB
        review.append("club membership fee, not a card fee")
    if CLOSED in rest:
        review.append("closed to new applications")
    review += [n for n in notes if n.startswith("Published amount")]
    remarks = [n for n in notes if not n.startswith("Published amount")]

    return {"model": card, "variant": [holder] + ([network] if network else []), "store_category": fee,
            "product_url": "", "remarks": remarks, "review": review}


BANKS = [
    ("Akbank", "Akbank", parse_akbank),
    ("DenizBank", "DenizBank", parse_denizbank),
    ("Garanti BBVA", "GarantiBBVA", parse_garanti),
]


def latest_file(folder):
    files = sorted((m.group(1), path) for path in folder.glob("*.csv") if (m := DATE_RE.search(path.name)))
    return files[-1] if files else (None, None)


def valid_price(text):
    try:
        return float(text) >= 0
    except (TypeError, ValueError):
        return False


def clean_bank(retailer, folder, parse, raw_dir):
    date, path = latest_file(raw_dir / folder)
    if path is None:
        print(f"{retailer}: no dated CSV in {raw_dir / folder}")
        return None

    with open(path, newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))

    specs, prices, seen, rejected = [], [], set(), 0
    for number, row in enumerate(raw, start=1):
        name = squeeze(row.get("product_name"))
        if not name or not valid_price(row.get("price")):
            rejected += 1
            continue
        if (name, row["price"]) in seen:
            continue
        seen.add((name, row["price"]))

        parsed = parse({**row, "product_name": name})
        variant = ", ".join(parsed["variant"])
        specs.append({
            "retailer": retailer,
            "record_key": f"{retailer}|{path.name}|{number}",
            "original_product_name": name,
            "standardized_product_name": " – ".join(p for p in (retailer, parsed["model"], variant) if p),
            "model": parsed["model"],
            "category_number": CATEGORY_NUMBER,
            "sub_category_number": squeeze(row.get("sub_category_number")),
            "variant": variant,
            "data_quality_status": "needs_review" if parsed["review"] else "clean",
            "review_reason": "; ".join(parsed["review"] + parsed["remarks"]),
            "standardization_changes": "kart adı ve ücret türü ayrıldı",
            "product_url": parsed["product_url"],
            "store_category": parsed["store_category"],
            "first_seen": date,
            "last_seen": date,
            "source_file": path.name,
        })
        prices.append({
            "retailer": retailer,
            "date": date,
            "price": float(row["price"]),
            "product_name": name,
            "model": parsed["model"],
            "product_url": parsed["product_url"],
        })

    prefix = folder.lower()
    write(SPECS_DIR / f"{prefix}_specs_clean.csv", CLEAN_FIELDS, specs, "utf-8")
    write(PRICES_DIR / f"{prefix}_prices_{date}.csv", PRICE_FIELDS, prices, "utf-8-sig")

    review = sum(r["data_quality_status"] == "needs_review" for r in specs)
    print(f"{retailer}: {path.name}: {len(raw)} rows, {rejected} rejected, "
          f"{len(raw) - rejected - len(specs)} duplicates, {len(specs)} kept ({review} need review)")
    return specs


def write(path, fields, rows, encoding):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW,
                        help="folder holding Akbank/, DenizBank/ and GarantiBBVA/ with the bank fee CSVs")
    args = parser.parse_args()

    total = 0
    for retailer, folder, parse in BANKS:
        specs = clean_bank(retailer, folder, parse, args.raw)
        total += len(specs or [])
    print(f"Total: {total} fees")


if __name__ == "__main__":
    main()
