"""
Shared pieces of the product-spec scrapers.

The daily inflation scrapers (InflationResearchStudy/InflationItems) record
prices. These scrapers record what each product *is* (brand, colour,
storage, screen size, ...) once, keyed by the same retailer product id the
daily CSVs carry, so a daily price row can be joined to its variant:

    daily CSV (product_id / id)  ->  specs CSV (retailer_product_id)

Every retailer writes the same columns (SPEC_FIELDS) to
data/specs/<retailer>_specs.csv. A run merges into the existing file
instead of replacing it: new products are added, known ones are updated,
and products that left the site are kept so older price rows still join.
"""

import csv
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "data" / "specs"
# The inflation study's daily price CSVs. Default: the study folder on the Desktop
# next to jkjk/; set INFLATION_DATAS when it lives elsewhere.
INFLATION_DATAS = Path(os.environ.get("INFLATION_DATAS")
                       or REPO_ROOT.parents[1] / "InflationResearchStudy" / "InflationItems" / "Datas")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

SPEC_FIELDS = [
    "retailer",
    "retailer_product_id",  # join key to the daily price CSV
    "model_code",           # manufacturer part number / SKU, the cross-store matching key
    "name",
    "brand",
    "category",             # retailer's category path, "A > B > C"
    "family",               # product line, e.g. "Galaxy S26"
    "color",
    "storage_gb",
    "ram_gb",
    "screen_size_in",
    "capacity",             # non-storage capacity as written: "9 kg", "508 L", "12.000 Btu/Saat"
    "processor",
    "connectivity",
    "condition",            # new / display / used
    "is_bundle",
    "url",
    "image_url",
    "attributes",           # every raw attribute the site gave, as JSON
    "first_seen",
    "last_seen",
]

# Grocery stores write a shorter set: the electronics columns are always empty for them.
GROCERY_FIELDS = [
    "retailer",
    "retailer_product_id",  # the store's own id
    "barcode",              # EAN-13 / EAN-8 / UPC, the cross-store matching key; '' when the store has none
    "name",                 # exactly as the store's daily inflation file writes it (the join key)
    "brand",
    "category",             # store's category path, "A > B"
    "size",                 # pack size as written in the name: "500 Gr", "1 L", "6x200 ml"
    "url",
    "image_url",
    "attributes",           # every raw attribute the site gave, as JSON
    "first_seen",
    "last_seen",
]

log = logging.getLogger("specs")


def make_session(headers=None):
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "tr-TR,tr;q=0.9"})
    session.headers.update(headers or {})
    return session


def today():
    return datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")


STORAGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(TB|GB)\b", re.IGNORECASE)
INCH_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:inç|inch|in\b|\"|”|'')", re.IGNORECASE)


def storage_gb(text):
    """'128GB' / '1 TB' / '1TB' -> 128 / 1024 / 1024; None when there is no size."""
    match = STORAGE_RE.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    if match.group(2).upper() == "TB":
        value *= 1024
    return int(value) if value.is_integer() else value


def screen_size_in(text):
    """'13.6 inç' / '65"' / '32”' -> 13.6 / 65 / 32; None for other units (e.g. '46mm')."""
    match = INCH_RE.search(text or "")
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    return int(value) if value.is_integer() else value


def specs_path(retailer):
    return SPECS_DIR / f"{retailer.lower()}_specs.csv"


def load_specs(path):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {row["retailer_product_id"]: row for row in csv.DictReader(f)}


def merge_and_save(retailer, rows, fields=SPEC_FIELDS):
    """Merge rows into data/specs/<retailer>_specs.csv; returns (path, added, updated, kept).

    A row's first_seen/last_seen default to today; a scraper that reads older daily
    files passes the files' dates instead. Grocery scrapers pass fields=GROCERY_FIELDS."""
    path = specs_path(retailer)
    existing = load_specs(path)
    date = today()
    added = updated = 0
    for row in rows:
        row = {k: ("" if row.get(k) is None else row[k]) for k in fields}
        if isinstance(row["attributes"], dict):
            row["attributes"] = json.dumps(row["attributes"], ensure_ascii=False, sort_keys=True)
        key = str(row["retailer_product_id"])
        old = existing.get(key)
        first, last = row["first_seen"] or date, row["last_seen"] or date
        row["first_seen"] = min(old["first_seen"], first) if old else first
        row["last_seen"] = max(old["last_seen"], last) if old else last
        if old:
            updated += 1
        else:
            added += 1
        existing[key] = row
    kept = len(existing) - added - updated

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.part")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=lambda r: (r["category"], r["name"], r["retailer_product_id"])))
    tmp.replace(path)
    return path, added, updated, kept


