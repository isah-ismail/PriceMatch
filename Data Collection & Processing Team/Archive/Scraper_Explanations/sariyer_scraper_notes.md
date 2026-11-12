**How the Sarıyer scraper works**

sariyer_specs.py (Data Collection & Processing Team/scrapers/specs/sariyer_specs.py) **reuses the inflation study's code.** The folder scrapers/specs/sariyer/ holds three files copied from the daily Sarıyer scraper (InflationItems/Codes/01_Food/Sariyer, commit a107f1664):

- config.py: the site address and request settings
- category_fetcher.py: reads the category menu from the home page
- product_fetcher.py: downloads every product of a category

The daily scraper already read each product's id, link and image, but then saved only the name and price. Our script keeps everything.

**How the site sends products**

The site does not give products in the normal page. The browser asks for them separately with a **POST** request (a request that sends a form, like a search box) to /Catalog/OBAjaxFilterProducts. The site only accepts it with an **anti-forgery token**, a hidden code from the category page that proves the request came from the site's own page. The copied code finds this token and sends it, 24 products per page.

**Two small changes to the copied code** (written at the top of each file)

1. **Images.** The page first shows a 1×1 empty picture in `src`, and puts the real image in `data-lazyloadsrc` (it loads when you scroll). The copy now reads `data-lazyloadsrc` first; before, every image was the empty picture.

2. **Only top-level categories.** The menu has 274 categories, but a parent includes its children's products (Meyve ve Sebze includes Sebze and Meyve). Each category now records its level in the menu, and our script reads only the 14 top-level ones: ~400 requests instead of ~1,000, ~9 minutes.

**An actual saved record**

retailer_product_id: 37111

name: Pınar Burger 225 Gr

brand: Pınar (from the name, see [[brands.py_notes]])

category: Et, Tavuk, Balık

size: 225 Gr

url: https://www.sariyermarket.com/pinar-burger-225-gr

Sarıyer's codes are 4–5 digit shop codes, so there is no barcode.

**Linking (2026-10-30):** 6,150 of 6,208 daily names link to one id. This also shows the 14 top-level categories missed almost nothing. See [[groceries_overview_notes]].
