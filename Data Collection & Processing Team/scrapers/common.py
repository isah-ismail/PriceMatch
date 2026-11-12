"""
Shared pieces of the product-spec scrapers.

The inflation study's daily scrapers record prices. These scrapers record what
each product *is* (brand, colour, storage, screen size, ...) once, keyed by the
same store product id the daily price files carry:

    daily price file (UrunID / product_id / id)  ->  spec file (retailer_product_id)

Every store writes the same columns (SPEC_FIELDS) to data/clean/<store>_specs.csv.
A run merges into the existing file instead of replacing it: new products are
added, known ones are updated, and products that left the site are kept so older
price rows still join. Every row, old and new, goes through clean.clean_row()
before the file is written, so the whole file always follows the current rules.
"""

import csv
import json
import os
from posixpath import exists
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import clean

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = REPO_ROOT / "data" / "clean"


def _inflation_datas():
    """The inflation study's Datas folder: INFLATION_DATAS if set, else the first known location that exists."""
    if os.environ.get("INFLATION_DATAS"):
        return Path(os.environ["INFLATION_DATAS"])
    above = REPO_ROOT.parents[1] # to reach the InflationStudy in my computer, reconfigure the path to your own computer if you trying to run
    target = above / "DataScraping" / "InflationResearchStudy" / "InflationItems" / "Datas"

    return target


INFLATION_DATAS = _inflation_datas()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

SPEC_FIELDS = [
    "listing_id",           # one id per store listing: "<STORE>-<retailer_product_id>" (clean.py)
    "retailer",
    "retailer_product_id",  # the store's own id; join key to the daily price files
    "model_code",           # manufacturer part number, the cross-store matching key
    "name",
    "brand",
    "category",             # store's category path, "A > B > C"
    "family",               # product line, e.g. "Galaxy S26"
    "color",                # as the store writes it: "Gece Mavisi"
    "color_group",          # colour family: "Mavi" (clean.py)
    "storage_gb",
    "ram_gb",
    "screen_size_in",
    "capacity",             # non-storage capacity: "9 kg", "12000 BTU" (clean.py)
    "processor",
    "connectivity",
    "condition",            # new / display / used
    "is_bundle",
    "quality_status",       # ok / exclude (clean.py)
    "quality_reason",       # why, when there is something to say (clean.py)
    "url",
    "image_url",
    "description",          # the store's product description as one line of plain text (Pozitif only)
    "attributes",           # every raw attribute the site gave, as JSON
    "first_seen",
    "last_seen",
]


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
    return CLEAN_DIR / f"{retailer.lower()}_specs.csv"


def load_specs(path):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {row["retailer_product_id"]: row for row in csv.DictReader(f)}


def save_specs(path, rows):
    """Clean every row and write the file. Written to a .part file first, so a crash never leaves half a CSV."""
    rows = [clean.clean_row({k: ("" if row.get(k) is None else row[k]) for k in SPEC_FIELDS}) for row in rows]
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.part")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SPEC_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["category"], r["name"], r["retailer_product_id"])))
    tmp.replace(path)


def merge_and_save(retailer, rows):
    """Merge rows into data/clean/<retailer>_specs.csv; returns (path, added, updated, kept).

    A row's first_seen/last_seen default to today; a scraper that reads older daily
    files passes the files' dates instead."""
    path = specs_path(retailer)
    existing = load_specs(path)
    date = today()
    added = updated = 0
    for row in rows:
        row = {k: ("" if row.get(k) is None else row[k]) for k in SPEC_FIELDS}
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
    save_specs(path, existing.values())
    return path, added, updated, kept
