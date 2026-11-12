"""
Pozitif Teknoloji (pt.com.tr) product specs.

pt.com.tr runs WooCommerce. Its public Store API
(/wp-json/wc/store/v1/products) is the same one the daily inflation
scraper reads; it returns the whole catalogue (~1,330 products) in about
14 requests. Every colour/storage variant is its own product with its own
id and permalink, and the specs come as structured attributes:

    Renk -> color, Depolama / Kapasite -> storage, Bellek -> RAM,
    Ekran Boyutu -> screen size, İşlemci -> processor,
    Bağlantı Türü / Bağlantı Özellikleri -> connectivity,
    Ürün Durumu -> condition (Yeni / Teşhir / İkinci El)

The product's HTML description (a spec table, then paragraphs) is kept as
one line of plain text: "Çip: M5 Pro çip, ... | Bellek: 48 GB ... | 2026 yılında ...".

Join key: retailer_product_id == `product_id` in
Datas/08_Communication/PozitifTeknoloji/pozitifTeknoloji_YYYY-MM-DD.csv.

Output: data/clean/pozitif_specs.csv (cleaned by clean.py on save)
"""

import html
import logging
import re
import sys
import time

import requests

import common

BASE_URL = "https://www.pt.com.tr"
STORE_API = f"{BASE_URL}/wp-json/wc/store/v1/products"
PER_PAGE = 100
MAX_PAGES = 100  # safety cap (~14 pages today)
PAGE_DELAY = 1.0

CONDITIONS = {"Yeni": "new", "Teşhir": "display", "İkinci El": "used"}
# Outlet SKUs carry the condition as a suffix: "MTP03TU/A-Teşhir", "MC7W4TU/A-KutuHasarlı".
CONDITION_SUFFIX_RE = re.compile(r"-(Teşhir|İkinci\s?El|Kutu\s?Hasarlı)$", re.IGNORECASE)

# Description HTML -> one line: table cells joined with ": ", rows, headings and paragraphs with " | ".
CELL_BREAK_RE = re.compile(r"</t[dh]>\s*<t[dh][^>]*>", re.IGNORECASE)
BLOCK_BREAK_RE = re.compile(r"</(?:p|h\d|tr|li|div|table)>|<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SEPARATORS_RE = re.compile(r"\s*\|\s*(?:\|\s*)*")

log = logging.getLogger("pozitif_specs")


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
    """{'Renk': 'Siyah', 'Depolama': '128GB', ...}; multi-valued attributes are joined with ', '."""
    return {
        html.unescape(a["name"]): ", ".join(html.unescape(t["name"]) for t in a.get("terms") or [])
        for a in product.get("attributes") or []
    }


def category_path(product):
    # gtm4wp lists the categories top-down (Outlet > iPhone Outlet > iPhone 15 Outlet);
    # the plain `categories` list has no order.
    item = ((product.get("extensions") or {}).get("gtm4wp") or {}).get("item") or {}
    levels = [item.get("item_category")] + [item.get(f"item_category{i}") for i in range(2, 6)]
    path = [html.unescape(level) for level in levels if level]
    if not path:
        path = [html.unescape(c["name"]) for c in product.get("categories") or []][:1]
    return " > ".join(path)


def plain_text(description):
    """'<tr><td>Çip</td><td>M5 Pro</td></tr><p>Text</p>' -> 'Çip: M5 Pro | Text'."""
    text = CELL_BREAK_RE.sub(": ", description or "")
    text = BLOCK_BREAK_RE.sub(" | ", text)
    text = " ".join(html.unescape(TAG_RE.sub(" ", text)).split())
    return SEPARATORS_RE.sub(" | ", text).strip(" |")


def to_spec(product):
    attrs = attribute_map(product)
    sku = html.unescape(product.get("sku") or "")
    images = product.get("images") or []
    brands = product.get("brands") or []
    storage_text = attrs.get("Depolama") or attrs.get("Kapasite") or ""
    name = " ".join(html.unescape(product.get("name") or "").split())
    condition = CONDITIONS.get(attrs.get("Ürün Durumu"), "new")
    if condition == "new" and "teşhir" in name.lower():  # "... Pt-Kılıf-01-Teşhir" with no Ürün Durumu
        condition = "display"
    return {
        "retailer": "Pozitif",
        "retailer_product_id": product["id"],
        "model_code": CONDITION_SUFFIX_RE.sub("", sku),
        "name": name,
        "brand": html.unescape(brands[0]["name"]) if brands else "",
        "category": category_path(product),
        "family": "",
        "color": attrs.get("Renk", ""),
        "storage_gb": common.storage_gb(storage_text),
        "ram_gb": common.storage_gb(attrs.get("Bellek")),
        "screen_size_in": common.screen_size_in(attrs.get("Ekran Boyutu")),
        "capacity": "",
        "processor": attrs.get("İşlemci", ""),
        "connectivity": attrs.get("Bağlantı Türü") or attrs.get("Bağlantı Özellikleri") or "",
        "condition": condition,
        "is_bundle": product.get("type") == "bundle",
        "url": product.get("permalink") or "",
        "image_url": images[0]["src"] if images else "",
        "description": plain_text(product.get("description")),
        "attributes": {**attrs, "sku": sku},
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
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
    path, added, updated, kept = common.merge_and_save("Pozitif", rows)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)


if __name__ == "__main__":
    main()
