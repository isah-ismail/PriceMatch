# Data dictionary (Team 01, draft)

This draft lists the columns of the CSV files in the Team 1 working repository (`cimri-akakce-team1`) and the raw daily columns of the 27 stores reviewed in Week 1. Other inflation study folders were not reviewed field by field.

Paths below are relative to that repository, unless they start with `data/audit/`. The team repository may not hold those files, so treat them as external references.

Files are UTF-8 CSV with a header row; some start with a byte order mark. Column names still need confirmation from Teams 02 and 03.

## Which file to use

| You need | Use | Rows | Key |
|---|---|---:|---|
| Electronics product details | `data/specs/beymen_specs.csv`, `pozitif_specs.csv`, `samsung_specs.csv` | 13,144 / 1,334 / 1,389 | `(retailer, retailer_product_id)` |
| Cleaned electronics names | `data/specs_clean/*_specs_clean.csv` | 15,867 for 3 stores | `(retailer, retailer_product_id)` |
| Grocery catalog, 24 stores | `data/groceries/pricematch/pricematch_cleaned_all_markets.csv` | 99,375 | `offer_id`, else `record_key` |
| Grocery records with price and match proposal | `data/groceries/pricematch/stores/<Store>.csv` | 99,375 | `offer_id`, else `record_key` |
| Grocery data for PostgreSQL | `data/groceries/pricematch_db/` | 98,645 offers | Database `offer_id` |
| Daily prices | Inflation study CSV files, not in this repository | One file per store and day | See section 1 |

## IDs

These IDs are not interchangeable.

| ID | Example | Made by | Identifies | Notes |
|---|---|---|---|---|
| Source product ID | `(Beymen, 1865304)` | The store | One product of one store | Unique only with the store: `(retailer, retailer_product_id)`. Daily names: `UrunID`, `product_id` (Pozitif), `id` |
| `offer_id` | `IDEAL-000123` | Team 1 | One store listing in the grocery catalog | Not a store ID. Also `catalog_offer_id` and `source_offer_key`. Day-to-day stability was not verified in this audit |
| `record_key` | `A101\|a101_kapida_2026-10-29.csv\|1` | Team 1 | One row of one file | Names a file and row, so it is not an ID across days |
| Cross-store `product_id` | `PRD-000123` | Team 1 | A proposed same-product group | A proposal, not Team 02's result. Do not confuse it with Pozitif's daily `product_id` |
| Database `offer_id`, `product_id` | `1` | Database export | One table row | Numbers. `id_map_offers.csv` and `id_map_products.csv` link them to Team 1 IDs |

The 24 grocery daily files have no store ID. Five stores get `retailer_product_id` from spec files by exact name. The other 19 have no source ID in this repository, and their `offer_id` must not be shown as one.

## Same concept, different names

| Concept | Daily file | Spec file | Cleaned file | Database |
|---|---|---|---|---|
| Name | `product_name` | `name` | `original_product_name`, `standardized_product_name` | `retailer_product_name`, `name` |
| CPI item code | `sub_category_number` | `tuik_code` | `category`, `sub_category_number` | `categories` table |
| Store's own category | `category`, `categories` | `category` | `store_category` | None |
| Link | `url` | `url` | `product_url` | `product_url` |

**`category` has two meanings.** In daily and spec files it is the store's own category. In cleaned files it is the 7-digit CPI code.

## Reading an empty value

| Status | Meaning |
|---|---|
| Absent column | The file does not have the column |
| Empty cell | The column exists but the cell has no value |
| Not applicable | The field does not fit the product, such as storage on a cable |

An empty cell in a conditional field can mean either of the last two. `field_role` in `data/audit/field_inventory.csv` marks each field as `every_row`, `source_dependent` or `conditional`.

## 1. Raw daily price files

Source: `InflationResearchStudy/InflationItems/Datas/<Group>/<Store>/`, one file per store and day.

| Column | Inferred type | Recommended type | Stores reviewed | Meaning |
|---|---|---|---|---|
| `product_name` | text | text | All 27 | Name as the store shows it |
| `price` | decimal; text in SozSanal | decimal | All 27 | Price in TL. SozSanal uses a decimal comma |
| `category_number` | integer | text | All but Migros, SozSanal | CPI main group, written `1` or `01` |
| `sub_category_number` | integer | text | All but Migros, SozSanal | CPI code; `0` = not in the basket. Leading zeros matter |
| `UrunID` | integer | text | Beymen | Store's product ID |
| `product_id` | integer | text | Pozitif | Store's product ID |
| `id` | text | text | Samsung | Store's product ID |
| `sku` | mixed | text | Pozitif | Store's stock code |
| `regular_price` | decimal | decimal | Pozitif | Store's regular price field |
| `in_stock` | boolean | boolean | Pozitif | Store's stock flag |
| `is_outlet` | boolean | boolean | Pozitif | Store's outlet flag |
| `category`, `categories` | text | text | Pozitif; Samsung has `category` only | Store's own category |
| `url` | url | text | Pozitif | Product page |