# ── Groceries ────────────────────────────────────────────────────────────────
# Since 2026-10-26 the inflation study's grocery files hold only
# product_name, price and the two TÜİK codes, so a daily price row is linked
# to its retailer_product_id through its name. Each grocery scraper writes
# `name` exactly as the store's daily scraper does, and check_name_join()
# measures how well that works on the latest daily file.

BARCODE_RE = re.compile(r"^(\d{8}|\d{12,14})$")
# Pack size as written in grocery names: "5 Kg", "500 Gr", "6x200 ml", "1.44 Ml", "12'li".
PACK_SIZE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?\s*(?:x\s*\d+(?:[.,]\d+)?\s*)?(?:kg|gr|g|mg|lt|l|ml|cl|cc|adet|yaprak)\b"
    r"|\d+\s*['’]?\s*(?:li|lı|lu|lü)\b)",
    re.IGNORECASE,
)


# Some stores name product images after the barcode: .../8690560355218.jpg (Marketzade),
# .../8690504107453-F6DB8.png (HappyCenter).
IMAGE_BARCODE_RE = re.compile(r"/(\d{13})(?:-[A-Za-z0-9]+)?\.\w+(?:\?.*)?$")


def valid_check_digit(code):
    """GS1 check digit (EAN-8, UPC-A, EAN-13, GTIN-14): from the right, digits are weighted 3, 1, 3, ..."""
    digits = [int(c) for c in code]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1])))
    return (10 - total % 10) % 10 == digits[-1]


def barcode(code):
    """code when it is a manufacturer barcode (8, 12, 13 or 14 digits with a valid check digit), else ''.

    Barcodes match the same product at other stores; stores' own codes ("91562",
    produce PLUs like "1036223", 8-digit SKUs like "74591012") do not."""
    code = (code or "").strip()
    return code if BARCODE_RE.match(code) and valid_check_digit(code) else ""


def image_barcode(image_url):
    """The barcode an image file is named after, or ''."""
    match = IMAGE_BARCODE_RE.search(image_url or "")
    return barcode(match.group(1)) if match else ""


def pack_size(name):
    """The last pack size in a name: 'Pınar Süt 1 L' -> '1 L'; '' when there is none."""
    sizes = PACK_SIZE_RE.findall(name or "")
    return " ".join(sizes[-1].split()) if sizes else ""


def check_name_join(retailer, store_folder, prefix):
    """Log how many names in the latest daily grocery file link to exactly one product id."""
    folder = INFLATION_DATAS / "01_Food" / store_folder
    files = sorted(folder.glob(f"{prefix}_????-??-??.csv"))
    if not files:
        log.error("no daily %s file under %s (set INFLATION_DATAS)", retailer, folder)
        return
    ids_per_name = {}
    for row in load_specs(specs_path(retailer)).values():
        ids_per_name[row["name"]] = ids_per_name.get(row["name"], 0) + 1
    with open(files[-1], newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        column = "product_name" if "product_name" in reader.fieldnames else "price_name"
        names = [" ".join(row[column].split()) for row in reader]
    unique = sum(1 for n in names if ids_per_name.get(n) == 1)
    ambiguous = sum(1 for n in names if ids_per_name.get(n, 0) > 1)
    missing = [n for n in names if n not in ids_per_name]
    log.info("%s: %d names, %d link to one id (%.1f%%), %d ambiguous, %d not in specs",
             files[-1].name, len(names), unique, 100 * unique / max(len(names), 1), ambiguous, len(missing))
    for n in missing[:10]:
        log.info("  not in specs: %s", n)
