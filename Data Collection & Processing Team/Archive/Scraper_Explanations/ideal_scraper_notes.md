**How the İdeal scraper works**

ideal_specs.py (Data Collection & Processing Team/scrapers/specs/ideal_specs.py) reads İdeal's category pages as **HTML**, 50 products per page. It follows the same steps as the inflation study's daily İdeal scraper (InflationItems/Codes/01_Food/Ideal, commit a107f1664), but is **rewritten**: most of the original uploads data to a Supabase database, which we do not need.

**What the daily scraper did not keep**

Each product card looks like this:

<a href="/urun/kultur-mantari-400gr-paket/58741"> <img data-src=".../api/image/58741.jpg"> Kültür Mantarı 400gr Paket ... 99.95 TL

The daily scraper read only the name and price. Our script also keeps:

- **The product id:** the number at the end of the link (`58741`). The same number is on the "Sepete Ekle" button as `data-id`.
- **The link.**
- **The image:** from `data-src`. The plain `src` is a "loading" animation; the real picture loads when you scroll.

**Only top-level categories**

The home page links to 64 categories, but the 10 top-level ones (/kategori/gida) already include their subcategories (/kategoriler/gida/makarna). The script reads only those 10: ~70 requests, ~7 minutes.

**An actual saved record**

retailer_product_id: 81581

name: Beyoğlu Dubai Çikolatası 35gr

brand: Beyoğlu (from the name, see [[brands.py_notes]])

category: Atıştırmalıklar

size: 35gr

url: https://www.ideal.com.tr/urun/beyoglu-dubai-cikolatasi-35gr/81581

**Linking (2026-10-30):** all 2,719 daily names link to exactly one id, so the 10 categories missed nothing. See [[groceries_overview_notes]].
