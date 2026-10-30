"""
Sarıyer Market (sariyermarket.com) product specs.

The site is nopCommerce; products load through a POST to
/Catalog/OBAjaxFilterProducts that needs the page's anti-forgery token. The
fetching code in sariyer/ is copied from the inflation study's daily scraper
(InflationItems/Codes/01_Food/Sariyer, commit a107f1664) with two small
changes, described at the top of each file.

The daily scraper walks all 274 menu categories; parents include their
subcategories' products, so this one reads only the 14 top-level ones (~400
requests instead of ~1,000).

Join key: the daily file (Datas/01_Food/Sariyer/sariyermarket_YYYY-MM-DD.csv)
has no id, so a price row is linked through its name; `name` is cleaned like
the daily scraper cleans it (whitespace stripped and collapsed).

Output: data/specs/sariyer_specs.csv
"""

import argparse
import logging
import sys
from pathlib import Path

import requests

import brands
import common

sys.path.insert(0, str(Path(__file__).resolve().parent / "sariyer"))
import category_fetcher  # noqa: E402
import product_fetcher  # noqa: E402

PAGE_DELAY = 1.0

log = logging.getLogger("sariyer_specs")


def fetch_catalogue():
    session = product_fetcher._make_session()
    categories = [c for c in category_fetcher.fetch_categories(session) if c["level"] == 1]
    log.info("%d top-level categories", len(categories))
    products = []
    for i, category in enumerate(categories, 1):
        found = product_fetcher.fetch_products_for_category(category, session, delay=PAGE_DELAY)
        products.extend(found)
        log.info("[%d/%d] %s: %d products", i, len(categories), category["name"], len(found))
    return products


def to_spec(product):
    name = " ".join((product.get("name") or "").split())
    sku = product.get("sku") or ""
    return {
        "retailer": "Sariyer",
        "retailer_product_id": product["id"],
        "barcode": common.barcode(sku),
        "name": name,
        "brand": brands.find_brand(name),
        "category": product.get("category") or "",
        "size": common.pack_size(name),
        "url": product.get("product_url") or "",
        "image_url": product.get("image_url") or "",
        "attributes": {k: v for k, v in (("sku", sku), ("unit", product.get("unit"))) if v},
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report how the latest daily file links to the specs (no requests)")
    if parser.parse_args().check:
        common.check_name_join("Sariyer", "Sariyer", "sariyermarket")
        return

    try:
        products = fetch_catalogue()
    except (requests.RequestException, RuntimeError, ValueError) as e:
        log.error("catalogue fetch failed: %s; specs not written", e)
        sys.exit(1)

    rows, seen = [], set()
    for product in products:  # a product listed in two categories is kept once
        if product.get("id") and product.get("name") and product["id"] not in seen:
            seen.add(product["id"])
            rows.append(to_spec(product))
    if not rows:
        log.error("no products returned; specs not written")
        sys.exit(1)
    path, added, updated, kept = common.merge_and_save("Sariyer", rows, common.GROCERY_FIELDS)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)
    common.check_name_join("Sariyer", "Sariyer", "sariyermarket")


if __name__ == "__main__":
    main()
