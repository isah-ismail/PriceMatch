# Retailer shortlist (Week 1)

Team 01 — Data collection & processing (Umut, Esra)

## Selected retailers: Beymen and Pozitif

The first version of the site (MVP) compares prices between these two stores.
All teams should build and test around them first.

| | Beymen (beymen.com) | Pozitif (pt.com.tr) |
|---|---|---|
| Products | 13,144 | 1,334 |
| Main products | Phones, computers, TVs, audio, accessories | Apple products (iPhone, iPad, Mac, Watch) and accessories |
| Daily prices joined to a product | 100% (by product ID) | 99% (by product ID) |
| Model code (e.g. `MG8Q4TU/A`) | 3,555 products (27%) | 1,334 products (100%) |
| Product link | All products | All products |
| Product image | None | All products |
| Where the details come from | Product names in the daily price files | The store's own product API |

## Why these two

- **Same kind of products.** Both sell electronics, so many products are sold at both stores.
- **Daily prices link to products.** Both daily price files have the store's product ID,
  so each day's price can be attached to the right product.
- **Easy to match.** The two stores share **203 model codes**. A shared model code means
  the same product, so the matching team (Team 02) can start with these easy, reliable matches.
  147 of them had a price at both stores on 2026-10-28 (new products only); the rest have
  left Beymen's site or are Pozitif bundles with no price.
- **They complement each other.** Pozitif has very detailed, reliable product information
  (colour, storage, RAM, screen, condition). Beymen has many more products.

## How often prices update

The inflation study's scrapers collect both stores' prices **once a day**. Beymen's runs at
02:00. Each run makes one new file per store, named by date (`beymen_2026-10-28.csv`,
`pozitifTeknoloji_2026-10-28.csv`). There has been a file for every day since 2026-09-28
for both stores. Pozitif also has older files from 2026-05-02, with gaps.

Product details (model code, colour, link and so on) don't change daily, so our spec
scripts only need to run again when new products appear.

## Limits

- **Beymen's details come only from product names.** They're good for phones, computers
  and TVs and weaker for accessories. Only 27% of Beymen products have a model code.
- **Beymen has no product images.** The website must show a placeholder, or use
  Pozitif's image when the product is matched.
- **Pozitif mostly sells Apple products.** Matches between the two stores will be mostly
  Apple products (iPhone, iPad, Mac and so on).
- **No product descriptions.** Neither store's data has a description text.

## Data files

- Beymen: `data/specs/beymen_specs_clean.csv`
- Pozitif: `data/specs/pozitif_specs_clean.csv`
- Daily prices: the inflation study's daily CSV files (see the main [README](README.md))

## Next store to add: Samsung

Once the MVP works with Beymen and Pozitif, Samsung (samsung.com/tr) is the easiest
store to add:

- Its daily prices link to products by ID (99%), like the other two.
- It shares **117 model codes** with Beymen. With Samsung added, Beymen products can be
  compared with another store 203 + 117 times instead of 203.
- It shares no model codes with Pozitif, because Pozitif sells mostly Apple products and
  Samsung sells only Samsung products.

Data file: `data/specs/samsung_specs_clean.csv`

## Other stores

We also have data for five supermarkets (Marketzade, Hakmar, Sariyer, HappyCenter, Ideal).
They match less well than the electronics stores: the most barcodes shared by any two of
them is 75 (Marketzade and HappyCenter), and Sariyer and Ideal have no barcodes at all.
