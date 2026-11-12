# Week 1 dataset audit (Team 1, data cleaning)

This report covers Esra's Week 1 tasks: inspect sample files, list fields and types, find missing values, duplicates and format problems, and compare store schemas. The grocery cleaning results stay in the Team 1 working repository (`cimri-akakce-team1`), in `data/groceries/pricematch/data_quality_report.md`.

## Scope

| Level | Covers | Output |
|---|---|---|
| Folder inventory | 373 store folders in the inflation data; newest file, rows and required columns only | `store_inventory.csv` |
| Detailed review | 27 stores: 24 grocery stores plus Beymen, Pozitif and Samsung, one daily file each | `schema_summary.csv`, `field_inventory.csv` |
| Spec file review | 8 files in `data/specs/`, as of commit `670d457` | `schema_summary.csv`, `field_inventory.csv` |
| Electronics quality | The 3 electronics stores: daily file, spec file and `data/specs_clean/` | `electronics_quality_stats.csv` |

Findings on fields, formats and repeats apply to the 27 stores and 8 spec files. The other 346 folders were counted, not reviewed field by field. All outputs are combined in `summary.json`.

Grocery files are the source files of the grocery catalog. Electronics files are dated 2026-10-29. No source file was changed. `scrapers/audit/build_week1_audit.py` rebuilds the audit CSV and JSON files. The stage counts in section 2 also use catalog and export files that stay in the working repository.

## Checks and their limits

| Check | What was done | What was not done |
|---|---|---|
| Date | `YYYY-MM-DD` parsed as a real calendar date | No check that the date is plausible for the store |
| Link | `http` or `https` with a hostname, no spaces | **No link was opened**, so working links are not confirmed |
| CPI code | Compared with `tuik_cpi_categories_comma.csv` | Whether a code suits the product was not checked |
| Empty cell | Blank, `nan`, `none`, `null`, `n/a`, `na` or `-` | Whether the store really has that value |

## 1. Main findings

1. **7 schemas appear in the reviewed sources.** 22 of the 24 grocery stores share one 4-column format. Migros and SozSanal have only `product_name` and `price`.
2. **The 24 grocery daily files have no store product ID and no link column.** Team 1's `offer_id` is not a store ID.
3. **No reviewed file has a description column.** The `attributes` JSON in spec files was not searched for description text.
4. **`category` and `product_id` each have more than one meaning** (section 3). `DATA_DICTIONARY.md` separates them.
5. **8,294 of the grocery rows have a CPI code that is not an item code.** 7,193 are valid parent codes and 1,101 are not in the CPI list.
6. **Category codes need a text type.** 70,670 grocery values of `sub_category_number` start with zero, and `category_number` appears as both `1` and `01`.
7. **Pozitif has 130 daily rows with price 0.** All 130 are marked as bundles in the spec file.
8. **999 and 9999 are not treated as invalid.** They are counted for review only (section 5).
9. **Repeated name and price is not proof of a duplicate.** All 1,037 such electronics rows have different store IDs.

## 2. Row counts at each stage

These counts come from different files and stages, so they do not add up to one total.

### Grocery

| Stage | Rows | Source |
|---|---:|---|
| Raw rows in the 24 source files | 99,431 | `schema_summary.csv` |
| Removed: price 0 | -37 | `rejected_records.csv` |
| Removed: same name and price in one file | -19 | `rejected_records.csv` |
| Delivered records | 99,375 | `stores/*.csv` |
| `needs_review`, left out of the export | -730 | `excluded_records.csv` |
| Clean records, equal to export offers | 98,645 | `offers.csv` |

The export has 81,181 products: 53,749 `product_id` values plus 27,432 clean records without one, each stored as its own product.

**Why 19 removed but 12 repeated.** 12 rows repeat exactly in the raw files. The other 7 match only after the cleaning step normalizes the name, such as `Mac&Cheese` and `Mac & Cheese`, or `KG` and `Kg`. `rejected_records.csv` labels all 19 `exact_duplicate_of_row_<n>`, which is too strong for those 7.

