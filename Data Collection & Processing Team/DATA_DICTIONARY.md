# Data dictionary

All files are UTF-8 CSV with a header row. Files written by this repo start with a byte
order mark (open them in Python with `encoding="utf-8-sig"`). An empty cell means the
source did not give the value, or the field does not apply (storage on a cable). Read ids
and codes as text: `0812002` must keep its leading zero.

| File | One row per | Key |
|---|---|---|
| `data/clean/<store>_specs.csv` | Product the store has listed (including ones no longer listed) | `listing_id` |
| `data/prices/<store>_prices_<date>.csv` | Product with a valid price that day | `listing_id` + `date` |
| `data/raw/<file>_<date>.csv` | Row of the inflation study's daily file | the store's id column |

## Spec files: `data/clean/<store>_specs.csv`

`beymen_specs.csv`, `pozitif_specs.csv`, `samsung_specs.csv`. Written by the scrapers and
cleaned by `scrapers/clean.py` on every save. No prices.

| Column | Type | Meaning |
|---|---|---|
| `listing_id` | text | `<STORE>-<retailer_product_id>`, e.g. `BEYMEN-1865279`. One per store listing; never empty, never repeated |
| `retailer` | text | `Beymen`, `Pozitif` or `Samsung` |
| `retailer_product_id` | text | The store's own product id. Joins to the daily price file (Beymen `UrunID`, Pozitif `product_id`, Samsung `id`) |
| `model_code` | text | Manufacturer part number, e.g. `MG8H4TU/A`, `SM-A185FLBDTUR`. The key for matching across stores. Empty when the store gives none or gives its own code (see `quality_reason`) |
| `name` | text | Product name as the store writes it, with HTML codes decoded and spaces collapsed |
| `brand` | text | One spelling per brand (`scrapers/brand_spelling.json`). Pozitif and Samsung: from the store. Beymen: from the name, only when it is clear |
| `category` | text | The store's own category. Pozitif and Samsung: a path (`Outlet > iPhone Outlet > iPhone 15 Outlet`). Beymen: the inflation study's group (`Cep telefonu`, `Bilgi ve iletişim aksesuarları`, ...) |
| `family` | text | Product line, e.g. `iPhone 17 Pro`, `Galaxy A18`. Never filled for Pozitif |
| `color` | text | Colour as the store writes it, in Turkish |
| `color_group` | text | Colour family from `color`: `Gece Mavisi`, `Lacivert`, `Blue` → `Mavi`. Empty when the colour is unknown |
| `storage_gb` | number | Storage in GB; 1 TB = 1024 |
| `ram_gb` | number | Memory in GB. Never filled for Samsung |
| `screen_size_in` | number | Screen size in inches |
| `capacity` | text | Non-storage capacity: `9 kg`, `508 L`, `12000 BTU` (Samsung only). The store's original text is in `attributes` |
| `processor` | text | e.g. `M5` (Pozitif only) |
| `connectivity` | text | `Wi-Fi`, `Wi-Fi + Cellular`, `GPS` or `GPS + Cellular` (Pozitif only) |
| `condition` | text | `new`, `display` (teşhir) or `used` (ikinci el). Only compare new with new |
| `is_bundle` | text | `True` for product sets, else `False` |
| `quality_status` | text | `exclude` for things that are not products (shipping fees, payment tokens, warranty or service packages), else `ok` |
| `quality_reason` | text | Reasons separated by `; `: `not_a_product: shipping fee`, `not_a_product: payment token`, `not_a_product: warranty or service package`, `model_code_removed (<code>)` (the store's own code, e.g. `Kargo-Bedeli-2`, kept here so nothing is lost) |
| `url` | text | Product page. Beymen's is built from the id (`beymen.com/tr/p_x_<id>` redirects to the product) |
| `image_url` | text | Main image. Never filled for Beymen |
| `description` | text | The store's product description as one line of plain text: spec table rows as `Çip: M5 Pro çip`, rows and paragraphs separated by ` \| `. Pozitif only; empty for products that left the store before the column was added |
| `attributes` | JSON | Every raw attribute the store gave. Pozitif includes its raw `sku`; Beymen has `source` and `tuik_item` |
| `first_seen`, `last_seen` | date | First and last date the store listed the product (`YYYY-MM-DD`, Istanbul time). Beymen: dates of the daily files that listed it. A product with an old `last_seen` has left the store; don't show a current price for it |

## Price files: `data/prices/<store>_prices_<date>.csv`

Written by `price_match/build_price_sample.py`, which prints the row count after each step.
Only rows that pass every step are saved: price above 0, in stock (Pozitif only; the other
files have no stock flag), id found in the spec file, `condition = new`, not a bundle,
`quality_status = ok`.

| Column | Type | Meaning |
|---|---|---|
| `listing_id` | text | As in the spec file |
| `retailer` | text | As in the spec file |
| `retailer_product_id` | text | As in the spec file |
| `date` | date | Date in the daily file's name. There is no time of day |
| `price` | number | Price above 0, as the daily file gives it |
| `currency` | text | Always `TRY` |
| `name` | text | From the spec file |
| `brand` | text | From the spec file |
| `model_code` | text | From the spec file |
| `url` | text | From the spec file |

## Raw daily files: `data/raw/`

Copied unchanged from the inflation study (`InflationItems/Datas/08_Communication/<Store>/`).
Prices are in TL with a dot as the decimal separator.

| Column | Beymen | Pozitif | Samsung | Meaning |
|---|:-:|:-:|:-:|---|
| `product_name` | ✓ | ✓ | ✓ | Name as the store shows it |
| `price` | ✓ | ✓ | ✓ | Price that day |
| `category_number` | ✓ | ✓ | ✓ | TÜİK CPI main group (`8` = communication) |
| `sub_category_number` | ✓ | ✓ | ✓ | TÜİK CPI item code, e.g. `0812002` (mobile phones). `0` = not in the CPI basket |
| `UrunID` | ✓ | | | Store's product id |
| `product_id` | | ✓ | | Store's product id |
| `id` | | | ✓ | Store's product id (Samsung's model code) |
| `category` | | ✓ | ✓ | Store's own category |
| `categories` | | ✓ | | All of the product's categories |
| `regular_price` | | ✓ | | Price before discount |
| `sku` | | ✓ | | Store's stock code |
| `in_stock` | | ✓ | | `True` / `False` |
| `is_outlet` | | ✓ | | `True` / `False` |
| `url` | | ✓ | | Product page |
