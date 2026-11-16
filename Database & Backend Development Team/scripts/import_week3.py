"""Import Week 3 clean specifications and dated prices into PriceMatch PostgreSQL.

Run from anywhere: python import_week3.py --data-root '/path/to/Data Collection & Processing Team/data'
Requires psycopg 3: pip install 'psycopg[binary]'
Requires migration 002 and DATABASE_URL (or --database-url). Does not reset existing data.

Conservative MVP: each source listing gets its own product. Never guess cross-store matches.
A confirmed listing_id -> canonical_id mapping from matching team is a later integration.
"""
import argparse
import csv
import os
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo


STORES = {"beymen": ("Beymen", "https://www.beymen.com"),
          "pozitif": ("Pozitif", "https://www.pt.com.tr"),
          "samsung": ("Samsung", "https://www.samsung.com")}
TZ = ZoneInfo("Europe/Istanbul")


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def clean(value):
    return (value or "").strip()


def import_data(conn, root):
    counts = Counter()
    with conn.transaction():
        with conn.cursor() as cur:
            for slug, (store, website) in STORES.items():
                spec_path = root / "clean" / f"{slug}_specs.csv"
                price_paths = sorted((root / "prices").glob(f"{slug}_prices_*.csv"))
                if not spec_path.is_file() or not price_paths:
                    raise FileNotFoundError(f"Missing specs/prices for {store}: {spec_path}")
                specs = {}
                for row in rows(spec_path):
                    listing = clean(row.get("listing_id"))
                    if not listing or listing in specs:
                        raise ValueError(f"Missing or duplicate listing_id in {spec_path}: {listing!r}")
                    if clean(row.get("retailer")).casefold() != store.casefold():
                        raise ValueError(f"Retailer mismatch in {spec_path}: {listing}")
                    specs[listing] = row
                cur.execute("SELECT retailer_id FROM retailers WHERE website_url = %s", (website,))
                record = cur.fetchone()
                if record:
                    retailer_id = record[0]
                else:
                    cur.execute("INSERT INTO retailers (name, website_url) VALUES (%s,%s) RETURNING retailer_id", (store, website))
                    retailer_id = cur.fetchone()[0]
                seen_prices = set()
                for price_path in price_paths:
                    for row in rows(price_path):
                        listing = clean(row.get("listing_id"))
                        spec = specs.get(listing)
                        if not spec:
                            counts["unmatched_price_rows"] += 1
                            continue
                        if clean(row.get("retailer")).casefold() != store.casefold():
                            raise ValueError(f"Price retailer mismatch: {listing}")
                        if clean(row.get("retailer_product_id")) != clean(spec.get("retailer_product_id")):
                            raise ValueError(f"Source ID mismatch: {listing}")
                        if clean(spec.get("condition")) != "new" or clean(spec.get("quality_status")) != "ok" or clean(spec.get("is_bundle")) != "False":
                            counts["filtered_rows"] += 1
                            continue
                        try:
                            price = Decimal(clean(row.get("price")))
                            day = date.fromisoformat(clean(row.get("date")))
                        except (InvalidOperation, ValueError) as exc:
                            raise ValueError(f"Bad price/date in {price_path}: {listing}") from exc
                        if price <= 0 or not price.is_finite():
                            raise ValueError(f"Nonpositive/nonfinite price: {listing}")
                        if clean(row.get("currency")) != "TRY":
                            raise ValueError(f"Unexpected currency for {listing}")
                        observation = datetime.combine(day, time.min, tzinfo=TZ)
                        key = (listing, day)
                        if key in seen_prices:
                            raise ValueError(f"Duplicate listing/date in price files: {key}")
                        seen_prices.add(key)
                        cur.execute("SELECT offer_id, product_id, last_updated FROM offers WHERE listing_id = %s", (listing,))
                        existing = cur.fetchone()
                        if existing:
                            offer_id, product_id, old_updated = existing
                            counts["existing_listings"] += 1
                        else:
                            category = clean(spec.get("category"))[:150] or "Uncategorized"
                            cur.execute("SELECT category_id FROM categories WHERE name = %s AND parent_category_id IS NULL ORDER BY category_id LIMIT 1", (category,))
                            found = cur.fetchone()
                            if found:
                                category_id = found[0]
                            else:
                                cur.execute("INSERT INTO categories (name) VALUES (%s) RETURNING category_id", (category,))
                                category_id = cur.fetchone()[0]
                            brand = clean(spec.get("brand"))[:150]
                            brand_id = None
                            if brand:
                                cur.execute("INSERT INTO brands (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING brand_id", (brand,))
                                brand_id = cur.fetchone()[0]
                            model = clean(spec.get("model_code"))[:150] or None
                            variant = " | ".join(filter(None, [clean(spec.get("color")), clean(spec.get("storage_gb")) and clean(spec.get("storage_gb")) + " GB"]))[:150] or None
                            cur.execute("""INSERT INTO products (category_id, brand_id, name, model, variant, image_url)
                                           VALUES (%s,%s,%s,%s,%s,%s) RETURNING product_id""",
                                        (category_id, brand_id, clean(spec.get("name"))[:255] or listing, model, variant, clean(spec.get("image_url")) or None))
                            product_id = cur.fetchone()[0]
                            cur.execute("""INSERT INTO offers (product_id, retailer_id, retailer_product_id, retailer_product_name,
                                          listing_id, condition, product_url, current_price, currency, in_stock, last_updated)
                                          VALUES (%s,%s,%s,%s,%s,'new',%s,%s,'TRY',%s,%s) RETURNING offer_id""",
                                        (product_id, retailer_id, clean(spec.get("retailer_product_id"))[:150],
                                         clean(spec.get("name"))[:255], listing, clean(spec.get("url")) or None,
                                         price, True if slug == "pozitif" else None, observation))
                            offer_id = cur.fetchone()[0]
                            old_updated = None
                            counts["created_listings"] += 1
                        # Never let an older daily file overwrite a newer current price.
                        if old_updated is None or observation >= old_updated:
                            cur.execute("""UPDATE offers SET current_price=%s, last_updated=%s, product_url=%s
                                           WHERE offer_id=%s""", (price, observation, clean(spec.get("url")) or None, offer_id))
                        cur.execute("""SELECT 1 FROM price_history WHERE offer_id=%s AND recorded_at=%s LIMIT 1""", (offer_id, observation))
                        if cur.fetchone() is None:
                            cur.execute("INSERT INTO price_history (offer_id, price, recorded_at) VALUES (%s,%s,%s)",
                                        (offer_id, price, observation))
                            counts["new_history_points"] += 1
                        counts["price_rows"] += 1
    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = p.parse_args()
    if not args.database_url:
        p.error("Set DATABASE_URL or pass --database-url")
    import psycopg
    with psycopg.connect(args.database_url) as conn:
        counts = import_data(conn, args.data_root)
    print("Import completed:", dict(counts))
    print("Matching note: listings are deliberately NOT merged across stores without confirmed matching output.")

if __name__ == "__main__":
    main()