Measured types per file are in `data/audit/field_inventory.csv`. Meanings of Pozitif's extra columns come from their names and were not confirmed with the store.

## 2. Electronics spec files

One row per store product. There is no price: prices join from the daily files on the store's ID. Details: `scrapers/specs/README.md`.

| Column | Type | Empty cell means | Meaning |
|---|---|---|---|
| `retailer` | text | Should not be empty | Store name |
| `retailer_product_id` | text | Should not be empty | Store's product ID |
| `model_code` | text | Source did not give it | Manufacturer part number |
| `name` | text | Should not be empty | Product name |
| `brand` | text | Source did not give it | Brand |
| `category` | text | Source did not give it | Store's own category |
| `family` | text | Conditional | Product line, such as `iPhone 17 Pro` |
| `color` | text | Conditional | Colour as written |
| `storage_gb` | decimal | Conditional | Storage; 1 TB = 1024 |
| `ram_gb` | decimal | Conditional | Memory |
| `screen_size_in` | decimal | Conditional | Screen size in inches |
| `capacity` | text | Conditional | Non-storage capacity, such as `9 kg` |
| `processor` | text | Conditional | Processor, such as `M5` |
| `connectivity` | text | Conditional | Connection type |
| `condition` | text | Source did not give it | `new`, `display` or `used` |
| `is_bundle` | boolean | Conditional | Product set |
| `url` | text | Source did not give it | Product page |
| `image_url` | text | Source did not give it | Main image |
| `attributes` | json | Source did not give it | Raw attributes from the source |
| `first_seen`, `last_seen` | date | Should not be empty | First and last dates listed |

## 3. Grocery spec files

`data/specs/hakmar_specs.csv`, `happycenter_specs.csv`, `ideal_specs.csv`, `marketzade_specs.csv`, `sariyer_specs.csv`. Daily prices join by exact `name`. `retailer`, `retailer_product_id`, `brand`, `url`, `image_url`, `attributes`, `first_seen` and `last_seen` work as in section 2.

| Column | Type | Meaning |
|---|---|---|
| `catalog_offer_id` | text | Team 1 `offer_id` of the same listing |
| `barcode` | text | Barcode; keep as text |
| `name` | text | Exactly as the daily file writes it |
| `category` | text | Store's own category path |
| `tuik_code` | text | 7-digit CPI code; keep leading zeros |
| `size`, `unit`, `pack_quantity`, `variant` | text | As in section 4 |
| `data_quality_status` | text | `clean` or `needs_review` |

## 4. Cleaned grocery catalog

`pricematch_cleaned_all_markets.csv` has the 19 columns marked below. `stores/<Store>.csv` has all 26. Full rules: `data/groceries/pricematch/data_dictionary.md`. That file calls `offer_id` permanent; treat this as the design goal, not a verified result.

| Column | Catalog | Type | Meaning |
|---|---:|---|---|
| `retailer` | Yes | text | Store name |
| `offer_id` | Yes | text | See IDs |
| `record_key` | Yes | text | See IDs |
| `product_id` | | text | See IDs: cross-store proposal |
| `original_product_name` | Yes | text | Name as scraped |
| `standardized_product_name` | Yes | text | `Brand – Product name – Quantity` |
| `canonical_product_name` | | text | One display name per `product_id` |
| `brand` | Yes | text | Confirmed brand, one spelling |
| `model` | Yes | text | Model or article code in the name |
| `category` | Yes | text | Valid 7-digit CPI code |
| `category_number`, `sub_category_number` | Yes | text | CPI codes as scraped |
| `variant` | Yes | text | Fat level, lactose-free, organic, flavour |
| `capacity` | Yes | text | Storage or battery capacity |
| `size` | Yes | text | Net quantity in one form, such as `500 g` |
| `color` | Yes | text | Colour words for non-food products |
| `pack_quantity` | Yes | integer | Items in the pack |
| `unit` | Yes | text | Sales unit: `paket`, `kg` or `adet` |
| `price` | | decimal | Shelf price in TRY, as scraped |
| `data_quality_status` | Yes | text | `clean` or `needs_review` |
| `match_status` | | text | `matched`, `single_retailer`, `ambiguous` or `not_matchable` |
| `review_reason` | Yes | text | Why a row needs review, plus remarks |
| `standardization_changes` | Yes | text | What name cleaning changed |
| `scrape_date` | | date | Date of the source file |
| `source_file`, `source_row` | | text, integer | Source file and its data row |

### Related grocery files

`products_master.csv`, `product_matches.csv` and `unmatched_products.csv` are in `archive_esra_old_work/matching_groundwork/`. The other two are in `data/groceries/pricematch/`.

