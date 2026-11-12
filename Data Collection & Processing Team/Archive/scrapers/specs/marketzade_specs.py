"""
Marketzade (marketzade.com) product specs.

Marketzade runs WooCommerce, like Pozitif, so this follows pozitif_specs.py.
Its public Store API (/wp-json/wc/store/v1/products) is the same one the daily
inflation scraper reads (InflationItems/Codes/01_Food/Marketzade/
marketzade_scraper.py); it returns the whole catalogue (~2,800 products) in
about 29 requests.

Join key: the daily file (Datas/01_Food/Marketzade/marketzade_YYYY-MM-DD.csv)
has had only product_name, price and the two TÜİK codes since 2026-10-26, so a
price row is linked to retailer_product_id through its name. `name` below is
cleaned exactly like the daily scraper cleans it (HTML entities and tags
removed, whitespace collapsed), so the two are equal for the same product.
Run with --check to see how many of the latest daily names link to one id.

Output: data/specs/marketzade_specs.csv
"""

import argparse
import html
import logging
import re
import sys
import time

import requests

import brands
import catalog
import common

BASE_URL = "https://marketzade.com"
STORE_API = f"{BASE_URL}/wp-json/wc/store/v1/products"
PER_PAGE = 100
MAX_PAGES = 100  # safety cap (~29 pages today)
PAGE_DELAY = 1.0

TAG_RE = re.compile(r"<[^>]+>")

log = logging.getLogger("marketzade_specs")


def clean_name(raw):
    """The daily scraper's name: entities and tags removed, whitespace collapsed."""
    return " ".join(TAG_RE.sub("", html.unescape(raw or "")).split())


def fetch_catalogue(session):
    products, page, total_pages = [], 1, None
    while page <= min(total_pages or MAX_PAGES, MAX_PAGES):
        response = session.get(STORE_API, params={"per_page": PER_PAGE, "page": page}, timeout=30)
        if response.status_code == 400 and page > 1:
            break  # past the last page
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        total_pages = total_pages or int(response.headers.get("X-WP-TotalPages") or 0) or None
        products.extend(batch)
        log.info("page %d/%s: %d products (total %d)", page, total_pages or "?", len(batch), len(products))
        page += 1
        time.sleep(PAGE_DELAY)
    return products


def attribute_map(product):
    """{'Marka': 'Focus', 'Menşei': 'Türkiye', ...}; multi-valued attributes are joined with ', '."""
    return {
        html.unescape(a["name"]): ", ".join(html.unescape(t["name"]) for t in a.get("terms") or [])
        for a in product.get("attributes") or []
    }


def to_spec(product):
    attrs = attribute_map(product)
    sku = html.unescape(product.get("sku") or "").strip()
    name = clean_name(product.get("name"))
    images = product.get("images") or []
    image_url = images[0]["src"] if images else ""
    store_brands = product.get("brands") or []
    if sku:
        attrs["sku"] = sku
    return {
        "retailer": "Marketzade",
        "retailer_product_id": product["id"],
        "barcode": common.barcode(sku) or common.image_barcode(image_url),
        "name": name,
        "brand": (html.unescape(store_brands[0]["name"]) if store_brands else attrs.get("Marka", ""))
                 or brands.find_brand(name),
        # The Store API lists categories without order; they are usually a single leaf.
        "category": " > ".join(html.unescape(c["name"]) for c in product.get("categories") or []),
        "size": common.pack_size(name),
        "url": product.get("permalink") or "",
        "image_url": image_url,
        "attributes": attrs,
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report how the latest daily file links to the specs (no requests)")
    args = parser.parse_args()
    if args.check:
        common.check_name_join("Marketzade", "Marketzade", "marketzade")
        return

    session = common.make_session({"Accept": "application/json", "Referer": BASE_URL + "/"})
    try:
        products = fetch_catalogue(session)
    except (requests.RequestException, ValueError) as e:
        log.error("catalogue fetch failed: %s; specs not written", e)
        sys.exit(1)
    if not products:
        log.error("no products returned; specs not written")
        sys.exit(1)

    rows = [to_spec(p) for p in products if p.get("id") and p.get("name")]
    log.info("%d of %d found in Esra's catalog", catalog.enrich("Marketzade", rows), len(rows))
    path, added, updated, kept = common.merge_and_save("Marketzade", rows, common.GROCERY_FIELDS)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)
    common.check_name_join("Marketzade", "Marketzade", "marketzade")


if __name__ == "__main__":
    main()
