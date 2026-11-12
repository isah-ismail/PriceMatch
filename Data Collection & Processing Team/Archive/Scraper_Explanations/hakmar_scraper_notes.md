**How the Hakmar scraper works**

hakmar_specs.py (Data Collection & Processing Team/scrapers/specs/hakmar_specs.py) reads Hakmar Express's own API, the one its website uses to show products:

https://api.hakmarexpress.com.tr/api

It is written new, but uses the same addresses as the inflation study's daily Hakmar scraper.

It works in two steps:

1. **home/initialize-v2** returns the whole category tree (Kuru Gıda & İçecek > Makarna, ...).
2. **home/slug/<category>** returns a category's product cards, one page at a time. The page number is sent in a header (`x-page-number`) instead of the address.

**Only food categories**

The daily scraper only records prices for food and drinks, so products like detergent or pet food would have specs but never a price. Our script chooses categories with the daily scraper's own word lists (for example "temizlik", "kozmetik", "pet"), copied into the file. Result: 49 categories, ~1,170 products, ~60 requests, ~2 minutes.

**Why Hakmar is valuable**

Each product card already contains a **barcode**:

{"id": 18193, "name": "Uno Kruvasan Çikolata Kremalı 30 Gr", "barcode": "8690698515713", "brand": {"name": "Uno"}, ...}

95% of products have a real barcode, sent by the store itself, so these are the most reliable barcodes we have. Barcodes are the same at every store, so they are the best key for matching products across stores. Fresh produce has short shop codes instead (`1036223` for onions); those fail the barcode check ([[common.py_notes]]) and are left empty.

**An actual saved record**

retailer_product_id: 18193

barcode: 8690698515713

name: Uno Kruvasan Çikolata Kremalı 30 Gr

brand: Uno

category: Fırından

size: 30 Gr

url: https://www.hakmarexpress.com.tr/uno-kruvasan-cikolata-kremali-30-gr-1030766-p

**Linking:** 1,147 of 1,177 names in the latest daily file (2026-10-27) link to one id, none ambiguous. The 30 misses are fresh produce (roka, mandalina) that was no longer listed. See [[groceries_overview_notes]].