| File | Columns |
|---|---|
| `products_master.csv` | `product_id`, `canonical_product_name`, `brand`, `model`, `variant`, `capacity`, `size`, `color`, `pack_quantity`, `unit`, `category`, `retailer_count`, `offer_count`, `retailers`, `match_rule`, `match_signature` |
| `product_matches.csv` | `retailer`, `offer_id`, `record_key`, `product_id`, `canonical_product_name`, `match_status`, `match_reason` |
| `unmatched_products.csv` | `retailer`, `offer_id`, `record_key`, `original_product_name`, `standardized_product_name`, `price`, `data_quality_status`, `match_status`, `reason` |
| `rejected_records.csv` | `retailer`, `source_file`, `source_row`, `original_value`, `reason` |
| `data_quality_stats.csv` | `retailer`, `source_file`, `scrape_date`, `raw_rows`, `unreadable_rows`, `rejected_rows`, `exact_duplicates_removed`, `records`, `clean`, `needs_review`, `missing_offer_id`, `missing_brand`, `missing_size_and_unit`, `missing_category`, `with_model`, `with_capacity`, `with_color`, `with_variant`, `with_pack_quantity`, `name_changed`, `matched`, `single_retailer`, `ambiguous`, `not_matchable`, `reason_placeholder_price`, `reason_suspicious_size`, `reason_corrupted_size_text`, `reason_same_name_different_price_no_offer_id`, `reason_case_or_single_price_unclear`, `reason_ambiguous_brand_word_not_used`, `reason_promotion_text_kept_in_name`, `reason_brand_not_found_in_name`, `reason_letter_case_uncertain`, `reason_abbreviation_not_expanded`, `reason_no_quantity_in_name`, `reason_range_kept_in_name` |

## 5. Cleaned spec files

`data/specs_clean/*_specs_clean.csv` and `specs_cleaned_all.csv`. The first 19 columns are the catalog columns in section 4. These follow them. Details: `data/specs_clean/README.md`.

| Column | Meaning |
|---|---|
| `retailer_product_id` | Store's product ID |
| `barcode` | Barcode |
| `product_url`, `image_url` | Product page and image |
| `store_category` | Store's own category |
| `condition`, `is_bundle` | Electronics only, as in section 2 |
| `first_seen`, `last_seen` | First and last dates listed |
| `source_file` | Spec file the row came from |

## 6. Database export

`data/groceries/pricematch_db/`. Details: `data/groceries/pricematch_db/README.md`.

| Table or file | Columns |
|---|---|
| `retailers` | `retailer_id`, `name`, `website_url` |
| `categories` | `category_id`, `parent_category_id`, `name` |
| `brands` | `brand_id`, `name` |
| `products` | `product_id`, `category_id`, `brand_id`, `name`, `barcode`, `model`, `variant`, `image_url` |
| `offers` | `offer_id`, `product_id`, `retailer_id`, `retailer_product_id`, `retailer_product_name`, `product_url`, `current_price`, `currency`, `in_stock`, `last_updated`, `source_offer_key` |
| `price_history` | `history_id`, `offer_id`, `price`, `recorded_at` |
| `id_map_offers.csv` | `source_offer_key`, `offer_id`, `retailer`, `record_key` |
| `id_map_products.csv` | `product_id`, `source_product_key`, `basis`, `offer_count` |
| `retailer_sources.csv` | `retailer`, `website_url`, `taken_from` |
| `excluded_records.csv` | `retailer`, `offer_id`, `record_key`, `original_product_name`, `price`, `reason` |

## 7. Audit files

`data/audit/`. See [the report](data/audit/week1_audit_report.md).

| File | Columns |
|---|---|
| `store_inventory.csv` | `group`, `store_folder`, `files`, `undated_files`, `newest_date`, `newest_file`, `rows`, `columns`, `has_all_required`, `absent_required_columns`, `active`, `read_error`, `reviewed_in_detail`, `same_date_files` |
| `field_inventory.csv` | `source_group`, `store`, `file`, `date`, `field`, `inferred_type`, `recommended_type`, `field_role`, `rows`, `empty_cells`, `empty_pct`, `distinct`, `values_with_leading_zero`, `example` |
| `schema_summary.csv` | `source_group`, `store`, `file`, `date`, `valid_file_date`, `rows`, `columns`, `header`, `has_all_required`, `absent_required_columns`, `extra_columns`, `wrong_column_count_rows`, `empty_name`, `price_missing`, `price_unparseable`, `price_zero`, `price_negative`, `price_positive`, `price_999_or_9999_review_only`, `price_formats`, `full_row_duplicates`, `name_price_repeats`, `names_with_several_prices`, `store_id_field`, `store_id_duplicates`, `empty_store_id`, `category_number_lengths`, `sub_category_lengths`, `cpi_empty_or_zero`, `cpi_item_code`, `cpi_parent_code`, `cpi_item_code_if_zero_padded`, `cpi_not_in_cpi_list`, `schema_group` |
| `electronics_quality_stats.csv` | `store`, `check`, `value` |

## Description field

No reviewed file has a description column. The `attributes` JSON in spec files was not searched for description text.
