"""
Cleaning and standardization rules for the spec files.

common.save_specs() runs clean_row() on every row each time a file is saved.
Running the rules twice gives the same result.

Re-clean every file without scraping (no network):
    python scrapers/clean.py
"""

import html
import re
from collections import Counter

import brands

# ------------------------------------------------------------ cleaning rules

# Things a store sells that are not products. Matched on the folded name.
NOT_A_PRODUCT = [
    (re.compile(r"\bkargo bedeli\b"), "not_a_product: shipping fee"),
    (re.compile(r"\bodeme jetonu\b"), "not_a_product: payment token"),
    (re.compile(r"\b(garanti|hizmet) paketi\b"), "not_a_product: warranty or service package"),
]

# A manufacturer part number: capital letters, digits and . / - ("MG8Q4TU/A").
# Store codes such as "Kargo-Bedeli-2" or "PT-Jeton" fail it.
PART_NUMBER_RE = re.compile(r"[A-Z0-9][A-Z0-9./-]*")

# A removed code is kept in quality_reason, so re-cleaning finds it again.
REMOVED_RE = re.compile(r"model_code_removed \((.*?)\)")

# ----------------------------------------------------- standardization rules

# (standard colour, words that mean it). A word matches the start of a word in
# the colour name, so "mavi" finds "Gece Mavisi". The first match wins.
COLOR_GROUPS = [
    ("Mavi", ["mavi", "lacivert", "blue", "iceblue", "navy", "abis", "gokyuzu", "turkuaz",
              "indigo", "sapphire", "kot", "yaban mersini"]),
    ("Yeşil", ["yesil", "green", "mint", "ada cayi", "adacayi", "haki", "khaki", "volt"]),
    ("Kırmızı", ["kirmizi", "red", "bordo", "sarap"]),
    ("Pembe", ["pembe", "pink", "rose", "rosa", "fusya", "guava", "greyfurt"]),
    ("Mor", ["mor", "purple", "violet", "lila", "lavanta", "eflatun", "murdum"]),
    ("Turuncu", ["turuncu", "orange", "mercan"]),
    ("Sarı", ["sari", "yellow"]),
    ("Kahverengi", ["kahverengi", "brown", "taba", "camel", "bronz", "tik"]),
    ("Bej", ["bej", "beige", "greige", "krem", "kum", "fildisi"]),
    ("Altın", ["altin", "gold", "sampanya"]),
    ("Gümüş", ["gumus", "silver", "inoks", "inox"]),
    ("Siyah", ["siyah", "simsiyah", "black", "gece yarisi", "midnight"]),
    ("Beyaz", ["beyaz", "white", "yildiz isigi", "starlight"]),
    ("Gri", ["gri", "gray", "grey", "graphite", "antrasit", "grafit", "titanyum", "naturel"]),
    ("Şeffaf", ["seffaf", "transparent", "renksiz"]),
    ("Çok Renkli", ["gokkusagi", "renkli"]),
]

CELL_RE = re.compile(r"\bCell\b")                            # "Wi-Fi + Cell"
BTU_RE = re.compile(r"(\d[\d.,]*)\s*btu\S*", re.IGNORECASE)  # "24.000 Btu/Saat"

# -------------------------------------------------------------------- helpers


def listing_id(retailer, retailer_product_id):
    """'Pozitif', 17870 -> 'POZITIF-17870'."""
    return f"{brands.fold(retailer).upper().replace(' ', '')}-{retailer_product_id}"


def color_group(color):
    """'Gece Mavisi' -> 'Mavi'; '' when no group matches."""
    words = " " + brands.fold(color)
    for group, keywords in COLOR_GROUPS:
        if any(" " + keyword in words for keyword in keywords):
            return group
    return ""


def standard_capacity(text):
    """'24.000 Btu/Saat' / '24,000 BTU/hr' -> '24000 BTU'. kg and L stay as they are."""
    return BTU_RE.sub(lambda m: re.sub(r"[.,]", "", m.group(1)) + " BTU", text)

# ------------------------------------------------------------- clean one row


def clean_row(row):
    # Cleaning
    row["listing_id"] = listing_id(row["retailer"], row["retailer_product_id"])
    row["name"] = " ".join(html.unescape(row["name"]).split())
    row["brand"] = brands.canonical(row["brand"])

    # Standardization
    row["color_group"] = color_group(row["color"])
    row["connectivity"] = CELL_RE.sub("Cellular", row["connectivity"])
    row["capacity"] = standard_capacity(row["capacity"])

    # Model code: keep only real part numbers
    reasons = []
    removed = REMOVED_RE.search(row["quality_reason"])
    code = row["model_code"] or (removed.group(1) if removed else "")
    if code and not PART_NUMBER_RE.fullmatch(code):
        reasons.append(f"model_code_removed ({code})")
        code = ""
    row["model_code"] = code

    # Not a product
    folded = brands.fold(row["name"])
    excluded = [reason for pattern, reason in NOT_A_PRODUCT if pattern.search(folded)]
    row["quality_status"] = "exclude" if excluded else "ok"
    row["quality_reason"] = "; ".join(excluded + reasons)
    return row

# ----------------------------------------------------------------------- main


def main():
    import common  # here, not at the top: common imports this module

    for path in sorted(common.CLEAN_DIR.glob("*_specs.csv")):
        common.save_specs(path, common.load_specs(path).values())
        rows = list(common.load_specs(path).values())

        reasons = Counter(r for row in rows for r in row["quality_reason"].split("; ") if r)
        removed = sum(n for r, n in reasons.items() if r.startswith("model_code_removed"))
        excluded = {r: n for r, n in reasons.items() if r.startswith("not_a_product")}
        colors = [row for row in rows if row["color"]]
        grouped = sum(1 for row in colors if row["color_group"])

        print(f"{path.name}: {len(rows)} rows, {sum(excluded.values())} excluded, "
              f"{removed} model codes removed, {grouped} of {len(colors)} colours grouped")
        for reason, n in sorted(excluded.items()):
            print(f"    {n:5d}  {reason}")


if __name__ == "__main__":
    main()
