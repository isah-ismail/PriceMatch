# Cimri / Akakçe clone — price comparison

An 8-person course project to build a price comparison website like
[Cimri](https://www.cimri.com) or [Akakçe](https://www.akakce.com): search for a
product and see its price at every store, cheapest first, with price history.

| Team | People | Area |
|---|---|---|
| 01 Data collection & processing | Umut (scraping), Esra (cleaning) | **this README** |
| 02 Product matching | Iftikhar, Poyraz | which store listings are the same product |
| 03 Database & backend | Fatima, Yake Kamal | PostgreSQL schema, API |
| 04 Frontend & integration | Isah, Ayşe | website, deployment |

---

## Where the data comes from

We **do not scrape prices ourselves.** A separate research project (a Turkish
inflation study) already scrapes about 110 Turkish stores every day and saves the
prices as CSV files (`InflationResearchStudy/InflationItems/Datas`). We use those files.

Those files were made to measure inflation, not for shopping. Most of them only
have `product_name, price, category_number, sub_category_number`: no link, no image,
no storage or colour. That is not enough for a comparison site.

Our professor's guidance (2026-10-28):

1. Use the data already scraped for inflation.
2. Write our own extra code for links and images.
3. Product information (storage, colour, ...) only has to be collected **once**
   per product, into our own database.
4. Connect each day's price to the right product version **through its link /
   product id**.

So there are two data flows, joined by the store's own product id:

```
 DAILY (inflation study, already running)        ONCE PER PRODUCT (this repo)
 ─────────────────────────────────────────       ─────────────────────────────────
 beymen_2026-10-28.csv                           data/specs/beymen_specs.csv
   product_name   price      UrunID  ──────────►   retailer_product_id  1865304
   iPhone 17 Pro… 122679.38  1865304               storage_gb 256, color Kozmik Turuncu,
                                                   model_code MG8Q4TU/A, url, ...
```

**Example.** Samsung's daily file has two rows that look the same:
`Galaxy A18, 17999`. Through their ids (`SM-A185FLBDTUR`, `SM-A185FZSDTUR`) the
spec file says one is *Açık Mavi 128 GB* and the other *Gümüş 128 GB*.

**Groceries link by name.** Since 2026-10-26 the inflation study's grocery files have
no id at all (only `product_name, price` and the two TÜİK codes). Inside one store the
daily scraper and ours read the same site, so each grocery spec script writes `name`
exactly as that store's daily file does, and the name leads to the id:

```
 hakmar_2026-10-27.csv                            data/specs/hakmar_specs.csv
   Uno Kruvasan Çikolata Kremalı 30 Gr, 19.50 ──►   name (same text) → retailer_product_id 18193,
                                                    barcode 8690698515713, url, image_url, ...
```

Tested on older files that still had ids: a name that leads to exactly one id is the
right product 99.9% of the time. A name used for two products is **ambiguous** and must
not be linked.

## Why electronics first

To compare prices we must know that two stores sell **the same** product. For
electronics this is easier than for anything else, because most products carry a
manufacturer part number: Apple `MG8Q4TU/A`, Samsung `SM-S948BLBGTUR`, Lenovo
`83JG00BMTR`. Product names alone almost never match across stores (5 identical
names among ~20,000 electronics products), but part numbers do.

## What is done

Spec files in `data/specs/`, one per store. Electronics and groceries use different
columns (see [the columns](#the-spec-file-columns-short-version)).

| Store | How | Products | Joins to daily prices | Notes |
|---|---|---|---|---|
| Pozitif (pt.com.tr) | Store's public product API | 1,334 | 99% | Best structured data: colour, storage, RAM, screen, condition |
| Samsung (samsung.com/tr) | Store's public product API | 1,389 | 99% | Colour, storage, screen size, capacity; no RAM |
| Beymen (beymen.com) | **No requests**: read from the names in the daily files | 13,144 | 100% | Good for phones, computers, TVs; weak for accessories |
| Marketzade (marketzade.com), groceries | Store's public product API (WooCommerce, like Pozitif) | 2,817 | 99.7% by name | Daily file has no id, so linked by name; barcode for 76%, image and link for all |
| Hakmar (hakmarexpress.com.tr), groceries | Store's JSON API | 1,170 | 97.5% by name | Food only, like the daily scraper; barcode for 95%, brand, image and link for all |
| Sariyer (sariyermarket.com), groceries | Site's product list (code copied from the inflation study) | 6,227 | 99.1% by name | Image and link for all; brand from the name (76%); no barcodes |
| HappyCenter (happycenter.com.tr), groceries | Category pages (code copied from the inflation study) | 5,872 | 99.4% by name | Food aisles only; image and link for all; brand from the name (79%); barcode from image names (25%) |
| Ideal (ideal.com.tr), groceries | Category pages | 2,723 | 100% by name | Image and link for all; brand from the name (86%); no barcodes |

Products we can already compare across stores: model codes Beymen–Pozitif 203,
Beymen–Samsung 117; grocery barcodes at two or more of Marketzade, Hakmar and
HappyCenter 194.

Not done yet:

| Store | Status |
|---|---|
| Vatan | Product pages have rich structured data, but the daily price file has no id or link yet, so nothing can be joined. The daily scraper needs a small change to save the link. Vatan allows one request every 10 s, so the first full run would take ~15 h. |
| MediaMarkt, Vestel | Daily scrapers only collect white goods (fridges, washers). Adding phones / laptops / TVs is a small change in the inflation study's scrapers. |
| Teknosa, Hepsiburada, Trendyol, Amazon | Not scraped by anyone yet. These are the biggest electronics sellers. |

## Repository layout

```
scrapers/
  requirements.txt
  specs/
    README.md          details: every column, per-store notes, known gaps
    common.py          shared columns, merge logic, path to the inflation data
    name_parser.py     reads storage / RAM / screen / colour / model code / brand from a name
    pozitif_specs.py
    samsung_specs.py
    beymen_specs.py
    marketzade_specs.py
    hakmar_specs.py
    sariyer_specs.py
    happycenter_specs.py
    ideal_specs.py
    sariyer/           fetching code copied from the inflation study's Sariyer scraper
    happycenter/       crawling code copied from the inflation study's HappyCenter scraper
data/
  specs/
    pozitif_specs.csv
    samsung_specs.csv
    beymen_specs.csv
    marketzade_specs.csv
    hakmar_specs.csv
    sariyer_specs.csv
    happycenter_specs.csv
    ideal_specs.csv
```

## Running it

Needs Python 3.9+.

```bash
pip install -r scrapers/requirements.txt
python scrapers/specs/pozitif_specs.py   # ~20 s
python scrapers/specs/samsung_specs.py   # ~35 s
python scrapers/specs/beymen_specs.py    # needs the inflation study's daily CSVs (below)
python scrapers/specs/marketzade_specs.py  # ~4 min
python scrapers/specs/hakmar_specs.py      # ~2 min
python scrapers/specs/sariyer_specs.py     # ~9 min
python scrapers/specs/happycenter_specs.py # ~8 min
python scrapers/specs/ideal_specs.py       # ~7 min
```

Running a script again **updates** its CSV instead of replacing it. New products are
added, products that left the store are kept, and `first_seen` / `last_seen` record
when each was listed. It is safe to run any number of times.

`beymen_specs.py` and the grocery scripts' link check read the inflation study's
`Datas` folder. By default they look two folders above this repo
(`<that folder>/InflationResearchStudy/InflationItems/Datas`). If yours is somewhere else,
set `INFLATION_DATAS` once, for example in `~/.zshrc`:

```bash
export INFLATION_DATAS="$HOME/Desktop/AI 201/DataScraping/InflationResearchStudy/InflationItems/Datas"
```

(`beymen_specs.py --datas <path>` also works for a single run.) Every grocery script has
`--check`: it makes no requests and reports how many names in the store's latest daily
file link to exactly one product.

> **Don't save these CSVs from Excel.** Opening them is fine, but if you click Save,
> Excel rewrites dates (`2026-09-28` → `9/28/2026`) and turns barcodes and barcode-style
> model codes into `8.69056E+12`. That corrupts the data and breaks the next run. If it happens,
> `git checkout -- data/specs/` restores the committed files.

## The spec file columns (short version)

| Column | Example | Use |
|---|---|---|
| `retailer`, `retailer_product_id` | `Beymen`, `1865304` | **Join key** to the daily price files |
| `model_code` | `MG8Q4TU/A` | **Matching key** across stores |
| `name`, `brand`, `category`, `family` | `iPhone 17 Pro`, `Apple` | Display, search, filters |
| `color`, `storage_gb`, `ram_gb`, `screen_size_in`, `capacity` | `Kozmik Turuncu`, `256`, `12`, `6.9` | Variant details, filters |
| `condition` | `new` / `display` / `used` | Never compare a display unit's price with a new one |
| `url`, `image_url` | | "Go to store" link, product picture |
| `first_seen`, `last_seen` | `2026-09-28` | When the store listed it |

Grocery stores use a shorter set: `retailer, retailer_product_id, barcode, name, brand, category, size,
url, image_url, attributes, first_seen, last_seen`. `name` is the join key to their daily prices
(their daily files have no id), and `barcode` is the matching key across stores.

Full list: [`scrapers/specs/README.md`](scrapers/specs/README.md).

## For the other teams

- **Esra (cleaning):** `name_parser.parse_name(name)` already extracts storage, RAM,
  screen size, colour, model code and brand from a product name. Reuse and improve it
  instead of starting over. It works for any store that only has names (e.g. Vatan).
  For groceries, `brands.py` uses your brand list and brand finder from the grocery
  catalogue (`dddf328`); improving the list raises brand coverage for Sariyer (76%),
  HappyCenter (79%) and Ideal (86%).
- **Team 02 (matching):** match on `model_code` first. That alone links hundreds
  of products. Use `storage_gb` + `color` + `family` for the rest, and keep
  `condition` separate.
  For groceries, match on `barcode` first (Hakmar 95%, Marketzade 76%, HappyCenter 25%;
  194 barcodes are already at two or more stores), then `brand` + `size` + name. Barcodes read
  from image file names (Marketzade, HappyCenter) can be wrong when a store reuses a picture, so
  confirm them with brand and size.
- **Team 03 (database):** a store listing is identified by
  `(retailer, retailer_product_id)`, **not by URL**: Beymen and Vatan have no URL in
  the daily data, so `offers.product_url` must be allowed to be empty. Daily prices go
  to `price_history` by joining on that key; for groceries, first look the daily name up
  in the store's spec file (same text) to get the id, and skip names that lead to two ids.
  History by id does not reach back to March 2026 everywhere: Beymen's ids start in
  August–September, and grocery files before 2026-10-26 come in many formats.
- **Team 04 (frontend):** Beymen has no images. Show the image of the same
  `model_code` from another store.

## Rules we follow

- Respect each site's `robots.txt` and crawl delay, and stop when a site blocks us.
  Never try to get around a block.
- Don't put more load on a site than the inflation scrapers already do. When the
  daily data already has the information (Beymen), read it from there.
- Don't commit the inflation study's raw data to this repo. It is ~4 GB.
