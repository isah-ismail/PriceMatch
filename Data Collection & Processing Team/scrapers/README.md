# Spec scrapers

Each scraper collects what a store's products **are** (model code, brand, colour,
storage, link, image) and saves them to `data/clean/<store>_specs.csv`, keyed by the
store's own product id, the same id the inflation study's daily price files carry.
Columns: [DATA_DICTIONARY.md](../DATA_DICTIONARY.md).

| Store | Script | Source | Requests | Join column in the daily file |
|---|---|---|---|---|
| Pozitif (pt.com.tr) | `pozitif_specs.py` | Store's public WooCommerce API | ~15, ~1 min | `product_id` |
| Samsung (samsung.com/tr) | `samsung_specs.py` | Samsung's public product finder API | 21, ~1 min | `id` |
| Beymen (beymen.com) | `beymen_specs.py` | Names in the inflation study's daily files | none | `UrunID` |

## Pozitif

`pozitif_specs.py` reads `https://www.pt.com.tr/wp-json/wc/store/v1/products`, the API
the store's own website uses. It returns JSON, 100 products per request; the script
waits 1 second between pages and stops at the last page (at most 100 pages). Every
colour and storage version is its own product with its own id.

The store's attributes become columns:

| Pozitif attribute | Column | Example |
|---|---|---|
| `Renk` | `color` | `Yıldız Işığı` |
| `Depolama` / `Kapasite` | `storage_gb` | `128GB` → `128`, `1 TB` → `1024` |
| `Bellek` | `ram_gb` | |
| `Ekran Boyutu` | `screen_size_in` | |
| `İşlemci` | `processor` | `M5` |
| `Bağlantı Türü` / `Bağlantı Özellikleri` | `connectivity` | `Wi-Fi + Cell` |
| `Ürün Durumu` | `condition` | `Yeni` → `new`, `Teşhir` → `display`, `İkinci El` → `used` |

`model_code` is the store's SKU with any condition suffix removed: `MLPG3TU/A-Teşhir`
becomes `MLPG3TU/A`, `MC7W4TU/A-KutuHasarlı` becomes `MC7W4TU/A`. So a display unit
has the same model code as the new product; `condition` tells them apart. A name that
contains "Teşhir" is a display unit even when `Ürün Durumu` is missing. The raw SKU
stays in `attributes`. Product type `bundle` sets `is_bundle`.

The product's HTML description (a spec table, then paragraphs) is saved as `description`, one
line of plain text: `Mac mini M5 Pro ... | Çip: M5 Pro çip, 18 çekirdekli CPU ... | 2026 yılında ...`.

## Samsung

`samsung_specs.py` reads the product finder API that samsung.com/tr's category pages
call, for 21 top-level categories (phones, tablets, watches, TVs, monitors, appliances,
...). Each category returns product **families** (`Galaxy A18`), and each family has a
`modelList` with one entry per sellable version, so the script writes one row per
version:

```
Galaxy A18
  ├── Açık Mavi, 128 GB → SM-A185FLBDTUR
  └── Gümüş, 128 GB     → SM-A185FZSDTUR
```

A version's options come as "chips": `COLOR` → `color`, `MOBILE MEMORY` → `storage_gb`,
`TV SIZE` / `MONITOR SCREEN SIZE` → `screen_size_in`, capacity chips (washers, fridges,
air conditioners) → `capacity`. Samsung's id is its model code, so `retailer_product_id`
and `model_code` are the same. A version listed in two categories is written once. The API
has no RAM or processor, so those stay empty; empty means unknown, not zero.

## Beymen

**`beymen_specs.py` makes no requests.** Beymen's listing API is disallowed by its
`robots.txt`, so the script reads the product names the inflation study's daily scraper
already collected and extracts the specs from them with `name_parser.py`.

1. It reads every `beymen_YYYY-MM-DD.csv` in `<INFLATION_DATAS>/08_Communication/Beymen/`,
   oldest first (not the `beymen_tech_` or `beymen_enflasyon_` files).
2. It keeps one row per `UrunID`, with the latest name.
3. `first_seen` and `last_seen` are the dates of the first and last file that listed it.

