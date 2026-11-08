"""
Brand from a grocery product name, and one spelling per brand.

find_brand(name): brand from a grocery product name, for stores that give no brand field
(Sariyer, HappyCenter, Ideal) and as a fallback for the others.

Adapted from Esra's grocery catalogue (commit dddf328,
scrapers/groceries/build_grocery_catalog.py: fold, name_key, load_brands,
find_brand). The brand list and overrides in brands/ are hers: 4,139 brands
from the ucuzu project, with false hits removed ("ideal", "tuna", "dereotu")
and multi-word brands added ("Dr. Oetker", "Coca-Cola").
"""

import csv
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent / "brands"
# Esra's cleaned catalog: one spelling per brand across 24 stores.
CATALOG = Path(__file__).resolve().parents[2] / "data" / "groceries" / "pricematch" / "pricematch_cleaned_all_markets.csv"


def fold(text):
    """Turkish-aware lower case folded to ASCII: 'İthal Süt' -> 'ithal sut'."""
    text = text.replace("I", "ı").replace("İ", "i").lower()
    text = text.translate(str.maketrans("ığüşöç", "igusoc"))
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def name_key(name):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9.,x' ]", " ", fold(name))).strip()


@lru_cache(maxsize=1)
def load_brands():
    """({folded brand: display name}, multi-word folded brands, longest first)"""
    data = json.loads((HERE / "brands.json").read_text(encoding="utf-8"))
    overrides = json.loads((HERE / "brand_overrides.json").read_text(encoding="utf-8"))
    remove = {fold(x) for x in overrides.get("remove", [])}
    brands = {b["key"]: b["name"] for b in data["brands"] if b["key"] not in remove}
    for name in overrides.get("add", []):
        brands[name_key(name).replace(".", "").strip()] = name
    multi_word = sorted((b for b in brands if " " in b), key=len, reverse=True)
    return brands, multi_word


def find_brand(name):
    """Longest known brand at the start of the name, else a multi-word brand inside it; '' if none."""
    brands, multi_word = load_brands()
    tokens = name_key(name).replace(",", " ").split()
    for n in range(min(4, len(tokens)), 0, -1):
        candidate = " ".join(tokens[:n])
        if candidate in brands:
            return brands[candidate]
    joined = " " + " ".join(tokens) + " "
    for brand in multi_word:
        if f" {brand} " in joined:
            return brands[brand]
    return ""


@lru_cache(maxsize=1)
def spellings():
    """{folded brand: the one spelling}: brands/brand_spelling.json first, then Esra's catalog."""
    out = {}
    if CATALOG.exists():
        with open(CATALOG, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row["brand"]:
                    out.setdefault(fold(row["brand"]), row["brand"])
    overrides = json.loads((HERE / "brand_spelling.json").read_text(encoding="utf-8"))["spelling"]
    out.update(overrides)
    return out


def canonical(brand):
    """One spelling for a brand: 'PAKMAYA', 'Pakmaya' -> 'Pakmaya'; 'Frıskıes' -> 'Friskies'.

    A stray combining dot ('Sabri̇', from upper-casing 'İ' in some sites) is removed;
    brands that no list knows are kept as written."""
    brand = " ".join((brand or "").replace("\u0307", "").split())
    return spellings().get(fold(brand), brand) if brand else ""
