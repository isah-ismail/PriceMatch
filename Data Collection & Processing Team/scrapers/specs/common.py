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


def merge_and_save(retailer, rows):
    """Merge rows into data/specs/<retailer>_specs.csv; returns (path, added, updated, kept).

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

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.part")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SPEC_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=lambda r: (r["category"], r["name"], r["retailer_product_id"])))
    tmp.replace(path)
    return path, added, updated, kept