For accessories (TÜİK item `0819201`), sizes in the name describe what the accessory fits
("15" Laptop Kılıfı"), so storage, RAM, screen size and family are left empty. The link is
built from the id (`https://www.beymen.com/tr/p_x_<UrunID>` redirects to the product).
There are no images in the daily data.

Example: `iPhone 17 Pro 256GB Kozmik Turuncu Akıllı Cep Telefonu MG8H4TU/A` gives
`model_code MG8H4TU/A`, `brand Apple`, `family iPhone 17 Pro`, `storage_gb 256`,
`color Kozmik Turuncu`.

## Shared code

### `common.py`: columns and saving

`SPEC_FIELDS` is the column list every store writes. `merge_and_save()` merges a run's
rows into the existing file:

```
existing file: A, B      this run: B, C      saved: A, B, C
```

A stays, so old prices still join. B gets the new values; `first_seen` keeps the earliest
date and `last_seen` the latest. C is added. Every other field of B is replaced by the new
run, so a value the store stops giving becomes empty. The file is written to a `.part` file
first and then moved into place, so a crash never leaves half a CSV.

`common.py` also finds the inflation study's `Datas` folder (`INFLATION_DATAS`) and has the
storage and screen-size converters the scrapers share.

### `clean.py`: cleaning rules

`save_specs()` runs `clean.clean_row()` on **every row of the file** each time it is saved,
including products that have left the store. The rules only use the row itself, so running
them twice gives the same result:

| Rule | Example |
|---|---|
| `listing_id` = store + the store's id | `POZITIF-17870` |
| Name: HTML codes decoded, spaces collapsed | `iPad &#8211; Kılıf` → `iPad – Kılıf` |
| Brand: one spelling (`brands.py`) | `Beats Electronics` → `Beats` |
| Model code must look like a part number: capital letters, digits, `.` `/` `-` | `Kargo-Bedeli-2`, `_Z536`, `BeatsSesPaketi...` are removed; the removed code is kept in `quality_reason` |
| Not a product → `quality_status = exclude` | Shipping fees (`Kargo Bedeli`), payment tokens (`Ödeme Jetonu`), warranty or service packages (`Garanti Paketi`, `Hizmet Paketi`) |

To re-clean every file without scraping (after changing a rule): `python scrapers/clean.py`.

### `name_parser.py`: specs from a name

Used for Beymen, whose data has only names. It uses regular expressions:

| Text in the name | Becomes |
|---|---|
| `24GB Bellek` | `ram_gb 24` (a size followed by RAM / Bellek) |
| `1TB SSD` | `storage_gb 1024` |
| `13"` | `screen_size_in 13` |
| `Gümüş` | `color` |
| `MDH94TU/A` | `model_code` (Apple and Samsung patterns first, then codes with a dot, then a code-like word) |
| `RH80T2AP6RM.ABWPLTK`, `Ecam 220.31.SB` | `model_code` with a dot (Samsung, LG, De'Longhi appliances). A code written in two words is joined: `ECAM220.31.SB` |
| `MacBook` | `brand Apple` (a product line that names its maker) |

Graphics memory (`RTX 5060 8GB`) is skipped. Of the remaining sizes the largest is storage
and a smaller one may be RAM. These are best-effort rules, not manufacturer data. Words that
look like codes but are specs are rejected as model codes: processors (`275HX`), resolutions
(`1080P`, `4K/60FPS`), fabric types (`1500D`), `HDR10`, Wi-Fi speeds (`AX1800`) and Lenovo
laptop lines (`15AHP10`).

For an accessory, a product line names what it fits ("iPhone 17 Kılıfı"), so only the maker's
name at the start of the name counts as the brand, and none when the name says "Uyumlu".

### `brands.py`: one spelling per brand

Different stores write one brand differently. `canonical()` looks the brand up in
`brand_spelling.json` (keys are lower case, Turkish letters folded); brands not in the list
are kept as written. When two stores spell a brand differently, add a line there and run
`python scrapers/clean.py`.

## Adding a store

1. Copy the closest scraper. Its `to_spec()` must return the store's own product id as
   `retailer_product_id`: the id that the store's daily price file carries.
2. Save with `common.merge_and_save("<Store>", rows)`. `listing_id` and cleaning are added for you.
3. In `price_match/build_price_sample.py`, copy `samsung_match()` to `<store>_match()`, change
   the file prefix and the id column, call it from `main()`, and copy a daily file into `data/raw/`.
