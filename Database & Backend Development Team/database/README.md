# PriceMatch — Database Documentation

## 1. Overview

PriceMatch is a web-based multi-store product price comparison system designed to help users compare prices of the same product across different online retailers.

The database is implemented using PostgreSQL 17 and supports product organization, retailer listings, price comparisons, and historical price tracking.

## 2. Database Structure

The database contains six main tables:

| Table | Description |
|---|---|
| `categories` | Stores product categories and supports subcategories. |
| `brands` | Stores product brands. |
| `products` | Stores unique products that can be listed by multiple retailers. |
| `retailers` | Stores information about online retailers. |
| `offers` | Connects products to retailers and stores current prices, availability, and product URLs. |
| `price_history` | Records historical prices for individual offers. |

An additional table, `schema_migrations`, tracks applied database migrations.

## 3. Entity Relationships

- One category can contain multiple products. Each product belongs to one category.
- Categories can have a parent category, allowing hierarchical organization.
- One brand can have multiple products. A product may have no assigned brand.
- One product can have multiple offers from different retailers.
- One retailer can publish multiple offers.
- One offer belongs to one product and one retailer.
- One offer can have multiple price history records.

The `offers` table connects products and retailers, allowing PriceMatch to compare prices across stores.

## 4. Primary Keys and Foreign Keys

All six main tables have automatically generated primary keys.

Foreign-key relationships:

| Table | Foreign Key | References |
|---|---|---|
| `categories` | `parent_category_id` | `categories.category_id` |
| `products` | `category_id` | `categories.category_id` |
| `products` | `brand_id` | `brands.brand_id` |
| `offers` | `product_id` | `products.product_id` |
| `offers` | `retailer_id` | `retailers.retailer_id` |
| `price_history` | `offer_id` | `offers.offer_id` |

## 5. Database Setup

### Requirements

- PostgreSQL 17
- Python 3.9 or newer
- PostgreSQL command-line tools (`psql` and `createdb`)

The current migration runner is configured for PostgreSQL 17 installed through Homebrew on an Apple Silicon Mac. Users with different installations must update the `PSQL` path in `scripts/run_migrations.py`.

### Create the database

Run:

```bash
createdb pricematch_db
```

If PostgreSQL's command-line tools are not on your PATH, use their full installation paths.

### Run database migrations

From the project root, execute:

```bash
python3 scripts/run_migrations.py
```

The migration runner creates the migration-tracking table if necessary, checks previously applied migrations, and executes new migration files in order.

Existing migrations are skipped.

## 6. Migration Management

Database migration files are stored in:

`database/migrations/`

Current migration files:

- `000_migration_tracking.sql` — Creates the migration-tracking table.
- `001_initial_schema.sql` — Creates the six main database tables and their indexes.

Applied migrations are recorded in the `schema_migrations` table.

Future database changes should be implemented using new numbered migration files rather than modifying migrations that have already been applied.

## 7. Data Integrity

The database uses PostgreSQL constraints to maintain data integrity.

Implemented protections include:

- Primary keys to uniquely identify records.
- Foreign keys to prevent invalid references.
- Required fields using `NOT NULL`.
- Positive-price constraints for offers and price history.
- Unique brand names.
- Unique retailer website URLs.
- Unique product barcodes when provided.
- Prevention of duplicate product URLs within the same retailer.
- Prevention of categories referencing themselves directly as their parent.

These constraints help prevent inconsistent or invalid data from being stored.

## 8. Price Comparison

The database supports retrieving retailer offers for a product and sorting them by price.

Example query:

```sql
SELECT
    p.name AS product,
    r.name AS retailer,
    o.current_price,
    o.currency,
    o.product_url
FROM offers o
JOIN products p ON o.product_id = p.product_id
JOIN retailers r ON o.retailer_id = r.retailer_id
WHERE o.in_stock = TRUE
ORDER BY o.current_price ASC;
```

The first result represents the lowest-priced in-stock offer among the returned records. In production, comparisons should also account for currency and product variants.

## 9. Price History

The `price_history` table records the price of an offer at a specific time.

Each record contains:

- `history_id` — Unique history record identifier.
- `offer_id` — The corresponding retailer offer.
- `price` — Recorded price.
- `recorded_at` — Timestamp of the recorded price.

Historical prices can be used to analyze price changes over time.

## 10. Database Testing

The database has been tested locally using PostgreSQL 17.

Successful tests include:

- Creating all six main tables.
- Inserting example products and retailer offers.
- Comparing prices across three example retailers.
- Identifying the lowest-priced offer.
- Recording price history.
- Rejecting negative prices.
- Rejecting offers referencing nonexistent products.
- Rejecting duplicate retailer product URLs.
- Recognizing previously applied migrations.

Temporary test records were rolled back after testing.

## 11. Current Status

The database schema, migration tracking, migration runner, and initial integrity tests have been completed.

The database is currently empty and ready for integration with the project's product data collection and preprocessing components.

Future development includes importing real product data, integrating scraping pipelines, handling product matching across retailers, and connecting the database to the backend application.