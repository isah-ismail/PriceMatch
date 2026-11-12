"""
Week 1 dataset audit for Team 1.

Reads the raw daily files and the spec files and writes, into data/audit/:

    store_inventory.csv    one row per store folder in the inflation data: newest file, rows, status
    field_inventory.csv    one row per reviewed source and field: inferred and recommended type,
                           empty cells, distinct values, example
    schema_summary.csv     one row per reviewed source: columns, schema group, prices, repeats, CPI codes
    electronics_quality_stats.csv
                           one row per electronics store and check
    summary.json           the numbers the reports quote

Detailed review covers 27 stores (24 grocery, Beymen, Pozitif, Samsung) and the 8 spec files.
store_inventory.csv only lists the other folders: their fields are not reviewed.

Links are checked for syntax only (http/https plus a hostname). No request is sent.
Nothing is changed in the source files. Run from any folder:

    python scrapers/audit/build_week1_audit.py --datas <InflationItems/Datas>
        [--specs <folder>] [--clean <folder>] [--stores <folder>] [--cpi <csv>] [--out <folder>]

Default paths are relative to the folder two levels above this script.
See README_ESRA_WEEK1.md for what each input is and where it comes from.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date as calendar_date
from pathlib import Path
from urllib.parse import urlsplit

csv.field_size_limit(10**9)

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ("product_name", "price", "category_number", "sub_category_number")
MISSING = {"", "nan", "none", "null", "n/a", "na", "-"}
SNAPSHOT_END = "2026-10-29"
ACTIVE_FROM = "2026-10-22"  # a store counts as active when its newest file is this recent
ELECTRONICS_DAILY = {
    "Beymen": ("08_Communication/Beymen", r"^beymen_(\d{4}-\d{2}-\d{2})\.csv$"),
    "Pozitif": ("08_Communication/PozitifTeknoloji", r"^pozitifTeknoloji_(\d{4}-\d{2}-\d{2})\.csv$"),
    "Samsung": ("08_Communication/Samsung", r"^samsung_(\d{4}-\d{2}-\d{2})\.csv$"),
}
STORE_ID_FIELDS = ("retailer_product_id", "UrunID", "product_id", "id")
PRICE_STATUSES = ("missing", "unparseable", "zero", "negative", "positive")
SUSPECT_ROUND_PRICES = (999.0, 9999.0)  # counted for review only; never treated as invalid

CODE_FIELDS = {"category_number", "sub_category_number", "tuik_code", "retailer_product_id", "UrunID",
               "product_id", "id", "sku", "model_code", "barcode", "catalog_offer_id"}
RECOMMENDED = {
    "price": "decimal", "regular_price": "decimal", "storage_gb": "decimal", "ram_gb": "decimal",
    "screen_size_in": "decimal", "pack_quantity": "integer", "in_stock": "boolean", "is_outlet": "boolean",
    "is_bundle": "boolean", "first_seen": "date", "last_seen": "date", "attributes": "json",
}
EVERY_ROW = {"product_name", "name", "price", "retailer", "first_seen", "last_seen", *STORE_ID_FIELDS}
CONDITIONAL = {"color", "storage_gb", "ram_gb", "screen_size_in", "capacity", "processor", "connectivity",
               "family", "size", "unit", "pack_quantity", "variant", "regular_price", "is_bundle"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows, bad = [], 0
        for raw in reader:
            if not raw:
                continue
            if len(raw) != len(header):
                bad += 1
            rows.append(dict(zip(header, raw)))
    return header, rows, bad


def is_missing(value):
    return value is None or value.strip().lower() in MISSING


def valid_date(value):
    """True only for a real calendar date written YYYY-MM-DD, with or without a time."""
    text = value.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}([ T].*)?$", text):
        return False
    try:
        calendar_date.fromisoformat(text[:10])
    except ValueError:
        return False
    return True


def valid_url(value):
    """True for http/https with a hostname. Syntax only: the link is not opened."""
    text = value.strip()
    if re.search(r"\s", text):
        return False
    try:
        parts = urlsplit(text)
        host = parts.hostname
    except ValueError:
        return False
    return parts.scheme.lower() in ("http", "https") and bool(host)


def is_json(value):
    text = value.strip()
    if not text.startswith(("[", "{")):
        return False
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def value_type(value):
    text = value.strip()
    if re.fullmatch(r"-?\d+", text):
        return "integer"
    if re.fullmatch(r"-?\d+\.\d+", text):
        return "decimal"
    if valid_date(text):
        return "date"
    if valid_url(text):
        return "url"
    if text.lower() in ("true", "false"):
        return "boolean"
    if is_json(text):
        return "json"
    return "text"


def field_type(values):
    counts = Counter(value_type(v) for v in values)
    if not counts:
        return "empty"
    if set(counts) == {"integer", "decimal"}:
        return "decimal"
    total = sum(counts.values())
    main, n = counts.most_common(1)[0]
    return main if n == total else f"mixed ({main} {n / total:.0%})"


def recommended_type(field):
    if field in CODE_FIELDS:
        return "text (code or ID; keep leading zeros)"
    return RECOMMENDED.get(field, "text")


def field_role(field):
    """How to read an empty cell. `conditional` fields apply to some product types only."""
    if field in EVERY_ROW:
        return "every_row"
    return "conditional" if field in CONDITIONAL else "source_dependent"


def price_format(value):
    v = value.strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return "plain_number"
    if re.fullmatch(r"-?\d+,\d{1,2}", v):
        return "decimal_comma"
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+,\d{1,2}", v):
        return "thousand_dot_decimal_comma"
    if re.search(r"₺|TL", v, re.I):
        return "with_currency_text"
    return "other" if v else "empty"


def to_price(value):
    """Number for the formats this data uses, or None. `1.769` stays 1.769: the format cannot tell."""
    v = re.sub(r"₺|TL", "", value.strip(), flags=re.I).strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return float(v)
    if re.fullmatch(r"-?\d+,\d{1,2}", v):
        return float(v.replace(",", "."))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+,\d{1,2}", v):
        return float(v.replace(".", "").replace(",", "."))
    return None


def price_status(value):
    if is_missing(value):
        return "missing"
    number = to_price(value)
    if number is None:
        return "unparseable"
    if number == 0:
        return "zero"
    return "negative" if number < 0 else "positive"


def repeat_counts(rows, header, name_field):
    """The three kinds of repeat, kept apart. A repeat is every row after the first of its group."""
    def repeats(keys):
        return sum(c - 1 for c in Counter(keys).values() if c > 1)

    out = {"full_row_duplicates": repeats(tuple(r.get(c, "") for c in header) for r in rows)}
    has_price = "price" in header
    if has_price and name_field:
        by_name = defaultdict(set)
        for r in rows:
            by_name[r[name_field].strip()].add(r["price"].strip())
        out["name_price_repeats"] = repeats((r[name_field].strip(), r["price"].strip()) for r in rows)
        out["names_with_several_prices"] = sum(1 for n, p in by_name.items() if n and len(p) > 1)
    else:
        out["name_price_repeats"] = out["names_with_several_prices"] = ""
    id_field = next((f for f in STORE_ID_FIELDS if f in header), "")
    if id_field == "product_id" and "id" in header:
        id_field = "id"
    out["store_id_field"] = id_field
    if id_field:
        pairs = [(r.get("retailer", ""), r[id_field].strip()) for r in rows if r[id_field].strip()]
        out["store_id_duplicates"] = repeats(pairs)
        out["empty_store_id"] = len(rows) - len(pairs)
    else:
        out["store_id_duplicates"] = out["empty_store_id"] = ""
    return out


def load_cpi(path):
    if path is None or not path.exists():
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {row["code"].strip() for row in csv.DictReader(f)}


def cpi_status(value, cpi):
    code = value.strip()
    if code in ("", "0"):
        return "empty_or_zero"
    if len(code) == 7 and code in cpi:
        return "item_code"
    if code in cpi:
        return "parent_code"
    if code.zfill(7) in cpi and len(code) < 7:
        return "item_code_if_zero_padded"
    return "not_in_cpi_list"


def inventory(group, store, path, date, header, rows):
    out = []
    for field in header:
        values = [r.get(field) or "" for r in rows]
        present = [v for v in values if not is_missing(v)]
        out.append({
            "source_group": group, "store": store, "file": path.name, "date": date, "field": field,
            "inferred_type": field_type(present), "recommended_type": recommended_type(field),
            "field_role": field_role(field), "rows": len(rows),
            "empty_cells": len(rows) - len(present),
            "empty_pct": round(100 * (len(rows) - len(present)) / len(rows), 2) if rows else 0,
            "distinct": len(set(present)),
            "values_with_leading_zero": sum(1 for v in present if re.fullmatch(r"0\d+", v.strip())),
            "example": present[0].replace("\n", " ")[:80] if present else "",
        })
    return out


def schema_row(group, store, path, date, header, rows, bad, cpi):
    name_field = "product_name" if "product_name" in header else ("name" if "name" in header else None)
    prices = [r.get("price") or "" for r in rows] if "price" in header else []
    statuses = Counter(price_status(p) for p in prices)
    formats = Counter(price_format(p) for p in prices)
    names = [r.get(name_field) or "" for r in rows] if name_field else []
    row = {
        "source_group": group, "store": store, "file": path.name, "date": date,
        "valid_file_date": valid_date(date), "rows": len(rows),
        "columns": len(header), "header": "|".join(header),
        "has_all_required": all(c in header for c in REQUIRED),
        "absent_required_columns": "|".join(c for c in REQUIRED if c not in header),
        "extra_columns": "|".join(c for c in header if c not in REQUIRED),
        "wrong_column_count_rows": bad,
        "empty_name": sum(is_missing(n) for n in names),
    }
    for status in PRICE_STATUSES:
        row[f"price_{status}"] = statuses[status] if prices else ""
    row["price_999_or_9999_review_only"] = (
        sum(1 for p in prices if to_price(p) in SUSPECT_ROUND_PRICES) if prices else "")
    row["price_formats"] = "; ".join(f"{k}={v}" for k, v in formats.most_common())
    row.update(repeat_counts(rows, header, name_field))
    row["category_number_lengths"] = lengths(rows, "category_number")
    row["sub_category_lengths"] = lengths(rows, "sub_category_number")
    codes = Counter()
    if cpi and "sub_category_number" in header:
        codes = Counter(cpi_status(r["sub_category_number"], cpi) for r in rows)
    for status in ("empty_or_zero", "item_code", "parent_code", "item_code_if_zero_padded", "not_in_cpi_list"):
        row[f"cpi_{status}"] = codes[status] if codes else ""
    return row


def lengths(rows, field):
    counts = Counter(len((r.get(field) or "").strip()) for r in rows if field in r)
    return "; ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def grocery_sources(datas, stores_dir):
    for path in sorted(stores_dir.glob("*.csv")):
        with open(path, newline="", encoding="utf-8-sig") as f:
            first = next(csv.DictReader(f))
        folder = first["retailer"]
        yield folder, datas / "01_Food" / folder / first["source_file"], first["scrape_date"]


def newest_daily(datas, folder, pattern):
    best = None
    for path in (datas / folder).iterdir():
        match = re.match(pattern, path.name)
        if match and match.group(1) <= SNAPSHOT_END and (best is None or match.group(1) > best[0]):
            best = (match.group(1), path)
    return best


def electronics_checks(store, spec_path, clean_path, daily):
    header, rows, bad = read_csv(spec_path)
    _, clean, _ = read_csv(clean_path)
    names = Counter(r["name"].strip() for r in rows)
    ids = {r["retailer_product_id"].strip(): r for r in rows}
    models = defaultdict(set)
    for r in rows:
        if r["model_code"].strip():
            models[r["model_code"].strip()].add(r["retailer_product_id"])

    def count(test):
        return sum(1 for r in rows if test(r))

    def not_a_number(field):
        return count(lambda r: r[field].strip() and not re.fullmatch(r"\d+(\.\d+)?", r[field].strip()))

    repeats = repeat_counts(rows, header, "name")
    checks = {
        "rows": len(rows),
        "wrong_column_count_rows": bad,
        "empty_name": count(lambda r: is_missing(r["name"])),
        "empty_retailer_product_id": repeats["empty_store_id"],
        "store_id_duplicates": repeats["store_id_duplicates"],
        "full_row_duplicates": repeats["full_row_duplicates"],
        "rows_repeating_a_name": sum(c - 1 for c in names.values() if c > 1),
        "model_code_on_several_ids": sum(1 for v in models.values() if len(v) > 1),
        "not_a_number_storage_gb": not_a_number("storage_gb"),
        "not_a_number_ram_gb": not_a_number("ram_gb"),
        "not_a_number_screen_size_in": not_a_number("screen_size_in"),
        "invalid_url_syntax": count(lambda r: r["url"].strip() and not valid_url(r["url"])),
        "invalid_image_url_syntax": count(lambda r: r["image_url"].strip() and not valid_url(r["image_url"])),
        "invalid_calendar_date": count(lambda r: not valid_date(r["first_seen"]) or not valid_date(r["last_seen"])),
        "first_seen_after_last_seen": count(lambda r: r["first_seen"] > r["last_seen"]),
        "condition_not_new": count(lambda r: r["condition"] != "new"),
        "bundles": count(lambda r: r["is_bundle"].strip().lower() == "true"),
        "clean_rows": len(clean),
        "clean_needs_review": sum(1 for r in clean if r["data_quality_status"] != "clean"),
        "clean_no_brand": sum(1 for r in clean if not r["brand"].strip()),
        "clean_no_cpi_category": sum(1 for r in clean if not r["category"].strip()),
    }
    for field in ("brand", "model_code", "category", "url", "image_url"):
        checks[f"empty_{field}"] = count(lambda r: is_missing(r[field]))
    for field in ("color", "storage_gb", "ram_gb", "screen_size_in", "capacity"):
        checks[f"empty_conditional_{field}"] = count(lambda r: is_missing(r[field]))

    d_header, d_rows, _ = read_csv(daily[1])
    id_field = repeat_counts([], d_header, "product_name")["store_id_field"]
    d_repeats = repeat_counts(d_rows, d_header, "product_name")
    statuses = Counter(price_status(r["price"]) for r in d_rows)
    groups = defaultdict(set)
    for r in d_rows:
        groups[(r["product_name"].strip(), r["price"].strip())].add(r[id_field].strip())
    joined = sum(1 for r in d_rows if r[id_field].strip() in ids)
    checks.update({
        "daily_file": daily[1].name, "daily_rows": len(d_rows),
        "daily_id_field": id_field,
        "daily_empty_store_id": d_repeats["empty_store_id"],
        "daily_store_id_duplicates": d_repeats["store_id_duplicates"],
        "daily_full_row_duplicates": d_repeats["full_row_duplicates"],
        "daily_name_price_repeats": d_repeats["name_price_repeats"],
        "daily_name_price_repeats_with_distinct_ids": sum(len(v) - 1 for v in groups.values() if len(v) > 1),
        "daily_rows_joined_to_spec": joined,
        "daily_zero_price_rows_marked_bundle": sum(
            1 for r in d_rows if price_status(r["price"]) == "zero"
            and ids.get(r[id_field].strip(), {}).get("is_bundle", "").strip().lower() == "true"),
    })
    for status in PRICE_STATUSES:
        checks[f"daily_price_{status}"] = statuses[status]
    checks["daily_price_999_or_9999_review_only"] = sum(
        1 for r in d_rows if to_price(r["price"]) in SUSPECT_ROUND_PRICES)
    return checks


def store_inventory(datas, used):
    """One row per store folder in the 13 CPI groups, read from its newest dated file."""
    out = []
    for group in sorted(p for p in datas.iterdir() if p.is_dir() and re.match(r"\d{2}_", p.name)):
        folders = defaultdict(list)
        for path in group.rglob("*.csv"):
            folders[path.parent].append(path)
        for folder, files in sorted(folders.items()):
            dated = []
            for path in files:
                match = re.search(r"\d{4}-\d{2}(-\d{2})?", path.name)
                if match and match.group(0) <= SNAPSHOT_END:
                    dated.append((match.group(0), path.name, path))
            row = {
                "group": group.name, "store_folder": folder.relative_to(group).as_posix(),
                "files": len(files), "undated_files": len(files) - len(dated),
                "newest_date": "", "newest_file": "", "rows": "", "columns": "",
                "has_all_required": "", "absent_required_columns": "", "active": False, "read_error": "",
                "reviewed_in_detail": (group.name, folder.name) in used,
            }
            if dated:
                date = max(d[0] for d in dated)
                newest = max(d for d in dated if d[0] == date)
                row.update(newest_date=date, newest_file=newest[1],
                           same_date_files=sum(1 for d in dated if d[0] == date),
                           active=date >= ACTIVE_FROM[:len(date)])
                try:
                    header, rows, _ = read_csv(newest[2])
                    row.update(rows=len(rows), columns=len(header),
                               has_all_required=all(c in header for c in REQUIRED),
                               absent_required_columns="|".join(c for c in REQUIRED if c not in header))
                except (UnicodeDecodeError, StopIteration, csv.Error) as error:
                    row["read_error"] = type(error).__name__
            row.setdefault("same_date_files", "")
            out.append(row)
    return out


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datas", type=Path, required=True)
    parser.add_argument("--specs", type=Path, default=REPO_ROOT / "data" / "specs")
    parser.add_argument("--clean", type=Path, default=REPO_ROOT / "data" / "specs_clean")
    parser.add_argument("--stores", type=Path, default=REPO_ROOT / "data" / "groceries" / "pricematch" / "stores")
    parser.add_argument("--cpi", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "audit")
    args = parser.parse_args()
    missing = [f"--{name} ({path})" for name, path in (
        ("datas", args.datas), ("specs", args.specs), ("clean", args.clean), ("stores", args.stores))
        if not path.is_dir()]
    if missing:
        raise SystemExit("input folder not found: " + ", ".join(missing))
    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)
    cpi_path = args.cpi or (args.datas.resolve().parents[1] / "Inflations" / "Codes" / "product-to-ctagory"
                            / "tuik_cpi_categories_comma.csv")
    cpi = load_cpi(cpi_path)
    if cpi is None:
        raise SystemExit(f"CPI list not found: --cpi ({cpi_path})")

    fields, schemas = [], []
    for store, path, date in grocery_sources(args.datas, args.stores):
        header, rows, bad = read_csv(path)
        fields += inventory("grocery_daily", store, path, date, header, rows)
        schemas.append(schema_row("grocery_daily", store, path, date, header, rows, bad, cpi))

    stats, electronics = [], {}
    for store, (folder, pattern) in ELECTRONICS_DAILY.items():
        daily = newest_daily(args.datas, folder, pattern)
        if daily is None:
            raise SystemExit(f"no daily file found for {store}")
        header, rows, bad = read_csv(daily[1])
        fields += inventory("electronics_daily", store, daily[1], daily[0], header, rows)
        schemas.append(schema_row("electronics_daily", store, daily[1], daily[0], header, rows, bad, cpi))
        checks = electronics_checks(store, args.specs / f"{store.lower()}_specs.csv",
                                    args.clean / f"{store.lower()}_specs_clean.csv", daily)
        electronics[store] = checks
        stats += [{"store": store, "check": k, "value": v} for k, v in checks.items()]

    for spec in sorted(args.specs.glob("*_specs.csv")):
        header, rows, bad = read_csv(spec)
        store = spec.stem.replace("_specs", "")
        last = max((r.get("last_seen") or "" for r in rows), default="")
        fields += inventory("spec_file", store, spec, last, header, rows)
        schemas.append(schema_row("spec_file", store, spec, last, header, rows, bad, cpi))

    groups = {}
    for row in schemas:
        groups.setdefault(row["header"], f"S{len(groups) + 1:02d}")
        row["schema_group"] = groups[row["header"]]

    used = {("01_Food", r["store"]) for r in schemas if r["source_group"] == "grocery_daily"}
    used |= {("08_Communication", folder.split("/")[1]) for folder, _ in ELECTRONICS_DAILY.values()}
    stores = store_inventory(args.datas, used)
    write_csv(OUT / "store_inventory.csv", stores, list(stores[0]))
    write_csv(OUT / "field_inventory.csv", fields, list(fields[0]))
    write_csv(OUT / "schema_summary.csv", schemas, list(schemas[0]))
    write_csv(OUT / "electronics_quality_stats.csv", stats, ["store", "check", "value"])

    def total(group, key):
        return sum(r[key] for r in schemas if r["source_group"] == group and r[key] != "")

    summary = {
        "snapshot_end": SNAPSHOT_END,
        "cpi_list_found": cpi is not None,
        "grocery_daily_totals": {key: total("grocery_daily", key) for key in (
            "rows", "empty_name", "price_missing", "price_unparseable", "price_zero", "price_negative",
            "price_positive", "price_999_or_9999_review_only", "full_row_duplicates", "name_price_repeats",
            "names_with_several_prices", "cpi_empty_or_zero", "cpi_item_code", "cpi_parent_code",
            "cpi_item_code_if_zero_padded", "cpi_not_in_cpi_list")},
        "inventory": {
            "folders": len(stores),
            "active": sum(1 for r in stores if r["active"]),
            "rows_in_active_newest_files": sum(r["rows"] or 0 for r in stores if r["active"]),
            "active_without_all_required": sum(1 for r in stores if r["active"] and r["has_all_required"] is False),
            "folders_without_dated_file": sum(1 for r in stores if not r["newest_date"]),
            "folders_with_several_newest_files": sum(1 for r in stores if (r["same_date_files"] or 0) > 1),
            "reviewed_in_detail": sum(1 for r in stores if r["reviewed_in_detail"]),
        },
        "groups": {v: {"header": k, "stores": [r["store"] for r in schemas if r["header"] == k]}
                   for k, v in groups.items()},
        "stores": [{k: v for k, v in r.items() if k != "header"} for r in schemas],
        "electronics": electronics,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
