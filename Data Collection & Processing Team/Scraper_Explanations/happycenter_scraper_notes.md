**How the HappyCenter scraper works**

happycenter_specs.py (Data Collection & Processing Team/scrapers/specs/happycenter_specs.py) **reuses the inflation study's code.** scrapers/specs/happycenter/happycenter_scraper.py is copied from the daily HappyCenter scraper (InflationItems/Codes/01_Food/HappyCenter, commit 70d13e445).

HappyCenter has no API, so the products are read from the **HTML** of its category pages: the same text a browser receives before it draws the page. Each product sits in a block like:

<div class="desktop-product-card" id="productCardStandart62824"> ... <img src=".../8690504107453-F6DB8.png"> ... Ülker Go Ahead Protein Taco Cips 55 Gr ...

The number at the end of `productCardStandart62824` is the product id.

**How it walks the site**

The copied code starts from the food groups in the menu (Kuru Gıda, Taze Ürünler) and goes down through each "Reyon Seçiniz" list to the smallest aisles, reading every page (?page=2, ?page=3, ...). It has a useful trick: for a parent aisle, it counts the products on the site; if its children already contain the same number, it does not read the parent again.

It reads only the food aisles, like the daily scraper, because only those get daily prices. ~5,900 products, ~8 minutes.

**Changes to the copied file** (written at its top)

1. Removed the parts that write the daily price file (they created folders as soon as the file was opened).
2. Removed the pandas import, which was only used for that file.
3. Added the product image: one extra line reads the `<img src>` of each card.

**Barcodes from image names**

Many HappyCenter images are named after the product's barcode, followed by a random code:

.../Uploads/8690504107453-F6DB8.png

Like Marketzade ([[marketzade_scraper_notes]]), the script takes those 13 digits only if they pass the check digit test ([[common.py_notes]]). This gives a barcode for 25% of products. A store sometimes reuses another product's picture, so an image barcode is a strong hint, not proof; check brand and size too.

**An actual saved record**

retailer_product_id: 62824

name: Ülker Go Ahead Protein Taco Cips 55 Gr

barcode: 8690504107453

brand: Ülker (from the name, see [[brands.py_notes]])

category: Kuru Gıda > Atıştırmalık > Atıştırmalık Çerez > Cipsler

size: 55 Gr

image_url: https://static.happycenter.com.tr/Uploads/8690504107453-F6DB8.png

**Linking:** 5,826 of 5,862 names in the latest daily file (2026-10-27) link to one id. 34 names are used for two products, so those are not linked. See [[groceries_overview_notes]].
