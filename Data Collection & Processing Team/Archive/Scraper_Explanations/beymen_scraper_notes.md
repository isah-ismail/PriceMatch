**How the Beymen scraper works**

Beymen’s script (Data Collection & Processing Team/scrapers/specs/beymen_specs.py) takes a different approach: **it makes no website requests.**

It reads the inflation study’s existing files:

beymen_2026-10-14.csv

beymen_2026-10-15.csv

...

The code comments and README explain that this approach was chosen because Beymen’s listing API is disallowed by its robots.txt.

The script:

1. Finds files whose names exactly follow beymen_YYYY-MM-DD.csv.
2. Sorts them from oldest to newest.
3. Reads every product row.
4. Extracts specs from the product name.
5. Keeps one record per UrunID, with the latest encountered name.
6. Records the earliest and latest file dates containing that product.

An actual saved record comes from this name:

iPhone 15 128 GB Siyah Akıllı Cep Telefonu MTP03TU/A

The extracted fields are:

retailer_product_id: 2146955

model_code: MTP03TU/A

brand: Apple

family: iPhone 15

storage_gb: 128

color: Siyah

first_seen: 2026-10-14

last_seen: 2026-10-28

It also constructs a product link from UrunID. It leaves image_url empty because the input files do not contain images.

To see how the name parser works, check: [[name_parser_notes]]

