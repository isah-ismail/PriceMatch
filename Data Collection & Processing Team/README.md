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
inflation study) already scrapes about 200 Turkish stores every day and saves the
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

## Why electronics first

To compare prices we must know that two stores sell **the same** product. For
electronics this is easier than for anything else, because most products carry a
manufacturer part number: Apple `MG8Q4TU/A`, Samsung `SM-S948BLBGTUR`, Lenovo
`83JG00BMTR`. Product names alone almost never match across stores (5 identical
names among ~20,000 electronics products), but part numbers do.

## What is done

Spec files in `data/specs/`, one per store, all with the same columns:

| Store | How | Products | Joins to daily prices | Notes |
|---|---|---|---|---|
| Pozitif (pt.com.tr) | Store's public product API | 1,334 | 99% | Best structured data: colour, storage, RAM, screen, condition |
| Samsung (samsung.com/tr) | Store's public product API | 1,389 | 99% | Colour, storage, screen size, capacity; no RAM |
| Beymen (beymen.com) | **No requests**: read from the names in the daily files | 13,144 | 100% | Good for phones, computers, TVs; weak for accessories |

Model codes that appear at two stores (= products we can already compare):
Beymen–Pozitif 203, Beymen–Samsung 117.

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
data/
  specs/
    pozitif_specs.csv
    samsung_specs.csv
    beymen_specs.csv
```

## Running it

Needs Python 3.9+.

```bash
pip install -r scrapers/requirements.txt
python scrapers/specs/pozitif_specs.py   # ~20 s
python scrapers/specs/samsung_specs.py   # ~35 s
python scrapers/specs/beymen_specs.py    # needs the inflation study's daily CSVs (below)
```

Running a script again **updates** its CSV instead of replacing it. New products are
added, products that left the store are kept, and `first_seen` / `last_seen` record
when each was listed. It is safe to run any number of times.

`beymen_specs.py` reads the inflation study's `Datas` folder. By default it looks
next to this repo's parent folder (`Desktop/InflationResearchStudy/InflationItems/Datas`).
If yours is somewhere else:

```bash
python scrapers/specs/beymen_specs.py --datas "D:/path/to/InflationItems/Datas"
```

> **Don't save these CSVs from Excel.** Opening them is fine, but if you click Save,
> Excel rewrites dates (`2026-09-28` → `9/28/2026`) and turns barcode-style model codes
> into `6.97439E+12`. That corrupts the data and breaks the next run. If it happens,
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

Full list: [`scrapers/specs/README.md`](scrapers/specs/README.md).

## For the other teams

- **Esra (cleaning):** `name_parser.parse_name(name)` already extracts storage, RAM,
  screen size, colour, model code and brand from a product name. Reuse and improve it
  instead of starting over. It works for any store that only has names (e.g. Vatan).
- **Team 02 (matching):** match on `model_code` first. That alone links hundreds
  of products. Use `storage_gb` + `color` + `family` for the rest, and keep
  `condition` separate.
- **Team 03 (database):** a store listing is identified by
  `(retailer, retailer_product_id)`, **not by URL**: Beymen and Vatan have no URL in
  the daily data, so `offers.product_url` must be allowed to be empty. Daily prices go
  to `price_history` by joining on that key. The daily files go back to March 2026,
  so price history charts can be filled from day one.
- **Team 04 (frontend):** Beymen has no images. Show the image of the same
  `model_code` from another store.

## Rules we follow

- Respect each site's `robots.txt` and crawl delay, and stop when a site blocks us.
  Never try to get around a block.
- Don't put more load on a site than the inflation scrapers already do. When the
  daily data already has the information (Beymen), read it from there.
- Don't commit the inflation study's raw data to this repo. It is ~670 MB.
