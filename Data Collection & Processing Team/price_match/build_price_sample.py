from pathlib import Path
import re
import pandas as pd


TEAM_ROOT = Path(__file__).resolve().parents[1]
RAW = TEAM_ROOT / "data/raw"
SPECS = TEAM_ROOT / "data/clean"
OUT = TEAM_ROOT / "data/prices"

SPEC_COLUMNS = ["listing_id", "retailer_product_id", "name", "brand", "model_code", "url",
                "condition", "is_bundle", "quality_status"]

OUTPUT_COLUMNS = ["listing_id", "retailer", "retailer_product_id", "date", "price", "currency",
                  "name", "brand", "model_code", "url"]


def latest_raw_file(file_prefix):
    pattern = "^" + re.escape(file_prefix) + r"_(\d{4}-\d{2}-\d{2})\.csv$"

    name_files = []
    for path in RAW.glob("*.csv"):
        match = re.match(pattern, path.name)
        if match:
            date = match.group(1)
            name_files.append((date, path))

    if not name_files:
        raise SystemExit(f"No {file_prefix}_YYYY-MM-DD.csv file in {RAW}")

    name_files.sort()
    return name_files[-1]


def keep_new_products(day):
    is_new = day["condition"] == "new"
    not_bundle = day["is_bundle"] == "False"
    is_product = day["quality_status"] == "ok"

    return day[is_new & not_bundle & is_product]


def save(day, retailer, date):
    day["retailer"] = retailer
    day["date"] = date
    day["currency"] = "TRY"
    day = day[OUTPUT_COLUMNS].sort_values("listing_id")

    OUT.mkdir(parents= True, exist_ok= True)

    out_file = OUT / f"{retailer.lower()}_prices_{date}.csv"
    day.to_csv(out_file, index= False, encoding= "utf-8-sig")

    print("Saved ", out_file.name)
    print()


def beymen_match():
    date, path = latest_raw_file("beymen")
    print("Beymen ", date, path.name)

    beymen_day = pd.read_csv(path, dtype= str, encoding= "utf-8-sig", usecols=["UrunID", "price"])
    beymen_day = beymen_day.rename(columns={"UrunID": "retailer_product_id"})
    beymen_day["price"] = pd.to_numeric(beymen_day["price"], errors= "coerce")
    print("Beginning item count: ", len(beymen_day))

    beymen_day = beymen_day[beymen_day["price"] > 0]
    print("Valid priced items: ", len(beymen_day))

    beymen_specs = pd.read_csv(SPECS / "beymen_specs.csv", dtype= str, encoding= "utf-8-sig")
    beymen_specs = beymen_specs[SPEC_COLUMNS]

    beymen_day = beymen_day.merge(beymen_specs, on= "retailer_product_id", how= "inner")
    print("Items found in the spec file: ", len(beymen_day))

    beymen_day = keep_new_products(beymen_day)
    print("New, non-bundle products: ", len(beymen_day))

    save(beymen_day, "Beymen", date)


def pozitif_match():
    date, path = latest_raw_file("pozitifTeknoloji")
    print("Pozitif ", date, path.name)

    pozitif_day = pd.read_csv(path, dtype= str, encoding= "utf-8-sig", usecols=["product_id", "price", "in_stock"])
    pozitif_day = pozitif_day.rename(columns={"product_id": "retailer_product_id"})
    pozitif_day["price"] = pd.to_numeric(pozitif_day["price"], errors= "coerce")
    print("Beginning item count: ", len(pozitif_day))

    pozitif_day = pozitif_day[pozitif_day["price"] > 0]
    print("Valid priced items: ", len(pozitif_day))

    pozitif_day = pozitif_day[pozitif_day["in_stock"] == "True"]
    print("In stock items: ", len(pozitif_day))

    pozitif_specs = pd.read_csv(SPECS / "pozitif_specs.csv", dtype= str, encoding= "utf-8-sig")
    pozitif_specs = pozitif_specs[SPEC_COLUMNS]

    pozitif_day = pozitif_day.merge(pozitif_specs, on= "retailer_product_id", how= "inner")
    print("Items found in the spec file: ", len(pozitif_day))

    pozitif_day = keep_new_products(pozitif_day)
    print("New, non-bundle products: ", len(pozitif_day))

    save(pozitif_day, "Pozitif", date)


def samsung_match():
    date, path = latest_raw_file("samsung")
    print("Samsung ", date, path.name)

    samsung_day = pd.read_csv(path, dtype= str, encoding= "utf-8-sig", usecols=["id", "price"])
    samsung_day = samsung_day.rename(columns={"id": "retailer_product_id"})
    samsung_day["price"] = pd.to_numeric(samsung_day["price"], errors= "coerce")
    print("Beginning item count: ", len(samsung_day))

    samsung_day = samsung_day[samsung_day["price"] > 0]
    print("Valid priced items: ", len(samsung_day))

    samsung_specs = pd.read_csv(SPECS / "samsung_specs.csv", dtype= str, encoding= "utf-8-sig")
    samsung_specs = samsung_specs[SPEC_COLUMNS]

    samsung_day = samsung_day.merge(samsung_specs, on= "retailer_product_id", how= "inner")
    print("Items found in the spec file: ", len(samsung_day))

    samsung_day = keep_new_products(samsung_day)
    print("New, non-bundle products: ", len(samsung_day))

    save(samsung_day, "Samsung", date)


def main():
    beymen_match()
    pozitif_match()
    samsung_match()


if __name__ == '__main__':
    main()