**Source dates differ.** The catalog used SozSanal 2026-03-31, Migros 2026-10-25, and Hakmar, HappyCenter and sok_market 2026-10-27. The other 19 stores use 2026-10-29.

**Why the inventory shows 94,914 food rows.** It uses each active store's newest file up to 2026-10-29. That leaves out SozSanal (-4,984) and uses newer files for Hakmar, HappyCenter, Migros and sok_market (+467).

### Electronics

| Store | Spec rows | Spec date | Daily rows, 2026-10-29 | Daily rows joined by store ID |
|---|---:|---|---:|---:|
| Beymen | 13,144 | Last seen up to 2026-10-28 | 11,207 | 11,188 (99.8%) |
| Pozitif | 1,334 | Last seen up to 2026-10-28 | 1,333 | 1,333 (100%) |
| Samsung | 1,389 | Last seen up to 2026-10-28 | 366 | 361 (98.6%) |

Spec files hold every product seen so far. Daily files hold one day. Their row counts are not expected to match.

## 3. Schema comparison

| Group | Source | Stores | Columns | Shape |
|---|---|---:|---:|---|
| S01 | Daily | 22 grocery | 4 | The 4 required columns |
| S02 | Daily | Migros, SozSanal | 2 | `product_name`, `price` |
| S03 | Daily | Beymen | 5 | S01 + `UrunID` |
| S04 | Daily | Pozitif | 12 | S01 + 8 extra columns |
| S05 | Daily | Samsung | 6 | S01 + `id`, `category` |
| S06 | Spec | Beymen, Pozitif, Samsung | 21 | Electronics attributes; no price |
| S07 | Spec | Hakmar, HappyCenter, Ideal, Marketzade, Sariyer | 18 | Grocery attributes; no price |

### Absent column, empty cell and not applicable

| Status | Meaning | Examples |
|---|---|---|
| Absent column | The file has no such column | `category_number` in Migros and SozSanal; any store ID in the 24 grocery daily files |
| Empty cell | The column exists, the cell has no value | `brand` empty in 11,728 Beymen spec rows |
| Not applicable | The field does not fit the product | Storage on a cable |

Empty cells in `conditional` fields may be either of the last two. The audit does not know the product type of each row, so it does not split them. `field_role` in `field_inventory.csv` marks these fields.

### Format differences

| Issue | Stores | Rows |
|---|---|---:|
| Decimal comma in price | SozSanal | 4,984 |
| CPI code is a parent code, not an item | CarrefourSA 3,716; Basdas 2,080; Gurmar 1,210; Kale 187 | 7,193 |
| CPI code not in the CPI list | CarrefourSA 819; Gurmar 282 | 1,101 |
| No category columns | Migros, SozSanal | 8,009 |
| HTML entities in raw names, such as `&#8211;` | Pozitif | Not counted |

No grocery or electronics code became valid by adding a lost leading zero.

## 4. Repeats

| Measure | Grocery daily (24) | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|---:|
| Full row repeated exactly | 12 | 0 | 0 | 0 |
| Same name and price | 12 | 956 | 0 | 81 |
| Same name and price, different store ID | No store ID | 956 | 0 | 81 |
| `(retailer, store ID)` repeated | No store ID | 0 | 0 | 0 |
| Names with several prices | 19 | 33 | 1 | 31 |

All 8 spec files have 0 repeated `(retailer, retailer_product_id)` pairs and 0 repeated full rows. Rows with the same name and a different store ID are kept: they may be variants.

## 5. Prices

| Status | Grocery daily (24) | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|---:|
| Rows | 99,431 | 11,207 | 1,333 | 366 |
| Missing | 0 | 0 | 0 | 0 |
| Cannot be read as a number | 0 | 0 | 0 | 0 |
| Zero | 37 | 0 | 130 | 0 |
| Negative | 0 | 0 | 0 | 0 |
| Above zero | 99,394 | 11,207 | 1,203 | 366 |
| Of those, exactly 999 or 9999 | 87 | 116 | 32 | 5 |

