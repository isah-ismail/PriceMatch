# Price Sample Builder

`build_price_sample.py` takes each retailer's latest daily price CSV, matches it with that retailer's cleaned spec file, and saves one clean price file per retailer to `data/prices/`.

## How to run

From the repository root:

```bash
python scrapers/prices/build_price_sample.py
```

`main()` calls one matching function per retailer. To leave a retailer out of a run, comment out its call there.

## Input files

| Input | Location |
| ----- | -------- |
| Daily price CSVs | Folders in the inflation research project, outside this repo (paths set at the top of the script) |
| Cleaned spec files | `data/specs_clean/<retailer>_specs_clean.csv` |

> **Note:** the daily price CSVs are **not in this repo**. The paths at the top of the script assume the `DataScraping` folder sits two levels above the repo root. If your copy is somewhere else, change those paths.

## Code structure

| Part | Description |
| ---- | ----------- |
| `main()` | Calls each retailer's matching function |
| Matching functions | One per retailer (`<retailer>_match()`). Each one cleans the day's prices, matches them with the specs, and saves the result |
| Latest file finders | Find the latest daily price file for a retailer |

### Latest file finders

- Take a `folder_name` (the retailer's folder) and a `file_prefix` (the retailer name as it appears in the CSV filenames)
- Look for files named `<file_prefix>_<YYYY-MM-DD>.csv`
- Return a `(date, path)` pair for the file with the latest date in its filename

Example: `folder_name="Beymen"`, `file_prefix="beymen"` matches `beymen_2026-11-06.csv`.

If no matching file is found, the script stops with Python's `IndexError: list index out of range`. This usually means the folder path or the prefix is wrong.

### Matching functions

Each matching function does roughly the same steps. A retailer can skip a step or add its own filters if its data needs them.

1. Load the latest price file and keep only the columns needed
2. Rename the columns to the shared names (e.g. the retailer's product ID column becomes `retailer_product_id`)
3. Drop rows that are invalid, such as a missing price, a price ≤ 0, or an out-of-stock product when the retailer provides stock status
4. Match the rows with the retailer's spec file on `retailer_product_id` and keep only products found in both files
5. Keep only new products that aren't bundles (`condition == "new"` and `is_bundle == "False"`)
6. Keep only the output columns and save the result

Each function prints the row count after its main steps, so you can see how many rows each filter dropped.

## Output

`data/prices/<retailer>_prices_<YYYY-MM-DD>.csv`, saved as UTF-8 with BOM. Every retailer's file has the same columns:

| Column | Description |
| ------ | ----------- |
| `retailer` | Retailer name |
| `retailer_product_id` | The retailer's own product ID |
| `date` | Date of the daily price file |
| `price` | Price in TRY |
| `product_name` | Product name from the price file |
| `brand` | From the spec file (may be empty) |
| `model` | Model code from the spec file (may be empty) |
| `product_url` | Product page URL from the spec file |

## Adding a new retailer

1. Write a `<retailer>_match()` function following the steps above (copying an existing one is the easiest way to start)
2. Make sure its output has exactly the columns listed above
3. Call it from `main()`
