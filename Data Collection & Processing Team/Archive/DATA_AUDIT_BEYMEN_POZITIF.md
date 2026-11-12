# Data audit: Beymen and Pozitif (Week 1)

Team 01 — Data collection & processing (Umut, Esra)

This checks the two MVP stores (see [RETAILER_SHORTLIST.md](RETAILER_SHORTLIST.md)): what data
we have, what's missing and what problems the other teams need to know about.

**Files checked**
- Product details: `data/specs/beymen_specs.csv`, `data/specs/pozitif_specs.csv`
- Daily prices: the inflation study's `beymen_2026-10-28.csv` and `pozitifTeknoloji_2026-10-28.csv`
  (the newest daily files when this was written)

## Size

| | Beymen | Pozitif |
|---|---|---|
| Products in the spec file | 13,144 | 1,334 |
| Still listed on 2026-10-28 | 11,212 | 1,334 |
| No longer listed (kept on purpose) | 1,932 | 0 |
| Rows in the 2026-10-28 daily price file | 11,212 | 1,347 |
| Daily rows that link to a product | 11,212 (100%) | 1,333 (99%) |
| Repeated product IDs | 0 | 0 |

The 14 Pozitif daily rows without a product are products that appeared after the spec file
was last made. Running `pozitif_specs.py` again adds them.

## How full each column is

Percent of products that **have** a value.

| Column | Beymen | Pozitif | Note |
|---|---|---|---|
| `retailer_product_id` | 100% | 100% | Join key to daily prices |
| `name` | 100% | 100% | |
| `model_code` | 27% | 100% | Beymen: only when the name has it |
| `brand` | 11% | 99% | Beymen: only from the name |
| `family` (e.g. "iPhone 17 Pro") | 13% | 0% | Pozitif never filled |
| `color` | 42% | 80% | |
| `storage_gb` | 6% | 40% | Low because most products are accessories |
| `ram_gb` | 4% | 10% | |
| `screen_size_in` | 7% | 25% | |
| `processor` | 0% | 9% | |
| `connectivity` | 0% | 25% | |
| `capacity` | 0% | 0% | Not used for these stores |
| `condition` | 100% | 100% | |
| `url` | 100% | 100% | |
| `image_url` | 0% | 100% | Beymen's daily data has no image |
| `first_seen`, `last_seen` | 100% | 100% | |

There are no product descriptions for either store.

## Problems found

### Beymen

1. **No images.** The website needs a placeholder, or Pozitif's image when the product is matched.
2. **Brand and family mostly empty.** Everything comes from the product name, and many
   accessory names don't contain the brand.
3. **Some "model codes" were not real model codes. Fixed.** The name parser took any code-like
   word, for example `15AHP10` (a Lenovo laptop line shared by 18 laptops with different RAM
   and SSD), `7-7435HS` (a processor) and `1500D` (a fabric type: "Aramid Fiber 1500D").
   `name_parser.py` now rejects processors, resolutions (`1080P`, `4K/60FPS`), fabric types,
   `HDR10`, `HEPA13`, Wi-Fi speeds and Lenovo laptop lines. 97 products changed: 25 now have
   their real part number (e.g. `B2WH-091TR` instead of `275HX`) and 72 have no model code.
   The 203 Beymen–Pozitif matches did not change.

   **Codes on several products.** 244 codes are still used by two or more Beymen products.
   These are real model codes, but one model is often sold in several colours under one code
   (KitchenAid `5KSM175PS` in 11 colours), or the same product is listed twice. So a model code
   alone is not enough at Beymen: also check colour and storage.
4. **Same name, different products.** 730 names are used by two or more Beymen products,
   654 of them by products that are all still listed, for example two
   `3D Nakışlı iPhone 18 Pro Max Köpek Tasarım ... Telefon Kılıfı` with different IDs. They are
   probably different colours that the name doesn't mention. They can't be told apart by name.
5. **Products that left the site.** 1,932 products are no longer listed. They stay in the spec
   file so price history keeps working, but they must not be shown with a current price.
6. **Condition.** All products are `new`. No display (`teşhir`) items were found in names.
7. **Prices look valid.** All prices are above 0, from 492.94 TL to 1,175,000 TL.

### Pozitif

1. **130 products have price 0.** All of them are bundles (`is_bundle = True`, e.g.
   "Beats Ses Paketi – ..."). 94 of them are marked in stock. **Price 0 must never be
   shown as the cheapest price.**
2. **Display and used products share the new product's model code.** 72 display (`teşhir`) and
   14 used products. For example `MGN03TU/A` (new) and `MGN03TU/A-Teşhir` (display) both have
   model code `MGN03TU/A`. Always compare new with new, using the `condition` column.
3. **Things that aren't products.** For example "Parçalı Ödeme Jetonu" (a payment token,
   1 TL) and software licences (JamfSchool). They should be left out of search.
4. **`family` is always empty.** Filling it in (e.g. "iPhone 17 Pro", "MacBook Air 15") would help
   the matching team with products that don't share a model code.
5. **Names in the daily file contain HTML codes** (`&#8211;` instead of `–`). The spec file's
   names are already clean.

## Ready for matching

| | Count |
|---|---|
| Model codes found at both stores | 203 |
| Of those, priced at both stores on 2026-10-28 (new products only, price above 0) | **147** |
| Storage conflicts among the 203 | 0 |
| Beymen cheaper (of the 147) | 36 |

So on 2026-10-28 the website could show a real two-store price comparison for 147 products.

## Rules for the other teams

- Skip prices of 0 or less.
- Compare `condition = new` only, unless the page says "display" or "used".
- Only show a current price for products in that day's daily file.
- At Beymen, a model code alone is not proof of a match. Also check colour and storage.
