# PriceMatch: data collection and processing

Team 1's part of PriceMatch, a price comparison site like Cimri or Akakçe. This repo
collects product details for the MVP stores, cleans them, and joins them to the daily
prices so the other teams get one file per store and day: what the product is, where to
buy it and what it costs.

MVP stores: **Beymen** and **Pozitif**, plus **Samsung**. Grocery stores come after the MVP.

## How the data flows

```
 inflation study's daily price files             our spec scrapers
 (one file per store and day)                    (what each product is)
          │                                                │
          ▼                                                ▼
     data/raw/                                       data/clean/
 beymen_2026-11-06.csv                           beymen_specs.csv
   UrunID 1865279, 109277.32 TL                    listing_id BEYMEN-1865279
          │                                         model_code MG8H4TU/A, 256 GB, ...
          │                                                │
          └──────────────► price_match/ ◄──────────────────┘
                     joins on the store's product id
                                  │
                                  ▼
                            data/prices/
                  beymen_prices_2026-11-06.csv
          listing_id, price, currency, name, brand, model_code, url
```

We do not scrape prices. A separate inflation research project already scrapes about
110 Turkish stores every day (`InflationResearchStudy/InflationItems/Datas`). Its files
have the price and the store's product id but almost nothing else, so our scrapers
collect the product details once per product and the price builder joins the two.

## Layout

```
scrapers/            spec scrapers and their shared code (see scrapers/README.md)
  pozitif_specs.py   Pozitif's public product API
  samsung_specs.py   Samsung's public product API
  beymen_specs.py    no requests: reads the names in the inflation study's daily files
  common.py          columns, merge-and-save, paths
  clean.py           cleaning rules, applied every time a spec file is saved
  name_parser.py     storage, RAM, screen, colour, model code and brand from a name
  brands.py          one spelling per brand (brand_spelling.json)
price_match/
  build_price_sample.py   data/raw + data/clean -> data/prices
data/
  raw/               daily price files copied unchanged from the inflation study
  clean/             cleaned spec files, one per store
  prices/            price files: one per store and day
DATA_DICTIONARY.md   every column of every file
```

## Setup

Python 3.9 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`beymen_specs.py` reads the inflation study's `Datas` folder. It looks for
`InflationResearchStudy`. If yours is elsewhere, set `INFLATION_DATAS`:

```bash
export INFLATION_DATAS="$HOME/Desktop/AI 201/DataScraping/InflationResearchStudy/InflationItems/Datas"
```

## Running it

From the repository root:

```bash
python scrapers/pozitif_specs.py            # ~15 requests, ~1 min
python scrapers/samsung_specs.py            # 21 requests, ~1 min
python scrapers/beymen_specs.py             # no requests; reads every Beymen daily file
python price_match/build_price_sample.py    # seconds
```

The scrapers **update** their file in `data/clean/` instead of replacing it: new products
are added, products that left the store are kept (old prices still join), and
`first_seen` / `last_seen` record when each was listed. They are safe to run any number of
times. Every save re-cleans the whole file, so a file is never older than the cleaning rules.

After changing a rule in `clean.py`, re-clean all files without scraping:

```bash
python scrapers/clean.py
```

### Adding a newer price day

Copy that day's daily files from the inflation study into `data/raw/` without changing
them (`08_Communication/Beymen/beymen_<date>.csv`, `PozitifTeknoloji/pozitifTeknoloji_<date>.csv`,
`Samsung/samsung_<date>.csv`). Run the scrapers first so new products are in the spec files,
then run the price builder: it always uses the newest file in `data/raw/` for each store.

Copy only the days you need. The whole inflation study's data is about 4 GB.

## IDs

Every spec and price file has these three columns:

| Column | Example | Made by | Means |
|---|---|---|---|
| `retailer_product_id` | `1865279` | The store | The store's own product id. Unique only within one store |
| `listing_id` | `BEYMEN-1865279` | This repo | One store listing: store name + the store's id. Unique across all stores, the same every day, and can be computed from a daily price row |
| `model_code` | `MG8H4TU/A` | The manufacturer | Manufacturer part number, the same at every store. Not unique: empty when the store gives none, and one code can be several listings (see below) |

`listing_id` is the only id this repo creates. Use it as the key for offers and prices.
The id that groups listings of the same product across stores (`product_id`) is made by
Team 2 (matching), not here.
Samsung's ids are its model codes, so its `listing_id` contains a `/`
(`SAMSUNG-SM-A185FLBDTUR`, `SAMSUNG-AC071RN4DKG/EU`); encode it in URLs.

