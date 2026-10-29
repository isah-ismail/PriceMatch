"""
Beymen (beymen.com) product specs, read from the inflation study's daily CSVs.

Beymen's listing API is disallowed by its robots.txt, so this makes no
requests at all: it reads the names the daily inflation scraper already
collected (Datas/08_Communication/Beymen/beymen_YYYY-MM-DD.csv) and pulls
the specs out of them with name_parser. For phones, computers and TVs the
names carry storage, RAM, screen size, colour and the manufacturer part
number ("iPhone 17 Pro 1TB Kozmik Turuncu Akıllı Cep Telefonu MG8Q4TU/A").

The link is built from the id: beymen.com/tr/p_x_<UrunID> redirects to the
product page. There is no image in the daily data.

Join key: retailer_product_id == `UrunID` in the daily CSV.
Every daily file is read, oldest first, so products that have left the site
are kept and a product's latest name wins; first_seen / last_seen are the
dates of the first and last daily file that listed it.

Output: data/specs/beymen_specs.csv
"""

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

import common
import name_parser

PRODUCT_URL = "https://www.beymen.com/tr/p_x_{}"
DAILY_RE = re.compile(r"^beymen_(\d{4}-\d{2}-\d{2})\.csv$")  # not beymen_tech_ / beymen_enflasyon_

# TÜİK 08 items the inflation scraper assigns (Codes/08_Communication/tuik08.py).
CATEGORIES = {
    "0812002": "Cep telefonu",
    "0813101": "Bilgisayar",
    "0813209": "Bilgisayar çevre birimleri",
    "0814001": "Ses ve görüntü ekipmanı",
    "0814007": "Televizyon",
    "0819103": "Diğer iletişim cihazları",
    "0819201": "Bilgi ve iletişim aksesuarları",
    "0": "Diğer",
}
ACCESSORIES = "0819201"

log = logging.getLogger("beymen_specs")


def daily_files(datas):
    folder = datas / "08_Communication" / "Beymen"
    files = sorted((m.group(1), path) for path in folder.glob("beymen_*.csv")
                   if (m := DAILY_RE.match(path.name)))
    return folder, files


def to_spec(row, date):
    name = " ".join(row["product_name"].split())
    item = row["sub_category_number"]
    specs = name_parser.parse_name(name, device=item != ACCESSORIES)
    return {
        **specs,
        "retailer": "Beymen",
        "retailer_product_id": row["UrunID"],
        "name": name,
        "category": CATEGORIES.get(item, "Diğer"),
        "capacity": "",
        "processor": "",
        "connectivity": "",
        "condition": "display" if "teşhir" in name.lower() else "new",
        "is_bundle": False,
        "url": PRODUCT_URL.format(row["UrunID"]),
        "image_url": "",
        "attributes": {"source": "name", "tuik_item": item},
        "first_seen": date,
        "last_seen": date,
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--datas", type=Path, default=common.INFLATION_DATAS,
                        help="the inflation study's Datas folder (default: %(default)s)")
    args = parser.parse_args()

    folder, files = daily_files(args.datas)
    if not files:
        log.error("no beymen_YYYY-MM-DD.csv in %s; set --datas or INFLATION_DATAS", folder)
        sys.exit(1)

    products = {}  # UrunID -> spec row, with the first and last file date
    for date, path in files:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if not row.get("UrunID") or not row.get("product_name"):
                    continue
                spec = to_spec(row, date)
                old = products.get(row["UrunID"])
                if old:
                    spec["first_seen"] = old["first_seen"]
                products[row["UrunID"]] = spec
    log.info("%d daily files (%s .. %s), %d products", len(files), files[0][0], files[-1][0], len(products))

    path, added, updated, kept = common.merge_and_save("Beymen", list(products.values()))
    log.info("%s: %d new, %d updated, %d not in the daily files (kept)", path, added, updated, kept)


if __name__ == "__main__":
    main()
