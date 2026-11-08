"""
Fill grocery spec rows from Esra's cleaned catalog
(data/groceries/pricematch/pricematch_cleaned_all_markets.csv, 24 stores).

Her catalog and our spec files describe the same store listings: her
`original_product_name` is the name as the daily file writes it, which is
exactly our `name`. When a name appears once for the store in her catalog,
the row takes:

    offer_id                       -> catalog_offer_id (maps her ids to the store's ids)
    brand                          -> brand (her one spelling; ours when she has none)
    category (TÜİK 7-digit code)   -> tuik_code
    size, unit, pack_quantity,
    variant, data_quality_status   -> same names

Names her catalog does not have (new since her snapshot, or listed twice)
keep our own brand and the size as written in the name; catalog_offer_id
stays empty, so they are easy to find.
"""

import csv
from collections import defaultdict
from functools import lru_cache

from brands import CATALOG

TAKEN = ("size", "unit", "pack_quantity", "variant", "data_quality_status")


@lru_cache(maxsize=1)
def load():
    """{(retailer, name): [catalog rows]}"""
    index = defaultdict(list)
    if CATALOG.exists():
        with open(CATALOG, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                index[(row["retailer"], " ".join(row["original_product_name"].split()))].append(row)
    return index


def enrich(retailer, rows):
    """Fill rows in place from the catalog; returns how many were found."""
    index = load()
    found = 0
    for row in rows:
        matches = index.get((retailer, row["name"]), [])
        if len(matches) != 1:
            continue
        entry = matches[0]
        found += 1
        row["catalog_offer_id"] = entry["offer_id"]
        row["brand"] = entry["brand"] or row.get("brand", "")
        row["tuik_code"] = entry["category"]
        for key in TAKEN:
            row[key] = entry[key]
    return found
