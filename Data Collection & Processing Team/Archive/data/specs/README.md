# Cleaned spec files

Umut's spec files (`data/specs/*_specs.csv`) cleaned and standardized into Team 1's catalog format. Umut's files are not changed; this folder is an addition.

| File | Rows | With Team 1 `offer_id` |
|---|---:|---:|
| `beymen_specs_clean.csv` | 13,144 | — (electronics, not in the grocery catalog) |
| `pozitif_specs_clean.csv` | 1,334 | — |
| `samsung_specs_clean.csv` | 1,389 | — |
| `hakmar_specs_clean.csv` | 1,170 | 1,144 |
| `happycenter_specs_clean.csv` | 5,872 | 5,767 |
| `ideal_specs_clean.csv` | 2,723 | 2,559 |
| `marketzade_specs_clean.csv` | 2,817 | 2,663 |
| `sariyer_specs_clean.csv` | 6,227 | 6,120 |
| `specs_cleaned_all.csv` | 34,676 | all of the above in one file |

## Columns

The first 19 columns are the same as `data/groceries/pricematch/pricematch_cleaned_all_markets.csv`; see `data/groceries/pricematch/data_dictionary.md`. After them come Umut's own fields, unchanged:

| Column | Meaning |
|---|---|
| `retailer_product_id` | the store's own permanent product id |
| `barcode` | the barcode, only when its check digit is valid |
| `product_url` | link to the product page |
| `image_url` | link to the product image |
| `store_category` | the store's own category |
| `condition` | electronics only: new, display or used |
| `is_bundle` | electronics only: whether the listing is a bundle |
| `first_seen`, `last_seen` | when the store listed the product |
| `source_file` | the spec file the row came from |

## Rules

- **`offer_id`**: A grocery row gets the Team 1 catalog `offer_id` only when its exact name appears once in the same store's catalog. Every other row has an empty `offer_id`; its permanent key is the store's own `retailer_product_id`. No new ids are made up. `record_key` (`retailer|source_file|retailer_product_id`) is unique for every row.
- **`brand`**: For Pozitif and Samsung the brand comes from the store's own data (Samsung's names often do not repeat "Samsung"). For the other files it is used only when the name carries it.
- **`category`**: The CPI item of the matched catalog row, or Beymen's own `tuik_item` when it is a valid CPI code. Otherwise empty; the store's own category is still in `store_category`.
- **`standardized_product_name`**: Built with the same rules as the grocery catalog. Mixed-case names (`iPad`, `MacBook`, `GeForce`), model codes and technical abbreviations are kept as written.
- **Prices**: There are none. These are product catalogs; prices are scraped daily and joined on the ids.

`validation_results.md`: 10 of 10 checks passed. Among them:
- every row is kept,
- original names and store ids are unchanged,
- no word or number is lost,
- every `offer_id` is a real catalog id of the same store and name,
- Umut's files and the earlier deliveries are unchanged.
