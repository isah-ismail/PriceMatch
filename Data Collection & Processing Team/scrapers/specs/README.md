# Product spec scrapers

Daily **prices** come from the inflation study's scrapers
(`InflationResearchStudy/InflationItems/Datas`). These scrapers collect what
each product **is** (brand, colour, storage, RAM, screen size, condition, link,
image) and write it to `data/specs/<retailer>_specs.csv`.

Each price row is joined to its variant through the retailer's own product id:

| Retailer | Daily price CSV (inflation study) | Daily column | = specs column |
|---|---|---|---|
| Pozitif | `08_Communication/PozitifTeknoloji/pozitifTeknoloji_YYYY-MM-DD.csv` | `product_id` | `retailer_product_id` |
| Samsung | `08_Communication/Samsung/samsung_YYYY-MM-DD.csv` | `id` | `retailer_product_id` |
| Beymen | `08_Communication/Beymen/beymen_YYYY-MM-DD.csv` | `UrunID` | `retailer_product_id` |
| Marketzade | `01_Food/Marketzade/marketzade_YYYY-MM-DD.csv` | `product_name` (no id since 2026-10-26) | `name` |
| Hakmar | `01_Food/Hakmar/hakmar_YYYY-MM-DD.csv` | `product_name` (no id) | `name` |
| Sariyer | `01_Food/Sariyer/sariyermarket_YYYY-MM-DD.csv` | `product_name` (no id) | `name` |
| HappyCenter | `01_Food/HappyCenter/happycenter_YYYY-MM-DD.csv` | `product_name` (no id) | `name` |
| Ideal | `01_Food/Ideal/ideal_prices_YYYY-MM-DD.csv` | `product_name` (no id) | `name` |

On 2026-10-28 the joins were: Pozitif 1333/1347, Samsung 343/348, Beymen 11212/11212.
On 2026-10-30, by name: Marketzade 2794/2802, Hakmar 1147/1177 (its latest daily file is from
2026-10-27; the misses are fresh produce no longer listed), Sariyer 6150/6208, HappyCenter 5826/5862
(2026-10-27 file; 34 names are used for two products), Ideal 2719/2719.

