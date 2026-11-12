"""
Samsung Türkiye (samsung.com/tr) product specs.

Uses the public Product Finder v2 (pfv2) JSON API that samsung.com/tr's
category pages call, the same endpoint the daily inflation scraper reads.
Each category returns product *families* ("Galaxy A07s"); each family has a
modelList with one entry per real SKU (one per colour / storage / size).
A SKU's variant options come as fmyChipList "chips":

    COLOR -> color, MOBILE MEMORY / MEMORY MEMORY -> storage,
    TV SIZE / MONITOR SCREEN SIZE -> screen size,
    *CAPACITY*, DISHWASHER PLACE, OTHER (air conditioner BTU) -> capacity

The API has no RAM or processor, so those stay empty.

Join key: retailer_product_id == `id` in
Datas/08_Communication/Samsung/samsung_YYYY-MM-DD.csv (Samsung's modelCode).

Output: data/specs/samsung_specs.csv
"""

import logging
import random
import sys
import time

import requests

import common

BASE_URL = "https://www.samsung.com"
PRODUCT_FINDER_URL = "https://searchapi.samsung.com/v6/front/b2c/product/finder/newhybris"
PAGE_SIZE = 500  # the API's tested maximum; every category fits in one page today
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": f"{BASE_URL}/tr/",
    "Origin": BASE_URL,
    "X-Requested-With": "XMLHttpRequest",
}

# Top-level categories (pfCategoryTypeCode), as in the inflation scraper's config.py.
CATEGORIES = [
    ("01010000", "Smartphones"),
    ("01020000", "Tablets"),
    ("01030000", "Watches"),
    ("01040000", "Audio Sound"),
    ("01050000", "Mobile Accessories"),
    ("01090000", "Rings"),
    ("04010000", "TVs"),
    ("04020000", "Lifestyle TVs"),
    ("04030000", "TV Accessories"),
    ("04050000", "Projectors"),
    ("05010000", "Audio Devices"),
    ("07010000", "Monitors"),
    ("09010000", "Memory & Storage"),
    ("08010000", "Washers & Dryers"),
    ("08030000", "Refrigerators"),
    ("08040000", "Air Purifier"),
    ("08050000", "Air Conditioners"),
    ("08070000", "Vacuum Cleaners"),
    ("08080000", "Cooking Appliances"),
    ("08090000", "Dishwashers"),
    ("08110000", "Microwave Ovens"),
]

STORAGE_CHIPS = {"MOBILE MEMORY", "MEMORY MEMORY"}
SCREEN_CHIPS = {"TV SIZE", "MONITOR SCREEN SIZE"}
CAPACITY_CHIPS = {"WASHER AND DRYERS CAPACITY", "REFRIGERATORS CAPACITY", "DISHWASHER PLACE",
                  "AIR CONDITIONER COOLING CAPACITY", "OTHER"}

log = logging.getLogger("samsung_specs")


def fetch_families(session, type_code):
    families, start = [], 1
    while True:
        params = {"type": type_code, "siteCode": "tr", "start": start, "num": PAGE_SIZE,
                  "sort": "newest", "onlyFilterInfoYN": "N"}
        response = session.get(PRODUCT_FINDER_URL, params=params, timeout=30)
        response.raise_for_status()
        result = (response.json().get("response") or {}).get("resultData") or {}
        batch = result.get("productList") or []
        families.extend(batch)
        total = int((result.get("common") or {}).get("totalRecord") or 0)
        if not batch or len(families) >= total:
            return families
        start += PAGE_SIZE
        time.sleep(random.uniform(1, 2))


def absolute(url, base):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return base + url
    return url


def to_spec(model, family, category):
    chips = {c["fmyChipType"]: (c.get("fmyChipLocalName") or c.get("fmyChipName") or "").strip()
             for c in model.get("fmyChipList") or []}
    storage = next((chips[k] for k in STORAGE_CHIPS if k in chips), "")
    screen = next((chips[k] for k in SCREEN_CHIPS if k in chips), "")
    capacity = next((chips[k] for k in CAPACITY_CHIPS if k in chips), "")
    attributes = dict(chips)
    if model.get("modelName"):
        attributes["modelName"] = model["modelName"]  # e.g. "SM-A077F/DS", how other stores often write it
    return {
        "retailer": "Samsung",
        "retailer_product_id": model["modelCode"],
        "model_code": model["modelCode"],
        "name": " ".join((model.get("displayName") or family.get("fmyMarketingName") or "").split()),
        "brand": "Samsung",
        "category": " > ".join(x for x in (category, family.get("categorySubTypeName")) if x),
        "family": family.get("fmyMarketingName") or "",
        "color": chips.get("COLOR", ""),
        "storage_gb": common.storage_gb(storage),
        "ram_gb": None,
        "screen_size_in": common.screen_size_in(screen),
        "capacity": capacity,
        "processor": "",
        "connectivity": "",
        "condition": "new",
        "is_bundle": model.get("packageYN") == "Y",
        "url": absolute(model.get("pdpUrl"), BASE_URL),
        "image_url": absolute(model.get("largeUrl") or model.get("thumbUrl"), BASE_URL),
        "attributes": attributes,
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    session = common.make_session(HEADERS)

    rows, seen = [], set()
    for type_code, category in CATEGORIES:
        try:
            families = fetch_families(session, type_code)
        except (requests.RequestException, ValueError) as e:
            log.error("%s: failed after retries: %s; specs not written", category, e)
            sys.exit(1)
        count = 0
        for family in families:
            for model in family.get("modelList") or []:
                code = model.get("modelCode")
                if not code or code in seen:  # a SKU can sit in two categories
                    continue
                seen.add(code)
                rows.append(to_spec(model, family, category))
                count += 1
        log.info("%s: %d families, %d SKUs", category, len(families), count)
        time.sleep(random.uniform(1, 2))

    if not rows:
        log.error("no products returned; specs not written")
        sys.exit(1)
    path, added, updated, kept = common.merge_and_save("Samsung", rows)
    log.info("%s: %d new, %d updated, %d no longer listed (kept)", path, added, updated, kept)


if __name__ == "__main__":
    main()
