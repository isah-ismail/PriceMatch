"""
Happy Center (happycenter.com.tr) product specs.

The site has no product API; product cards are read from the category pages'
HTML. The crawling code in happycenter/ is copied from the inflation study's
daily scraper (InflationItems/Codes/01_Food/HappyCenter, commit 70d13e445):
it walks the "Reyon Seçiniz" tree under Kuru Gıda and Taze Ürünler down to the
leaf aisles, and skips a parent aisle when its children already cover it. Each
card gives the product id (productCard<id>), name, link and image.

Like the daily scraper, this reads only the food aisles (the ones that have
daily prices); ~9,000 products in about the same number of requests as one
daily run.

Join key: the daily file (Datas/01_Food/HappyCenter/happycenter_YYYY-MM-DD.csv)
has no id, so a price row is linked through its name; `name` is exactly the
daily scraper's name (the same clean() is used).

Output: data/specs/happycenter_specs.csv
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import brands
import catalog
import common

sys.path.insert(0, str(Path(__file__).resolve().parent / "happycenter"))
import happycenter_scraper as hc  # noqa: E402

log = logging.getLogger("happycenter_specs")


def fetch_catalogue():
    """{product id: card with its aisle path}, walked like the daily scraper's main()."""
    groups = hc.get_start_groups()
    log.info("%d start groups", len(groups))
    rows, cat_log, visited = {}, [], set()
    for url, path in groups:
        if hc.norm(path.split(" > ")[-1]) in visited:
            continue
        log.info("[%s]", path)
        hc.walk(url, path, 0, visited, rows, cat_log)
        time.sleep(hc.SLEEP)
    return rows


def to_spec(product):
    name = " ".join(product["name"].split())
    image_url = "" if product["image_url"].endswith("/noimage.png") else product["image_url"]
    return {
        "retailer": "HappyCenter",
        "retailer_product_id": product["id"],
        # Many images are named after the barcode: .../8690504107453-F6DB8.png
        "barcode": common.image_barcode(image_url),
        "name": name,
        "brand": brands.find_brand(name),
        "category": product["path"],
        "size": common.pack_size(name),
        "url": product["url"],
        "image_url": image_url,
        "attributes": {},
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report how the latest daily file links to the specs (no requests)")
    if parser.parse_args().check:
        common.check_name_join("HappyCenter", "HappyCenter", "happycenter")
        return

    try:
        products = fetch_catalogue()
    except SystemExit as e:  # the copied code exits when the home page does not open
        log.error("catalogue fetch failed: %s; specs not written", e)
        sys.exit(1)
    rows = [to_spec(p) for p in products.values() if p.get("id") and p.get("name")]
    if not rows:
        log.error("no products returned; specs not written")
        sys.exit(1)
    log.info("%d of %d found in Esra's catalog", catalog.enrich("HappyCenter", rows), len(rows))
    path, added, updated, kept = common.merge_and_save("HappyCenter", rows, common.GROCERY_FIELDS)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)
    common.check_name_join("HappyCenter", "HappyCenter", "happycenter")


if __name__ == "__main__":
    main()
