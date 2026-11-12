**How the grocery scrapers fit together**

The grocery scripts (Data Collection & Processing Team/scrapers/specs/marketzade_specs.py, hakmar_specs.py, sariyer_specs.py, happycenter_specs.py, ideal_specs.py) collect what each supermarket product **is**: its id, barcode, brand, size, link and image. Prices still come from the inflation study's daily files.

**The problem they solve**

Since 2026-10-26 the inflation study's grocery files have only four columns:

product_name, price, category_number, sub_category_number

There is no product id, so a daily price cannot be joined to a product by id the way Pozitif or Beymen prices can.

**The solution: linking by name**

Inside one store, the daily scraper and our scraper read the same website, so the same product has the same name in both files. Each grocery script therefore writes `name` **exactly** the way that store's daily scraper writes it (same HTML cleaning, same spaces).

Daily file (Hakmar, 2026-10-27):     Uno Kruvasan Çikolata Kremalı 30 Gr, 19.50

Our specs file: Uno Kruvasan Çikolata Kremalı 30 Gr → id 18193, barcode 8690698515713

Before building on this, we tested it on old daily files that still had ids: when a name pointed to exactly one id, it was the right product 99.9% of the time.

Sometimes two products share one name (Ideal never, HappyCenter 34 names). Those are **ambiguous** and must not be linked; guessing would attach a price to the wrong product.

Every grocery script has a `--check` option that makes no requests and reports how many names in the latest daily file link to exactly one id. On 2026-10-30:

Marketzade 99.7%, Hakmar 97.5%, Sariyer 99.1%, HappyCenter 99.4%, Ideal 100%

**Grocery columns**

Groceries use a shorter column list than electronics, because colour, storage or RAM would always be empty:

retailer, retailer_product_id, barcode, name, brand, category, size, url, image_url, attributes, first_seen, last_seen

- **barcode** is the key for matching the same product across stores (see [[common.py_notes]] for how it is checked).
- **brand** comes from the store when it gives one, otherwise from the name (see [[brands.py_notes]]).
- **size** is the pack size written in the name: `30 Gr`, `1 L`, `6x200 ml`.

Each store: [[marketzade_scraper_notes]], [[hakmar_scraper_notes]], [[sariyer_scraper_notes]], [[happycenter_scraper_notes]], [[ideal_scraper_notes]]
