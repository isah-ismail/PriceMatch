from pathlib import Path
import re
import pandas as pd


TEAM_ROOT = Path(__file__).resolve().parents[2]
DAILY_TECH = TEAM_ROOT.parents[1] / "DataScraping/InflationResearchStudy/InflationItems/Datas/08_Communication"
DAILY_GROCERIES = TEAM_ROOT.parents[1] / "DataScraping/InflationResearchStudy/InflationItems/Datas/01_Food"
SPECS = TEAM_ROOT / "data/specs_clean"
OUT = TEAM_ROOT / "data/prices"

def latest_tech_market_file(folder_name, file_prefix):
    name_folder = DAILY_TECH / folder_name
    pattern = "^" + re.escape(file_prefix) + r"_(\d{4}-\d{2}-\d{2})\.csv$"

    name_files = []
    for path in name_folder.glob("*.csv"):
        match = re.match(pattern, path.name)
        if match:
            date = match.group(1)
            name_files.append((date, path))
    name_files.sort()
    return name_files[-1]

def beymen_match():
    date, path = latest_tech_market_file("Beymen", "beymen")
    print(date, path.name)

    beymen_day = pd.read_csv(path, dtype= str, encoding= "utf-8-sig", usecols=["UrunID", "product_name", "price"])

    beymen_day = beymen_day.rename(columns={"UrunID": "retailer_product_id"})

    beymen_day["retailer"] = "Beymen"
    beymen_day["date"] = date

    beymen_day["price"] = pd.to_numeric(beymen_day["price"], errors= "coerce")

    beymen_day.info()

    rows_before = len(beymen_day)

    beymen_day = beymen_day[~(beymen_day["price"].isna() | (beymen_day["price"] <= 0))]

    rows_after = len(beymen_day)

    discarded_items = rows_before-rows_after

    print("Discarded Invalid Priced Items: " , discarded_items)

    beymen_specs_location = SPECS / "beymen_specs_clean.csv"

    beymen_specs = pd.read_csv(beymen_specs_location, dtype= str, encoding= "utf-8-sig")
    beymen_specs = beymen_specs[["retailer_product_id", "brand", "model", "product_url", "condition", "is_bundle"]]

    beymen_day = beymen_day.merge(beymen_specs, on= 'retailer_product_id', how= "left", indicator= True)
    print("Total lines after merging: ",len(beymen_day))

    beymen_day = beymen_day[beymen_day['_merge'] == 'both']
    beymen_day = beymen_day.drop(columns= "_merge")

    print("Number of items after discarding non-matching items: ", len(beymen_day))

    is_new = beymen_day['condition'] == 'new'
    not_bundle = beymen_day['is_bundle'] ==  'False'

    beymen_day = beymen_day[is_new & not_bundle]

    print("New non-bundles: ", len(beymen_day))

    beymen_day = beymen_day[[
          "retailer", "retailer_product_id", "date", "price",
          "product_name", "brand", "model", "product_url",
      ]]

    OUT.mkdir(parents= True, exist_ok= True)

    out_file = OUT / f'beymen_prices_{date}.csv'
    beymen_day.to_csv(out_file, index= False, encoding= "utf-8-sig")

    print("Saved ", out_file)

    print()
    print("Beymen ", date)
    print("Beggining item count: ", rows_before)
    print("Final item count: ", len(beymen_day))
    print("With model code: ", beymen_day["model"].notna().sum())
    print("With brand: ", beymen_day["brand"].notna().sum())


def pozitif_match():
    date, path = latest_tech_market_file("PozitifTeknoloji", "pozitifTeknoloji")
    print(date, path.name)

    pozitif_day = pd.read_csv(path, dtype= str, encoding= "utf-8-sig")
    pozitif_day = pozitif_day[["product_name", "price", "product_id", "in_stock"]]
    pozitif_day = pozitif_day.rename(columns= {"product_id": "retailer_product_id"})
    pozitif_day["retailer"] = "Pozitif"
    pozitif_day["date"] = date
    pozitif_day["price"] = pd.to_numeric(pozitif_day["price"], errors= "coerce")
    pozitif_day.info()
    print()

    rows_before = len(pozitif_day)
    pozitif_day = pozitif_day[~(pozitif_day["price"].isna() | (pozitif_day["price"] <= 0))]
    pozitif_day = pozitif_day[pozitif_day["in_stock"] == "True"]
    rows_after = len(pozitif_day)
    print("Valid Item Count: ", rows_after)

    pozitif_file_location = SPECS / "pozitif_specs_clean.csv"
    pozitif_specs = pd.read_csv(pozitif_file_location, dtype= str, encoding= "utf-8-sig")
    pozitif_specs = pozitif_specs[["brand", "model", "product_url", "condition", "is_bundle", "retailer_product_id"]]

    pozitif_day = pozitif_day.merge(pozitif_specs, on= "retailer_product_id", how= "left", indicator= True)
    pozitif_day = pozitif_day[pozitif_day["_merge"] == 'both']
    pozitif_day = pozitif_day.drop(columns= ["_merge"])
    print("Matching Items: ", len(pozitif_day))

    is_new = pozitif_day["condition"] == 'new'
    not_bundle = pozitif_day["is_bundle"] == 'False'
    pozitif_day = pozitif_day[is_new & not_bundle]
    print("New, Non-bundle products: ", len(pozitif_day))

    pozitif_day = pozitif_day[[
          "retailer", "retailer_product_id", "date", "price",
          "product_name", "brand", "model", "product_url",
      ]]

    OUT.mkdir(parents= True, exist_ok= True)
    out_file = OUT / f'pozitif_prices_{date}.csv'
    pozitif_day.to_csv(out_file, index= False, encoding= "utf-8-sig")

    print("Saved ", out_file)

    print()
    print("PozitifTeknoloji ", date)
    print("Beggining item count: ", rows_before)
    print("Final item count: ", len(pozitif_day))
    print("With model code: ", pozitif_day["model"].notna().sum())
    print("With brand: ", pozitif_day["brand"].notna().sum())



def main():
    #beymen_match()
    pozitif_match()


if __name__ == '__main__':
    main()
