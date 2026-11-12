"""
Cleaning rules for the spec files.

common.save_specs() runs clean_row() on every row of a store's file, old and new,
each time the file is written. So the file always follows the rules below, even
for products that have left the store. The rules only use the row itself, so
running them twice gives the same result.

    listing_id      "<STORE>-<retailer_product_id>": one id per store listing
    name            HTML codes decoded (&#8211; -> –), spaces collapsed
    brand           one spelling per brand (brands.canonical)
    model_code      emptied when it is a store's own code, not a part number
    quality_status  "exclude" for things that are not products, else "ok"
    quality_reason  why, separated by "; "

Re-clean every file without scraping again (no network):

    python scrapers/clean.py
"""

import html
import re
from collections import Counter

import brands

# Things a store sells that are not products. Matched on the folded name (brands.fold).
NOT_A_PRODUCT = [
    (re.compile(r"\bkargo bedeli\b"), "not_a_product: shipping fee"),
    (re.compile(r"\bodeme jetonu\b"), "not_a_product: payment token"),
    (re.compile(r"\b(garanti|hizmet) paketi\b"), "not_a_product: warranty or service package"),
]

# A manufacturer part number: capital letters, digits and . / - only ("MG8Q4TU/A",
# "SM-A185FLBDTUR", "910-001356", "ST-ADVSM"). Store codes such as "Kargo-Bedeli-2",
# "_Z536", "PTGenişletilmişGarantiPaketi" or "BeatsSesPaketi..." fail it.
PART_NUMBER_RE = re.compile(r"^[A-Z0-9][A-Z0-9./\-]*$")
# A removed code is kept in quality_reason, so re-cleaning sees it again and nothing is lost.
REMOVED_RE = re.compile(r"model_code_removed \((.*?)\)(?:; |$)")


def listing_id(retailer, retailer_product_id):
    """'Pozitif', 17870 -> 'POZITIF-17870'."""
    return f"{brands.fold(retailer).upper().replace(' ', '')}-{retailer_product_id}"


def clean_row(row):
    """The row with listing_id, name, brand, model_code and the quality columns set."""
    reasons = []

    row["listing_id"] = listing_id(row["retailer"], row["retailer_product_id"])
    row["name"] = " ".join(html.unescape(row["name"]).split())
    row["brand"] = brands.canonical(row["brand"])

    removed = REMOVED_RE.search(row.get("quality_reason") or "")
    code = row["model_code"] or (removed.group(1) if removed else "")
    if code and not PART_NUMBER_RE.match(code):
        reasons.append(f"model_code_removed ({code})")
        code = ""
    row["model_code"] = code

    folded = brands.fold(row["name"])
    excluded = [reason for pattern, reason in NOT_A_PRODUCT if pattern.search(folded)]
    row["quality_status"] = "exclude" if excluded else "ok"
    row["quality_reason"] = "; ".join(excluded + reasons)
    return row


def main():
    import common  # here, not at the top: common imports this module

    for path in sorted(common.CLEAN_DIR.glob("*_specs.csv")):
        rows = list(common.load_specs(path).values())
        common.save_specs(path, rows)
        rows = list(common.load_specs(path).values())
        reasons = Counter(r for row in rows for r in row["quality_reason"].split("; ") if r)
        removed = sum(n for r, n in reasons.items() if r.startswith("model_code_removed"))
        excluded = Counter(r for r in reasons.elements() if r.startswith("not_a_product"))
        print(f"{path.name}: {len(rows)} rows, {sum(excluded.values())} excluded, {removed} model codes removed")
        for reason, n in sorted(excluded.items()):
            print(f"    {n:5d}  {reason}")


if __name__ == "__main__":
    main()
