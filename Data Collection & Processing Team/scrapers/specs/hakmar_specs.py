"""
Hakmar Express (hakmarexpress.com.tr) product specs.

Hakmar's site loads everything from a JSON API (api.hakmarexpress.com.tr), the
same one the daily inflation scraper reads (InflationItems/Codes/01_Food/
Hakmar/hakmar_scraper.py). home/initialize-v2 gives the category tree;
home/slug/<category> gives a category's product cards page by page. Each card
has the product id, barcode, brand, image, slug and category path.

Only the food and drink categories are read, chosen exactly like the daily
scraper chooses them (its MAIN_EXCLUDE / LEAF_EXCLUDE lists and keyword match,
copied below), because only those products get a daily price. ~1,200
products, ~60 requests.

Join key: the daily file (Datas/01_Food/Hakmar/hakmar_YYYY-MM-DD.csv) has no
id, so a price row is linked through its name; `name` is cleaned like the
daily scraper cleans it (whitespace stripped and collapsed).

Output: data/specs/hakmar_specs.csv
"""

import argparse
import logging
import re
import sys
import time
from urllib.parse import quote

import requests

import brands
import catalog
import common

SITE_URL = "https://www.hakmarexpress.com.tr"
API = "https://api.hakmarexpress.com.tr/api"
MAX_PAGES = 60  # per category; the largest has ~200 products
PAGE_DELAY = 1.0
# "Önerilen ürünler" blocks on a category page, outside its own product list
SKIP_COMPONENTS = {"products-with-sections"}

# From the daily scraper (hakmar_scraper.py, commit a107f1664): categories whose main or
# leaf name contains one of these words are not food, so they have no daily price.
MAIN_EXCLUDE = ["temizlik", "deterjan", "kisisel bakim", "kozmetik", "kagit", "ev",
                "evcil", "pet", "kedi", "kopek", "alkol", "sigara", "tutun", "kirtasiye",
                "elektronik", "oyuncak", "hirdavat", "tekstil", "giyim"]
LEAF_EXCLUDE = MAIN_EXCLUDE + ["bira", "sarap", "raki", "viski", "votka", "bezi", "bezleri", "mendil",
                               "sampuan", "bakim", "sac", "dis", "agiz", "parfum",
                               "deodorant", "tiras", "makyaj", "banyo", "camasir",
                               "bulasik", "hijyen", "pil", "ampul", "aksesuar", "pamuk"]

log = logging.getLogger("hakmar_specs")


def norm(s):
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    for a, b in zip("çğıöşüâî", "cgiosuai"):
        s = s.replace(a, b)
    return " ".join(re.split(r"[^a-z0-9]+", s)).strip()


def has_kw(text, kws):
    """Copied from the daily scraper: whole words, or word prefixes for keywords of 4+ letters."""
    padded = f" {norm(text)} "
    words = padded.split()
    for kw in kws:
        if " " in kw:
            if f" {kw} " in padded:
                return True
        elif any((w.startswith(kw) if len(kw) >= 4 else w == kw) for w in words):
            return True
    return False


def get_json(session, path, headers=None):
    response = session.get(f"{API}/{path}", headers=headers or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def leaf_categories(session):
    """Food leaf categories: [{'path': 'Kuru Gıda & İçecek > Makarna', 'slug': 'makarna-c', 'count': 41}, ...]"""
    tree = get_json(session, "home/initialize-v2")
    leaves = []

    def collect(category, path):
        children = category.get("categories") or []
        if not children and not has_kw(path.split(" > ")[0], MAIN_EXCLUDE) \
                and not has_kw(category["name"], LEAF_EXCLUDE):
            leaves.append({"path": path, "slug": category["slug"], "count": category.get("productCount") or 0})
        for child in children:
            collect(child, f"{path} > {child['name']}")

    for main in tree.get("category", {}).get("mainCategories", []):
        if not main.get("isDivider"):
            collect(main, main["name"])
    return leaves


def find_cards(obj, out, skip_sections=True):
    if isinstance(obj, dict):
        if skip_sections and obj.get("component") in SKIP_COMPONENTS:
            return
        if obj.get("component") == "product-card" and isinstance(obj.get("product"), dict):
            out.append(obj["product"])
            return
        for value in obj.values():
            find_cards(value, out, skip_sections)
    elif isinstance(obj, list):
        for value in obj:
            find_cards(value, out, skip_sections)


def fetch_category(session, category):
    products, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        data = get_json(session, f"home/slug/{category['slug']}?", {
            "x-encoded-url": quote(f"{category['slug']}?", safe=""),
            "x-page-number": str(page),
        })
        cards = []
        find_cards(data, cards)
        new = [card for card in cards if card.get("id") not in seen]
        if not new:
            break
        for card in new:
            seen.add(card.get("id"))
            products.append((category["path"], card))
        if category["count"] and len(products) >= category["count"]:
            break
        time.sleep(PAGE_DELAY)
    return products


def fetch_catalogue(session):
    categories = leaf_categories(session)
    log.info("%d categories, %d products listed", len(categories), sum(c["count"] for c in categories))
    products = []
    for i, category in enumerate(categories, 1):
        found = fetch_category(session, category)
        products.extend(found)
        log.info("[%d/%d] %s: %d/%d", i, len(categories), category["path"], len(found), category["count"])
        time.sleep(PAGE_DELAY)
    return products


def to_spec(category_path, card):
    name = " ".join((card.get("name") or "").split())
    brand = card.get("brand") or {}
    path = " > ".join(c["name"] for c in card.get("categories") or [] if c.get("name")) or category_path
    attrs = {k: card.get(k) for k in ("barcode", "unitCode", "packageWeight", "pricePerKg") if card.get(k) is not None}
    return {
        "retailer": "Hakmar",
        "retailer_product_id": card["id"],
        "barcode": common.barcode(card.get("barcode")),
        "name": name,
        "brand": (brand.get("name", "") if isinstance(brand, dict) else "") or brands.find_brand(name),
        "category": path,
        # Loose produce is sold by weight: "Arpacık Soğan 500 G" has packageWeight 0.5 kg.
        "size": common.pack_size(name),
        "url": f"{SITE_URL}/{card['slug']}" if card.get("slug") else "",
        "image_url": card.get("imageUrl") or "",
        "attributes": attrs,
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report how the latest daily file links to the specs (no requests)")
    if parser.parse_args().check:
        common.check_name_join("Hakmar", "Hakmar", "hakmar")
        return

    session = common.make_session({
        "Accept": "application/json, text/plain, */*",
        "Origin": SITE_URL,
        "Referer": SITE_URL + "/",
    })
    try:
        products = fetch_catalogue(session)
    except (requests.RequestException, ValueError) as e:
        log.error("catalogue fetch failed: %s; specs not written", e)
        sys.exit(1)
    if not products:
        log.error("no products returned; specs not written")
        sys.exit(1)

    rows, seen = [], set()
    for category_path, card in products:  # a product listed in two categories is kept once
        if card.get("id") and card.get("name") and card["id"] not in seen:
            seen.add(card["id"])
            rows.append(to_spec(category_path, card))
    log.info("%d of %d found in Esra's catalog", catalog.enrich("Hakmar", rows), len(rows))
    path, added, updated, kept = common.merge_and_save("Hakmar", rows, common.GROCERY_FIELDS)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)
    common.check_name_join("Hakmar", "Hakmar", "hakmar")


if __name__ == "__main__":
    main()
