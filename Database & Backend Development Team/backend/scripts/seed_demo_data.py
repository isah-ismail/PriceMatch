"""Load demo data into the PriceMatch database.

Sources
-------
* Team 01's product spec files  ``Data Collection & Processing Team/data/specs/*_specs.csv``
  (what each store listing *is*: name, brand, model code, colour, storage, url, image).
* The inflation study's daily price files ``InflationItems/Datas/08_Communication/<Store>/``
  (what it *costs* each day). Joined on the store's own product id.

What it writes
--------------
retailers, brands, categories, products, offers, price_history — i.e. Fatima's schema.

Product identity (TEMPORARY until Team 02 delivers the matcher)
----------------------------------------------------------------
Listings that share a manufacturer ``model_code`` (plus the same ``condition``)
are treated as the same canonical product. Everything else becomes its own
product. This is exactly the "match on model_code first" baseline Team 01
recommends; Team 02's output will replace it (see ../INTEGRATION.md).

Usage
-----
    python scripts/seed_demo_data.py --reset                 # uses DATABASE_URL from .env
    python scripts/seed_demo_data.py --reset --days 30 \
        --datas /path/to/InflationResearchStudy/InflationItems/Datas

Without ``--datas`` (or INFLATION_DATAS) only the spec files are used and no
prices are available, so no offers can be created. Run with the daily files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

# Make ``app`` importable when run as ``python scripts/seed_demo_data.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, insert, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import Brand, Category, Offer, PriceHistory, Product, Retailer  # noqa: E402

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]  # .../PriceMatch
DEFAULT_SPECS_DIR = REPO_ROOT / "Data Collection & Processing Team" / "data" / "specs"
ISTANBUL = ZoneInfo("Europe/Istanbul")

# retailer key in spec files -> (display name, website, daily folder, file prefix, id column, price column, in_stock column)
RETAILERS = {
    "Pozitif": {
        "name": "Pozitif Teknoloji",
        "website_url": "https://www.pt.com.tr",
        "folder": "08_Communication/PozitifTeknoloji",
        "prefix": "pozitifTeknoloji_",
        "id_col": "product_id",
        "price_col": "price",
        "stock_col": "in_stock",
    },
    "Samsung": {
        "name": "Samsung",
        "website_url": "https://www.samsung.com/tr",
        "folder": "08_Communication/Samsung",
        "prefix": "samsung_",
        "id_col": "id",
        "price_col": "price",
        "stock_col": None,
    },
    "Beymen": {
        "name": "Beymen",
        "website_url": "https://www.beymen.com",
        "folder": "08_Communication/Beymen",
        "prefix": "beymen_",
        "id_col": "UrunID",
        "price_col": "price",
        "stock_col": None,
    },
}

DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.csv$")


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ reading


def read_specs(specs_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(specs_dir.glob("*_specs.csv")):
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("retailer") in RETAILERS and row.get("retailer_product_id"):
                    rows.append(row)
        log(f"  specs: {path.name}")
    return rows


def daily_files(datas: Path, cfg: dict, days: int) -> list[tuple[str, Path]]:
    """Latest ``days`` daily files for one store, oldest first. Only exact ``<prefix>YYYY-MM-DD.csv``."""
    folder = datas / cfg["folder"]
    found: list[tuple[str, Path]] = []
    for path in folder.glob(f"{cfg['prefix']}*.csv"):
        m = DATE_RE.search(path.name)
        if m and path.name == f"{cfg['prefix']}{m.group(1)}.csv":
            found.append((m.group(1), path))
    found.sort()
    return found[-days:]


def parse_price(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        value = Decimal(str(raw).replace(",", ".").strip())
    except InvalidOperation:
        return None
    return value.quantize(Decimal("0.01")) if value > 0 else None


def parse_bool(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    return str(raw).strip().lower() in ("true", "1", "yes", "evet")


def read_prices(datas: Path, days: int) -> dict[tuple[str, str], list[tuple[str, Decimal, bool | None]]]:
    """(retailer, retailer_product_id) -> [(date, price, in_stock), ...] oldest first."""
    prices: dict[tuple[str, str], list] = defaultdict(list)
    for key, cfg in RETAILERS.items():
        files = daily_files(datas, cfg, days)
        if not files:
            log(f"  prices: {key}: no daily files under {datas / cfg['folder']}")
            continue
        n = 0
        for date, path in files:
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    rpid = (row.get(cfg["id_col"]) or "").strip()
                    price = parse_price(row.get(cfg["price_col"]))
                    if not rpid or price is None:
                        continue
                    stock = parse_bool(row.get(cfg["stock_col"])) if cfg["stock_col"] else True
                    prices[(key, rpid)].append((date, price, stock))
                    n += 1
        log(f"  prices: {key}: {len(files)} days ({files[0][0]} .. {files[-1][0]}), {n:,} rows")
    return prices


# ------------------------------------------------------------------ helpers


def canonical_key(row: dict) -> str:
    model = (row.get("model_code") or "").strip().upper()
    condition = (row.get("condition") or "new").strip().lower()
    if model:
        return f"model:{model}|{condition}"
    return f"listing:{row['retailer']}:{row['retailer_product_id']}"


def variant_text(row: dict) -> str | None:
    parts = []
    if row.get("storage_gb"):
        gb = row["storage_gb"]
        try:
            gbf = float(gb)
            parts.append(f"{int(gbf // 1024)} TB" if gbf >= 1024 and gbf % 1024 == 0 else f"{int(gbf)} GB")
        except ValueError:
            parts.append(f"{gb} GB")
    if row.get("ram_gb"):
        try:
            parts.append(f"{int(float(row['ram_gb']))} GB RAM")
        except ValueError:
            pass
    if row.get("screen_size_in"):
        parts.append(f'{row["screen_size_in"]}"')
    if row.get("capacity"):
        parts.append(row["capacity"])
    if row.get("color"):
        parts.append(row["color"])
    cond = (row.get("condition") or "new").lower()
    if cond != "new":
        parts.append({"display": "Teşhir", "used": "İkinci el"}.get(cond, cond))
    text_ = " · ".join(p for p in parts if p)
    return text_[:150] or None


def category_path(row: dict) -> tuple[str, str | None]:
    raw = (row.get("category") or "").strip()
    if not raw:
        return ("Diğer", None)
    parts = [p.strip() for p in raw.split(">") if p.strip()]
    top = parts[0][:150]
    sub = parts[1][:150] if len(parts) > 1 else None
    return (top, sub)


def to_dt(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12, tzinfo=ISTANBUL).astimezone(timezone.utc)


# ------------------------------------------------------------------- main


def reset_tables(db: Session) -> None:
    for model in (PriceHistory, Offer, Product, Brand, Category, Retailer):
        db.execute(delete(model))
    db.flush()
    if engine.dialect.name == "postgresql":
        pk = {
            "price_history": "history_id",
            "offers": "offer_id",
            "products": "product_id",
            "brands": "brand_id",
            "categories": "category_id",
            "retailers": "retailer_id",
        }
        for table, column in pk.items():
            db.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} RESTART WITH 1"))
    db.commit()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)
    ap.add_argument("--datas", type=Path, default=os.environ.get("INFLATION_DATAS"), help="InflationItems/Datas folder")
    ap.add_argument("--days", type=int, default=14, help="How many daily price files to load into price_history")
    ap.add_argument("--reset", action="store_true", help="Delete existing rows first (required if tables are not empty)")
    args = ap.parse_args()

    if not args.specs_dir.is_dir():
        log(f"Spec folder not found: {args.specs_dir}")
        return 1
    if args.datas is None or not Path(args.datas).is_dir():
        log("Daily price folder missing. Pass --datas or set INFLATION_DATAS (no prices => no offers).")
        return 1

    log(f"Database: {engine.url.render_as_string(hide_password=True)}")
    log("Reading inputs")
    specs = read_specs(args.specs_dir)
    prices = read_prices(Path(args.datas), args.days)
    log(f"  {len(specs):,} spec rows, {len(prices):,} listings with prices")

    with Session(engine) as db:
        if args.reset:
            reset_tables(db)
        elif db.scalar(select(Product.product_id).limit(1)) is not None:
            log("Tables are not empty. Re-run with --reset to replace the demo data.")
            return 1

        # retailers
        retailer_ids: dict[str, int] = {}
        for key, cfg in RETAILERS.items():
            r = Retailer(name=cfg["name"], website_url=cfg["website_url"])
            db.add(r)
            db.flush()
            retailer_ids[key] = r.retailer_id

        # brands + categories (collected first, inserted once)
        brand_ids: dict[str, int] = {}
        cat_ids: dict[tuple[str, str | None], int] = {}

        def brand_id_for(name: str | None) -> int | None:
            name = (name or "").strip()[:150]
            if not name:
                return None
            if name not in brand_ids:
                b = Brand(name=name)
                db.add(b)
                db.flush()
                brand_ids[name] = b.brand_id
            return brand_ids[name]

        def category_id_for(top: str, sub: str | None) -> int:
            if (top, None) not in cat_ids:
                c = Category(name=top)
                db.add(c)
                db.flush()
                cat_ids[(top, None)] = c.category_id
            if sub is None:
                return cat_ids[(top, None)]
            if (top, sub) not in cat_ids:
                c = Category(name=sub, parent_category_id=cat_ids[(top, None)])
                db.add(c)
                db.flush()
                cat_ids[(top, sub)] = c.category_id
            return cat_ids[(top, sub)]

        # products + offers
        product_ids: dict[str, int] = {}
        product_index: dict[str, int] = {}
        product_rows: list[dict] = []
        offer_rows: list[dict] = []
        seen_urls: set[tuple[int, str]] = set()
        skipped_no_price = skipped_no_url = 0

        for row in specs:
            key = (row["retailer"], row["retailer_product_id"].strip())
            history = prices.get(key)
            if not history:
                skipped_no_price += 1
                continue
            url = (row.get("url") or "").strip()
            if not url:
                skipped_no_url += 1
                continue
            retailer_id = retailer_ids[row["retailer"]]
            if (retailer_id, url) in seen_urls:
                continue
            seen_urls.add((retailer_id, url))

            ckey = canonical_key(row)
            if ckey not in product_ids:
                top, sub = category_path(row)
                product_rows.append(
                    {
                        "_ckey": ckey,
                        "category_id": category_id_for(top, sub),
                        "brand_id": brand_id_for(row.get("brand")),
                        "name": (row.get("name") or "").strip()[:255] or row["retailer_product_id"],
                        "model": (row.get("model_code") or "").strip()[:150] or None,
                        "variant": variant_text(row),
                        "image_url": (row.get("image_url") or "").strip() or None,
                    }
                )
                product_ids[ckey] = -1  # placeholder until inserted
                product_index[ckey] = len(product_rows) - 1
            else:
                # another store lists the same model: fill image / brand gaps from it
                pr = product_rows[product_index[ckey]]
                pr["image_url"] = pr["image_url"] or (row.get("image_url") or "").strip() or None
                pr["brand_id"] = pr["brand_id"] or brand_id_for(row.get("brand"))

            last_date, last_price, last_stock = history[-1]
            offer_rows.append(
                {
                    "_ckey": ckey,
                    "retailer_id": retailer_id,
                    "retailer_product_id": row["retailer_product_id"].strip()[:150],
                    "retailer_product_name": (row.get("name") or "").strip()[:255] or None,
                    "product_url": url,
                    "current_price": last_price,
                    "currency": "TRY",
                    "in_stock": last_stock,
                    "last_updated": to_dt(last_date),
                    "_history": history,
                }
            )

        log(f"Inserting {len(product_rows):,} products")
        for pr in product_rows:
            ckey = pr.pop("_ckey")
            result = db.execute(insert(Product).returning(Product.product_id), [pr])
            product_ids[ckey] = result.scalar_one()
        db.flush()

        log(f"Inserting {len(offer_rows):,} offers")
        history_rows: list[dict] = []
        for off in offer_rows:
            ckey = off.pop("_ckey")
            history = off.pop("_history")
            off["product_id"] = product_ids[ckey]
            offer_id = db.execute(insert(Offer).returning(Offer.offer_id), [off]).scalar_one()
            history_rows.extend(
                {"offer_id": offer_id, "price": price, "recorded_at": to_dt(date)} for date, price, _ in history
            )

        log(f"Inserting {len(history_rows):,} price history points")
        for i in range(0, len(history_rows), 5000):
            db.execute(insert(PriceHistory), history_rows[i : i + 5000])
        db.commit()

        log("Done.")
        log(f"  retailers {len(retailer_ids)}, brands {len(brand_ids)}, categories {len(cat_ids)}")
        log(f"  products {len(product_rows):,}, offers {len(offer_rows):,}, history {len(history_rows):,}")
        log(f"  skipped spec rows: {skipped_no_price:,} without a daily price, {skipped_no_url:,} without url")
        multi = defaultdict(int)
        for off in offer_rows:
            multi[off["product_id"]] += 1
        log(f"  products with offers from 2+ listings: {sum(1 for n in multi.values() if n > 1):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
