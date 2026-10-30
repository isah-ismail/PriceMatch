**How the Marketzade scraper works**

marketzade_specs.py (Data Collection & Processing Team/scrapers/specs/marketzade_specs.py) is adapted from the Pozitif scraper ([[pozitif_scraper_notes]]), because both stores run the same shop software, **WooCommerce**. That means the same API address and the same JSON shape:

https://marketzade.com/wp-json/wc/store/v1/products

It requests 100 products per page, waits one second between pages, and stops at the last page: about 29 requests for ~2,800 products. The server is slow, so a run takes ~4 minutes.

**What is different from Pozitif**

1. **The name is cleaned like the daily scraper cleans it.** WooCommerce sends names with HTML codes, for example `12&#8217;li`. The daily scraper turns that into `12'li` and removes extra spaces; ours does exactly the same, so the names match for linking by name ([[groceries_overview_notes]]).

2. **The barcode comes from the image file name.** Marketzade's own SKUs are short shop codes (`91562`) that mean nothing at other stores. But many images are named after the product's barcode:

.../uploads/2024/02/8690560355218.jpg

The script takes those 13 digits only if they pass the barcode check digit test (see [[common.py_notes]]), so a random number is never mistaken for a barcode. This gives a barcode for 76% of products.

One warning: a store sometimes reuses another product's picture. Marketzade's "Öncü Domates Salçası 1650 Gr" has the same image barcode as HappyCenter's "Öncü Tatlı Biber Salçası 900 Gr", so one of them is wrong. Treat an image barcode as a strong hint and check brand and size too.

**An actual saved record**

retailer_product_id: 12161

barcode: 8690560355218

name: Bağdat Tarçın 45 Gr

brand: Bağdat

category: Baharat

size: 45 Gr

url: https://marketzade.com/bagdat-tarcin-45-gr/

**Linking (2026-10-30):** 2,794 of 2,802 daily names link to exactly one id. 2 names belong to two products ("Kavrulmuş Kaju"), and 6 were not in the catalogue.
