"""
Turn the per-car comparison table (car_comparison_250.xlsx, sheet "Comparison") into
250 labelled pairs in the same format as ../cosmetics/cosmetics_pairs_manual.csv.

Pairs come from the table's own groups (same brand and model):
  1. every car with its "Compared with No." car (the cheapest other car in the group),
  2. then more pairs inside the same groups, new-vs-used first, until there are 250.
Cars with no partner ("No match", "Unknown model") give no pair.

Run: python make_pairs.py car_comparison_250.xlsx cars_pairs_manual.csv
"""

import csv
import re
import sys
from itertools import combinations

from openpyxl import load_workbook

TARGET = 250
FIELDS = ["pair_id", "shop_a", "name_a", "price_a", "shop_b", "name_b", "price_b", "manual_label",
          "confidence", "manual_reason", "group", "year_a", "year_b", "condition_a", "condition_b",
          "version_a", "version_b", "row_a", "row_b"]


def fold(text):
    text = (text or "").replace("I", "ı").replace("İ", "i").lower()
    return " ".join(text.translate(str.maketrans("ığüşöç", "igusoc")).split())


def load(path):
    ws = load_workbook(path)["Comparison"]
    head = [c.value for c in ws[1]]
    cars = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        row = dict(zip(head, values))
        if row["No"] is not None:
            cars.append(row)
    return cars


def label_and_reason(a, b):
    """same only when model, version, year and new/used all agree (as in the cosmetics rule)."""
    diffs = []
    if fold(a["Model"]) != fold(b["Model"]):
        diffs.append(f"different variant: {a['Model']} vs {b['Model']}")
    if a["New or used"] != b["New or used"]:
        diffs.append(f"{a['New or used'].lower()} vs {b['New or used'].lower()}")
    if a["Year"] and b["Year"] and a["Year"] != b["Year"]:
        diffs.append(f"{a['Year']} vs {b['Year']}")
    va, vb = a["Type / specification"], b["Type / specification"]
    if va and vb and fold(va) != fold(vb):
        diffs.append(f"different version: {va} vs {vb}")

    unknown = []
    if not a["Year"] or not b["Year"]:
        unknown.append("year")
    if not va or not vb:
        unknown.append("version")

    if diffs:
        label = "different"
        confidence = "high" if any(d.startswith(("new vs", "used vs", "different version", "19", "20"))
                                   or re.match(r"\d{4} vs", d) for d in diffs) else "medium"
        reason = f"Same model ({a['Group']}) but " + "; ".join(diffs)
    elif unknown:
        # As in the cosmetics set: too little in the name to confirm -> different, low confidence.
        label, confidence = "different", "low"
        reason = (f"Same model ({a['Group']}), but the {' and '.join(unknown)} is not in the listing, "
                  "so they cannot be confirmed as the same car")
    else:
        label, confidence = "same", "high"
        reason = f"Same model, version, year and condition ({a['Group']}); mileage and seller can differ"
    return label, confidence, reason


def build(cars):
    by_no = {c["No"]: c for c in cars}
    pairs, seen = [], set()

    def add(x, y):
        key = tuple(sorted((x, y)))
        if x == y or key in seen:
            return
        seen.add(key)
        pairs.append(key)

    for c in cars:  # 1. the comparisons already in the table
        if c["Compared with No."]:
            add(c["No"], int(c["Compared with No."]))

    groups = {}
    for c in cars:
        if c["Group"] and c["Group"] != "Unknown model":
            groups.setdefault(c["Group"], []).append(c["No"])
    extra = []
    for members in groups.values():  # 2. more pairs in the same group
        for x, y in combinations(members, 2):
            if tuple(sorted((x, y))) not in seen:
                a, b = by_no[x], by_no[y]
                mixed = a["New or used"] != b["New or used"]
                extra.append((not mixed, abs(a["Price (TL)"] - b["Price (TL)"]), x, y))
    for _, _, x, y in sorted(extra):
        if len(pairs) >= TARGET:
            break
        add(x, y)

    rows = []
    for i, (x, y) in enumerate(sorted(pairs, key=lambda p: (by_no[p[0]]["Group"], p)), 1):
        a, b = by_no[x], by_no[y]
        label, confidence, reason = label_and_reason(a, b)
        rows.append({
            "pair_id": f"CAR-{i:03d}",
            "shop_a": a["Website"], "name_a": a["Original title"], "price_a": f"{a['Price (TL)']:.2f}",
            "shop_b": b["Website"], "name_b": b["Original title"], "price_b": f"{b['Price (TL)']:.2f}",
            "manual_label": label, "confidence": confidence, "manual_reason": reason, "group": a["Group"],
            "year_a": a["Year"] or "", "year_b": b["Year"] or "",
            "condition_a": a["New or used"].lower(), "condition_b": b["New or used"].lower(),
            "version_a": a["Type / specification"] or "", "version_b": b["Type / specification"] or "",
            "row_a": x, "row_b": y,
        })
    return rows


if __name__ == "__main__":
    source, out = sys.argv[1], sys.argv[2]
    rows = build(load(source))
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(len(rows), "pairs ->", out)
