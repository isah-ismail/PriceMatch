"""
One spelling per brand.

Stores write the same brand differently ("APPLE", "Apple", "Beats Electronics",
"Beats"). To a database those are different words, so a brand filter would miss
products. canonical() gives every brand one spelling, from brand_spelling.json.
Brands that are not in the list are kept as written.

Adapted from the grocery brand code in cimri-akakce-team1 (brands.py, itself
adapted from Esra's grocery catalogue). The grocery brand finder and the grocery
catalog lookup are left out: electronics brands come from the store (Pozitif,
Samsung) or from name_parser (Beymen).
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

SPELLING_FILE = Path(__file__).resolve().parent / "brand_spelling.json"


def fold(text):
    """Turkish-aware lower case folded to ASCII: 'İthal Süt' -> 'ithal sut'."""
    text = text.replace("I", "ı").replace("İ", "i").lower()
    text = text.translate(str.maketrans("ığüşöç", "igusoc"))
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def spellings():
    """{folded brand: the one spelling}"""
    return json.loads(SPELLING_FILE.read_text(encoding="utf-8"))["spelling"]


def canonical(brand):
    """One spelling for a brand: 'APPLE', 'Apple' -> 'Apple'; 'Beats Electronics' -> 'Beats'.

    A stray combining dot ('Sabri̇', from upper-casing 'İ' on some sites) is removed."""
    brand = " ".join((brand or "").replace("̇", "").split())
    return spellings().get(fold(brand), brand) if brand else ""