### For the matching team

`listing_id` says **which listing** a row is, never which product. Two stores' ids for the
same iPhone have nothing in common. Matching compares what the product is instead: above all `model_code`, the manufacturer's part number, which is the same at every store, then `brand`, `family`, `color`, `storage_gb`, `ram_gb`, `screen_size_in` and `capacity`:

| model_code | Beymen | Pozitif |
|---|---|---|
| `MG8H4TU/A` (iPhone 17 Pro 256 GB Kozmik Turuncu) | `BEYMEN-1865279`, 109,277.32 TL | `POZITIF-479386`, 111,499.00 TL |

The matching output is a table that gives each listing a `product_id`
(`BEYMEN-1865279 → P1`, `POZITIF-479386 → P1`). The website then shows every offer of `P1`,
cheapest first. Things to watch:

- **Skip empty model codes.** pandas `merge` joins empty (NaN) keys with each other, which
  pairs unrelated products. Drop rows without a `model_code` before joining on it.
- **One code can be several listings.** On 2026-11-06, 102 shared codes give 105 Beymen–Pozitif
  pairs. At Beymen one code is often sold in several colours, so also compare `color` and `storage_gb`.
- **Compare new with new.** The price files already contain only new, non-bundle products.
- **Most Beymen listings have no model code** (28% do). About half of those (5,385 of 10,018) are accessories: phone cases, watch straps and chargers, mostly from small makers, and only 76 have a brand. Other stores are unlikely to sell the same item: Pozitif's accessories are branded (Beats, ZAGG, Apple, Satechi) and have model codes. Most of the rest are small appliances, game consoles and audio, which other stores may sell. For those, matching has to use the name, brand, colour and storage, and an uncertain match should stay unmatched.

## What is in the data now

Spec files: Beymen from its daily files up to 2026-11-08, Pozitif and Samsung scraped on
2026-11-11. Prices from 2026-11-06:

| | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|
| Products in the spec file | 13,893 | 1,374 | 1,398 |
| With a model code | 3,875 (28%) | 1,233 (90%) | 1,398 (100%) |
| With a brand | 1,532 (11%) | 1,363 (99%) | 1,398 (100%) |
| With an image | 0 | 1,374 | 1,398 |
| With a description | 0 | 1,303 | 0 |
| Rows in the 2026-11-06 daily price file | 11,583 | 1,303 | 348 |
| Saved to `data/prices/` | 11,583 | 633 | 341 |

The price builder prints the count after each step. Pozitif loses most rows
to its stock flag (468 out of stock), then display and used units (73), then bundles (123)
and non-products (6).

**Cross-store matches by model code:** Beymen and Pozitif share 212 model codes; 102 of
them have a price at both stores on 2026-11-06. Beymen and Samsung share 119 (32 priced at
both). Pozitif and Samsung share none: Pozitif sells mostly Apple, Samsung only Samsung.

## Known gaps

- **Beymen has no images**, and its brand and model code come only from the product name.
  Accessory names rarely say the maker, so most accessories have neither. Show the image of
  the same `model_code` from another store.
- **At Beymen a model code alone is not proof of a match.** One code is often sold in several
  colours (KitchenAid `5KSM175PS` in 11). Also compare `color` and `storage_gb`.
- **Compare new with new.** Pozitif's display and used units share the new product's model code.
- **Descriptions only at Pozitif.** Pozitif's `description` (1,303 of the 1,312 products it lists
  today) holds the store's spec table and text, so it can fill in what the columns miss.
  Samsung's product API gives none, and Beymen's daily files have only the name.
- **No barcodes (GTIN/EAN).** No store gives one as a field. Pozitif uses the EAN-13 barcode as
  the SKU for 41 accessories (Zore, I-Pro, Lito), so for those `model_code` is the barcode.
- **Software licences** (Microsoft 365, Office) stay in Pozitif's data as products. Shipping fees, payment tokens and warranty or service packages are marked `exclude`.

## Rules

- **Follow each site's `robots.txt`.** Don't request paths it disallows, and wait at least its
  `Crawl-delay` between requests. Beymen's `robots.txt` disallows its listing API, so
  `beymen_specs.py` makes no requests and reads the inflation study's daily files instead.
- **Don't save the CSVs from Excel.** Excel rewrites dates and long numbers and breaks the next
  run. If it happens, `git checkout -- data/` restores the committed files.
