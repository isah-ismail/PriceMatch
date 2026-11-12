"""
İdeal (ideal.com.tr) product specs.

The site has no product API; product cards are read from the category pages'
HTML (50 per page). The page walking follows the inflation study's daily
scraper (InflationItems/Codes/01_Food/Ideal/ideal_scraper.py, commit
a107f1664), which reads only names and prices. Each card also has what this
scraper keeps: the product id (the end of /urun/<slug>/<id>, also the cart
button's data-id), the link and the image (data-src; src is a loading gif).

The daily scraper walks all 64 category links; the 10 top-level ones
(/kategori/<name>) include their subcategories (/kategoriler/<a>/<b>), so this
one reads only those (~70 requests).

Join key: the daily file (Datas/01_Food/Ideal/ideal_prices_YYYY-MM-DD.csv) has
no id, so a price row is linked through its name; `name` is cleaned like the
daily scraper cleans it (whitespace stripped and collapsed).

Output: data/specs/ideal_specs.csv
"""

import argparse
import logging
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import brands
import catalog
import common

BASE_URL = "https://www.ideal.com.tr"
TOP_CATEGORY_RE = re.compile(r"^/kategori/[^/]+/?$")
PRODUCT_ID_RE = re.compile(r"/urun/[^/]+/(\d+)")
MAX_PAGES = 200  # per category; the largest has ~25 pages
PAGE_DELAY = 1.0

log = logging.getLogger("ideal_specs")


def get_soup(session, url, **params):
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def top_categories(session):
    """[(url, name)] of the /kategori/<name> links on the home page."""
    found = {}
    for a in get_soup(session, BASE_URL).find_all("a", href=True):
        path = a["href"].strip().replace(BASE_URL, "")
        if TOP_CATEGORY_RE.match(path):
            found.setdefault(BASE_URL + path.rstrip("/"), " ".join(a.get_text().split()))
    return list(found.items())


def parse_cards(soup, category):
    products = []
    for div in soup.find_all("div", class_="product-list"):
        a_tag = div.find("a", href=True)
        name_tag = a_tag.find("span", class_="urun-baslik") if a_tag else None
        if not name_tag:
            continue
        href = a_tag["href"].strip()
        button = div.find(attrs={"data-id": True})
        id_match = PRODUCT_ID_RE.search(href)
        img = a_tag.find("img")
        image = (img.get("data-src") or "") if img else ""
        products.append({
            "id": id_match.group(1) if id_match else (button["data-id"] if button else ""),
            "name": name_tag.text,
            "url": urljoin(BASE_URL, href),
            "image_url": urljoin(BASE_URL, image) if image else "",
            "category": category,
        })
    return products


def fetch_category(session, url, name):
    products, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        cards = parse_cards(get_soup(session, url, page=page), name)
        new = [c for c in cards if c["id"] and c["id"] not in seen]
        if not new:  # past the last page
            break
        seen.update(c["id"] for c in new)
        products.extend(new)
        time.sleep(PAGE_DELAY)
    return products


def fetch_catalogue(session):
    categories = top_categories(session)
    log.info("%d top-level categories", len(categories))
    products = []
    for i, (url, name) in enumerate(categories, 1):
        found = fetch_category(session, url, name)
        products.extend(found)
        log.info("[%d/%d] %s: %d products", i, len(categories), name, len(found))
    return products


def to_spec(product):
    name = " ".join(product["name"].split())
    return {
        "retailer": "Ideal",
        "retailer_product_id": product["id"],
        "name": name,
        "brand": brands.find_brand(name),
        "category": product["category"],
        "size": common.pack_size(name),
        "url": product["url"],
        "image_url": product["image_url"],
        "attributes": {},
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report how the latest daily file links to the specs (no requests)")
    if parser.parse_args().check:
        common.check_name_join("Ideal", "Ideal", "ideal_prices")
        return

    session = common.make_session({"Referer": BASE_URL + "/"})
    try:
        products = fetch_catalogue(session)
    except requests.RequestException as e:
        log.error("catalogue fetch failed: %s; specs not written", e)
        sys.exit(1)

    rows, seen = [], set()
    for product in products:  # a product listed in two categories is kept once
        if product["name"].strip() and product["id"] not in seen:
            seen.add(product["id"])
            rows.append(to_spec(product))
    if not rows:
        log.error("no products returned; specs not written")
        sys.exit(1)
    log.info("%d of %d found in Esra's catalog", catalog.enrich("Ideal", rows), len(rows))
    path, added, updated, kept = common.merge_and_save("Ideal", rows, common.GROCERY_FIELDS)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)
    common.check_name_join("Ideal", "Ideal", "ideal_prices")


if __name__ == "__main__":
    main()
