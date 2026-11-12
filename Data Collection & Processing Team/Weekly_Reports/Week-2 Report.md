# Week 2 Report — Team 01 (Data Collection & Processing)

**Umut:** Scraping  
**Esra:** Data cleaning

The repository was rebuilt during Week 2 (commit `132322f`, "v2", 2026-11-12). We also moved our Week 1 work to this new structure and repeated some of the earlier steps. Because of this, this report covers both Week 1 and Week 2.

The previous files are kept in the `Archive/` folder.

## Result

We created a clean price sample for **2026-11-06** under `data/prices/`:

- Beymen: 11,583 rows
- Pozitif: 633 rows
- Samsung: 341 rows

The current pipeline works as follows:

1. Store-specific spec scrapers collect the product information.
2. The cleaned spec files are saved in `data/clean/`.
3. `build_price_sample.py` reads the daily files from `data/raw/` and creates the price sample.

All price files use `listing_id` (for example, `BEYMEN-1865279`). The column names and their meanings are explained in `DATA_DICTIONARY.md`.

Beymen and Pozitif share 212 model codes. Out of these, 102 have prices available at both stores.

## Changes Made

| Date | Commit | Change |
|---|---|---|
| 2026-11-09 | `30bdd95` | Created the first price sample: 10,999 Beymen rows and 633 Pozitif rows. |
| 2026-11-09 | `a8ae8ba` | Corrected the documentation and noted outdated Beymen model codes. |
| 2026-11-12 | `132322f` | Rebuilt the repository (v2). |
| 2026-11-12 | `efb6128` | Merged pull request #1 (`week2-price-sample`). |
| 2026-11-12 | `15b93ad`, `3d7c72e` | Removed editor files. |
| 2026-11-13 | `0cf8283` | Copied v2 to the team repository (`isah-ismail/PriceMatch`). |
| 2026-11-13 | `6151678` | Added colour, connectivity and capacity standardization to `clean.py`. |

Commits are from our working repository (`esraseezgin/cimri-akakce-team1`), except `0cf8283`, which is in this repository.

### What Changed in v2?

- **Spec files:** We now have one spec file per store under `data/clean/`. This replaces the old `data/specs/` and `data/specs_clean/` folders. `clean.py` runs the cleaning steps every time a file is saved. These steps include fixing HTML codes, extra spaces, brand spelling, store codes in `model_code`, and removing non-product entries.

- **Price files:** Added `listing_id` and `currency = TRY`. Shipping fees, payment tokens and service packages are no longer included in the price data.

- **Updated data:** Beymen specs were collected again using daily files up to 2026-11-08. This fixed the outdated model codes from the previous version. Pozitif and Samsung were scraped on 2026-11-11.

- **Repeatable builder:** `build_price_sample.py` now reads the files in `data/raw/` and processes all three stores. Pandas was also added to `requirements.txt`.

- **New store:** Samsung was added as the third store. Pozitif also now has a description column, with descriptions available for 1,303 products.

The grocery data, Esra's Week 1 audit and the old documentation were kept unchanged in `Archive/`.

### Standardization

Stores write the same thing in different ways, so `clean.py` now also standardizes these values:

- **Colour:** Colour names are grouped under one colour family in the new `color_group` column. For example, "Gece Mavisi", "Lacivert" and "Blue" all become "Mavi". The original colour stays in `color`, because the matching team still needs the exact shade. 8,060 of the 8,065 products with a colour got a colour family.
- **Connectivity:** "Wi-Fi + Cell" is now written as "Wi-Fi + Cellular".
- **Capacity:** BTU values use one format, so "24.000 Btu/Saat" and "24,000 BTU/hr" both become "24000 BTU".

The spec files in `data/clean/` were rebuilt with these rules. The price files did not change.

## Tasks

All Week 1 and Week 2 tasks are completed. The related files and documentation are listed in the evidence column below (R = `README.md`, D = `DATA_DICTIONARY.md`).

| Week | Person | Task | Evidence |
|---|---|---|---|
| 1 | Umut | GitHub access, store list and script review | Repositories; R; `scrapers/README.md` |
| 1 | Umut | Select two stores | Beymen and Pozitif, plus Samsung (R) |
| 1 | Umut | Collect IDs, URLs, descriptions and price update frequency | D; prices update daily |
| 1 | Esra | Check fields and types, compare schemas and prepare the first data dictionary | D; first audit in `Archive/data/audit/` |
| 1 | Esra | Check missing values, duplicates and formats | R: "What is in the data now" and "Known gaps" |
| 2 | Umut | Set up the scripts, collect samples from both stores and save raw CSV files | `scrapers/`, `data/prices/`, `data/raw/` |
| 2 | Umut | Collect URLs, store IDs and timestamps | Every price row; date only, as in the source |
| 2 | Umut | Make the data collection process repeatable | R: "Running it" and "Adding a newer price day" |
| 2 | Esra | Check field names and types, normalize text and keep original values | D; `clean.py`; original files in `data/raw/` |
| 2 | Esra | Check prices and currency | Prices above 0, TRY currency and non-products excluded (D) |
| 2 | Esra | Check missing IDs and descriptions, and deliver the clean sample | R; `data/prices/` |

Esra's Week 1 audit was also added to the team repository through pull request #2, which was merged on 2026-11-06.

## Data Overview

|  | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|
| Products in spec file | 13,893 | 1,374 | 1,398 |
| With model code | 28% | 90% | 100% |
| With brand | 11% | 99% | 100% |
| With image / description | 0 / 0 | 1,374 / 1,303 | 1,398 / 0 |
| Daily rows (2026-11-06) → Saved | 11,583 → 11,583 | 1,303 → 633 | 348 → 341 |

The Pozitif products excluded from the price sample were:

- 468 out of stock
- 73 display or used products
- 123 bundles
- 6 non-products

## Known Gaps

There are still some limitations in the data:

- Beymen does not provide images.
- Beymen's brand and model code information can only be extracted from product names.
- A single Beymen model code can represent multiple colours.
- None of the stores provides a barcode.
- Software licences are still included in Pozitif's data.

## Open Items

The following tasks are still waiting to be completed:

1. Confirm the dictionary column names with Teams 02 and 03.
2. Share the clean sample with Team 02 so they can label 100–200 product pairs.