**Groceries link by name.** Since 2026-10-26 the grocery daily files have no id, so a price row is
linked through its name. Each grocery scraper cleans names exactly like that store's daily scraper does,
so the same product has the same name in both files (`common.check_name_join` measures it). A name that matches several ids is ambiguous and
must not be linked. Grocery files have their own columns (see [Grocery columns](#grocery-columns)).

**Code reused from the inflation study.** Each copy says where it came from and what changed:

- `sariyer/` is copied from `InflationItems/Codes/01_Food/Sariyer` (commit `a107f1664`). Images are read
  from `data-lazyloadsrc` (the `src` is a placeholder), and categories record their menu level so only
  the 14 top-level ones are read; they include their subcategories.
- `happycenter/` is copied from `InflationItems/Codes/01_Food/HappyCenter` (commit `70d13e445`). Its daily
  CSV output is removed and product images are read. It walks only the food aisles, like the daily scraper.
- `ideal_specs.py` follows the page walking of `InflationItems/Codes/01_Food/Ideal` (commit `a107f1664`)
  but is rewritten (the original also uploads to Supabase). It keeps the product id from the link
  (`/urun/<slug>/58741`) and the image from `data-src`, and reads only the 10 top-level categories.

**Beymen makes no requests.** Its listing API is disallowed by Beymen's robots.txt,
so `beymen_specs.py` reads the names the daily inflation scraper already collected and
extracts the specs with `name_parser.py`. The link is built from the id
(`beymen.com/tr/p_x_<UrunID>` redirects to the product page). It has no image; use the
image of the same `model_code` at another store.

How much the names give (2026-10-28):

| Beymen category | Products | Storage | RAM | Screen | Model code | Brand |
|---|---|---|---|---|---|---|
| Phones | 110 | 99% | 4% | — | 75% | 96% |
| Computers / tablets | 631 | 91% | 75% | 94% | 95% | 85% |
| TVs | 97 | — | — | 98% | 94% | 49% |
| Accessories | 5,502 | not read¹ | not read¹ | not read¹ | 8% | 3% |

¹ Sizes in an accessory's name are what it fits ("15" Laptop Kılıfı"), so they are left empty.

`name_parser.parse_name(name)` can be used for any store whose data has only names.

## Run

```bash
pip install -r scrapers/requirements.txt
python scrapers/specs/pozitif_specs.py   # ~15 requests, ~20 s
python scrapers/specs/samsung_specs.py   # 21 requests, ~35 s
python scrapers/specs/beymen_specs.py    # no requests; reads the daily CSVs
python scrapers/specs/marketzade_specs.py          # ~29 requests, ~4 min (slow server)
python scrapers/specs/marketzade_specs.py --check  # no requests; how the latest daily file links
python scrapers/specs/hakmar_specs.py              # ~60 requests, ~2 min
python scrapers/specs/sariyer_specs.py             # ~400 requests, ~9 min
python scrapers/specs/happycenter_specs.py         # ~same requests as a daily run, ~8 min
python scrapers/specs/ideal_specs.py               # ~70 requests, ~7 min
```

`beymen_specs.py` looks for the inflation study's `Datas` folder at
`Desktop/InflationResearchStudy/InflationItems/Datas` (next to `jkjk/`). If yours is
elsewhere, pass `--datas <path>` or set `INFLATION_DATAS`.

A run **merges** into the existing CSV. New products are added, and known
products are updated with `first_seen` kept. Products that are no longer listed
are kept, so older price rows still join. That means it can run once or on a
schedule to pick up new products.

## Electronics columns

Pozitif, Samsung and Beymen (`common.SPEC_FIELDS`).


| Column | Meaning |
|---|---|
| `retailer_product_id` | Join key to the daily price CSV |
| `model_code` | Manufacturer part number (Apple `MTP03TU/A`, Samsung `SM-A185FLBDTUR`). The key for matching the same product across stores |
| `name`, `brand`, `category`, `family` | `category` is the store's path, e.g. `Outlet > iPhone Outlet > iPhone 15 Outlet` |
| `color` | As the store writes it, in Turkish |
| `storage_gb`, `ram_gb` | Numbers; 1 TB = 1024 |
| `screen_size_in` | Inches |
| `capacity` | Non-storage capacity as written: `9 kg`, `508 L`, `12000 BTU/h` |
| `processor`, `connectivity` | e.g. `M5`, `Wi-Fi + Cell` |
| `condition` | `new`, `display` (teşhir), `used` (ikinci el). Don't compare a display unit's price with a new one |
| `is_bundle` | Product sets (Pozitif "Avantajlı ... Setleri") |
| `url`, `image_url` | Product page and main image |
| `attributes` | Every raw attribute the site gave, as JSON |
| `first_seen`, `last_seen` | Dates in Istanbul time |

## Grocery columns

Marketzade, Hakmar, Sariyer, HappyCenter and Ideal (`common.GROCERY_FIELDS`); the electronics
columns would always be empty for them.

| Column | Meaning |
|---|---|
| `retailer_product_id` | The store's own product id |
| `barcode` | EAN-8 / UPC / EAN-13 / GTIN-14 with a valid check digit: the key for matching the same product across stores. Hakmar's API gives it (95%); Marketzade (76%) and HappyCenter (25%) name many images after it (`.../8690560355218.jpg`, `.../8690504107453-F6DB8.png`); Sariyer and Ideal have only their own short codes (empty). See the note below the table |
| `name` | Exactly as the store's daily inflation file writes it: the **join key** to the daily prices |
| `brand` | The store's brand field (Hakmar, Marketzade), else found at the start of the name by `brands.py` (Sariyer 76%, HappyCenter 79%, Ideal 86%) |
| `category` | The store's category path, e.g. `Kuru Gıda & İçecek > Makarna` |
| `size` | Pack size as written in the name: `500 Gr`, `1 L`, `6x200 ml` |
| `url`, `image_url` | Product page and main image (all five stores: 100%) |
| `attributes` | Every raw attribute the site gave, as JSON (Marketzade, Hakmar, Sariyer) |
| `first_seen`, `last_seen` | Dates in Istanbul time |

**Barcodes from image names are a strong hint, not proof.** 194 barcodes already appear at two or more
stores. Of the 191 such pairs where both names have a size, 24 differ: some are the same pack written
differently (`3 X 131 Gr` / `393 Gr`), some look like real pack changes under one barcode (Knorr
`32 Gr` / `29 Gr`), and some are wrong because a store reused another product's picture (Öncü
*Domates* Salçası `1650 Gr` / *Tatlı Biber* Salçası `900 Gr`). Confirm a barcode match with brand and
size; Hakmar's barcodes come from its API and are the most reliable.

`brands.py` and its brand list (`brands/`) are adapted from Esra's grocery catalogue (commit `dddf328`).
Checked against the brands Hakmar and Marketzade give, it agrees for 90–96% of products.

## Gaps

- **Samsung:** the API has no RAM or processor. A few products that the inflation
  scraper finds through Samsung's sitemap (Movingstyle screen, some accessories)
  are not in any category and are missing.
- **Pozitif:** `Bellek` (RAM) is only set on Macs/iPads that offer a RAM choice. iMac
  and MacBook names also carry it ("16GB 256GB"), which `name_parser` can extract.
- **Beymen:** everything is best-effort from the name. Brand is often missing for TVs
  ("75T8D 75" Google ... TV") and laptops from smaller lines. Phone RAM is rarely in the name.