All 37 grocery zeros are in SozSanal. The last row is for review only, because these can be real prices and no reviewed source marks them as an error value. The grocery catalog already flags its 87 rows as `placeholder_price` and leaves them out of the export; that delivery was not changed here.

A value like `1.769` can be read two ways, so this audit reads it as written. All prices above are in one of the formats listed in `schema_summary.csv`.

## 6. Electronics quality

Spec files only. Blank cells are counted per column.

| Check | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|
| Rows | 13,144 | 1,334 | 1,389 |
| Empty name or store ID | 0 | 0 | 0 |
| Rows repeating an earlier name | 1,120 | 1 | 607 |
| Model code on 2+ store IDs | 244 | 47 | 0 |
| Storage, RAM or screen value not a number | 0 | 0 | 0 |
| Link fails the syntax check | 0 | 0 | 0 |
| Date is not a real calendar date | 0 | 0 | 0 |
| `first_seen` after `last_seen` | 0 | 0 | 0 |
| Not new (display or used) | 0 | 86 | 0 |
| Bundles | 0 | 130 | 14 |

### Empty cells

| Field | Role | Beymen | Pozitif | Samsung |
|---|---|---:|---:|---:|
| `url` | Source dependent | 0 | 0 | 0 |
| `brand` | Source dependent | 11,728 (89.2%) | 11 (0.8%) | 0 |
| `model_code` | Source dependent | 9,589 (73.0%) | 0 | 0 |
| `image_url` | Source dependent | 13,144 (100%) | 0 | 0 |
| `color` | Conditional | 7,661 (58.3%) | 271 (20.3%) | 245 (17.6%) |
| `storage_gb` | Conditional | 12,316 (93.7%) | 806 (60.4%) | 938 (67.5%) |
| `ram_gb` | Conditional | 12,647 (96.2%) | 1,194 (89.5%) | 1,389 (100%) |
| `screen_size_in` | Conditional | 12,273 (93.4%) | 996 (74.7%) | 1,155 (83.2%) |

Conditional counts are not error counts.

### After cleaning (`data/specs_clean/`)

| Check | Beymen | Pozitif | Samsung |
|---|---:|---:|---:|
| Rows kept | 13,144 | 1,334 | 1,389 |
| `needs_review` | 90 | 12 | 32 |
| No brand | 6,638 | 9 | 0 |
| No CPI category | 4,513 | 1,334 | 1,389 |

`data/specs_clean/` was built before the latest changes to `data/specs/`, so it does not reflect them.

## 7. Folder inventory

266 of 373 folders are active, meaning their newest file is from 2026-10-22 or later. Those newest files hold 789,194 rows. 27 folders were reviewed in detail.

| Group | Folders | Active | Rows in active newest files |
|---|---:|---:|---:|
| 01 Food | 24 | 23 | 94,914 |
| 02 Alcohol and tobacco | 16 | 16 | 4,258 |
| 03 Clothing | 24 | 23 | 127,948 |
| 04 Housing | 77 | 21 | 66,930 |
| 05 Furnishings | 31 | 30 | 176,995 |
| 06 Health | 24 | 21 | 46,267 |
| 07 Transport | 26 | 22 | 21,115 |
| 08 Communication | 33 | 29 | 26,164 |
| 09 Recreation | 15 | 14 | 124,595 |
| 10 Education | 12 | 4 | 2,878 |
| 11 Restaurants | 47 | 26 | 2,910 |
| 12 Insurance | 11 | 5 | 148 |
| 13 Personal care | 33 | 32 | 94,072 |

13 active folders lack one or more of the 4 required columns. 43 folders have no dated file up to 2026-10-29, and 7 have several files for their newest date. A folder is any folder with a CSV, including subfolders, so the count differs from the 354 in the first audit on 2026-10-29.

## 8. How this was verified

- The script ran against the raw files in the local inflation repository (commit `b56bb5ace`).
- 39 temporary sample checks passed. They covered each kind of repeat, 999 prices, zero, negative and unreadable prices, invalid dates and links without a hostname. They were not added to any data file.
- Report numbers were compared with `summary.json` and the CSV files.
