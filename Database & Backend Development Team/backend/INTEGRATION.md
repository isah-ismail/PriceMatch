# Backend ↔ other teams

What the backend consumes, what it produces, and what is still open.
Owner: Yake (Backend & API). Updated 2026‑10‑30.

## Fatima — database (Team 03)

**Using now:** `database/migrations/001_initial_schema.sql` as is. `app/models.py`
mirrors it 1:1; please ping me whenever you add a migration so I update the ORM.

**Requests for migration `002`** (all come from Team 01's README + the demo load):

| Change | Why |
|---|---|
| `offers.product_url` → nullable, and `UNIQUE (retailer_id, retailer_product_id)` | A listing is identified by `(retailer, retailer_product_id)`. Vatan's daily prices have no URL. Today the unique key is `(retailer_id, product_url)`, so a missing URL cannot be stored. |
| `offers.condition VARCHAR(10) NOT NULL DEFAULT 'new'` (`new` / `display` / `used`) | Team 01 asks us never to compare a *teşhir* unit with a new one. For now I encode it in `products.variant` text, which is not filterable. |
| `products.model` should be indexed (`CREATE INDEX idx_products_model ON products(model)`) | Search matches on model code; it is also the join key for Team 02's output. |
| Optional: `pg_trgm` extension + `GIN (name gin_trgm_ops)` on `products` | Real relevance ranking and tolerant search (`iphone` vs `İphone`). Week 7 performance item. |
| Optional: `products.source` / `match_method` text | So the UI can say "matched by model code" vs "matched by name similarity" (Team 02 output). |

**Queries the API runs** (so you can check indexes): per‑product `MIN(current_price) FILTER (in_stock IS NOT FALSE)`, `COUNT(DISTINCT retailer_id)` over `offers`; `ILIKE` on `products.name / model / variant` and `brands.name`; `price_history` by `offer_id` + `recorded_at >= now() - N days`. The existing `idx_offers_product_price` and `idx_price_history_offer_date` are exactly what those need.

## Umut & Esra — data (Team 01)

The seed script reads your spec files unchanged (`data/specs/*_specs.csv`, columns as in your README) and joins daily prices on
`retailer_product_id` ↔ `product_id` (Pozitif) / `id` (Samsung) / `UrunID` (Beymen). 14 days of prices gave 13,571 offers; 2,251 spec rows had no price in that window and were skipped.

What would help:

* A `condition` and `model_code` that are never empty strings (use empty, not `nan`).
* Vatan: once the daily file carries a link or id, add it to `RETAILERS` in `scripts/seed_demo_data.py` (one dict entry) and it is in.
* Esra: when the cleaned/normalised dataset exists, I will read it instead of the raw spec files. Please keep `retailer`, `retailer_product_id`, `model_code`, `name`, `brand`, `category`, `url`, `image_url`, `condition` as column names.

## Iftikhar & Poyraz — matching (Team 02)

**Today:** the seed script uses the baseline you were going to start from — listings with the same `model_code` (and same `condition`) are one product; everything else is its own product. 385 products currently have offers from 2+ listings.

**Proposed output format** for your matcher (CSV or JSONL, one row per listing):

| column | example | meaning |
|---|---|---|
| `retailer` | `Beymen` | as in the spec files |
| `retailer_product_id` | `1865304` | join key |
| `canonical_id` | `MG8Q4TU/A` or `grp_000123` | same value ⇒ same product |
| `canonical_name` | `iPhone 17 Pro 256GB Kozmik Turuncu` | display name for the product |
| `method` | `model_code` / `name_similarity` / `manual` | how the decision was made |
| `score` | `0.93` | optional confidence |
| `status` | `confirmed` / `uncertain` | **uncertain rows are not merged**; they stay separate products |

Give me that file and the backend will import it into `products` / `offers` (a small `scripts/apply_matches.py`, not written yet because there is no input). Your evaluation set (Poyraz) can then be checked against live API answers: `GET /api/v1/products/{id}` lists exactly the listings the system considers the same product.

**Known false match for your error analysis:** product `USB-C 3,5 mm Kulaklık Jakı Adaptörü MW2Q3ZM/A` currently has three offers (399 ₺, 499 ₺, 1 599 ₺). The 1 599 ₺ Beymen row is a different product whose name contains the same model code. Model code from names (Beymen) is weaker than model code from a store API (Pozitif/Samsung).

## Isah — frontend (Team 04)

* Everything you need is in [`API.md`](API.md); the interactive version is `/docs`.
* Search page → `GET /api/v1/products?q=…&page=…`; filter menus → `/categories`, `/brands`, `/retailers`.
* Product page → `GET /api/v1/products/{id}` (offers already sorted, `is_lowest` flagged, `product_url` is the "go to store" link).
* Price chart → `GET /api/v1/products/{id}/history?days=30`.
* `image_url` can be `null` (Beymen) — show a placeholder. `in_stock` can be `null` — show nothing rather than "in stock".
* Errors always have `error.code`; switch on it, show `error.message`.
* CORS is open in dev. Tell me the deployed origin and I will put it in `CORS_ORIGINS`.

## Ayşe — integration & deployment (Team 04)

* Run instructions: `backend/README.md`. Secrets only through `.env` / environment; `.env.example` lists them.
* Tests: `cd backend && pytest` (SQLite, no services) — the workflow `.github/workflows/backend-tests.yml` runs this on every push/PR touching the backend. Set `TEST_DATABASE_URL` in CI to also run on a PostgreSQL service container.
* Smoke test for the integrated build: `GET /health` → 200, `GET /api/v1/products?q=iphone` → `meta.total_items > 0`, `GET /api/v1/products/{first id}` → `offers` non‑empty.
* Hosting: the app is a plain ASGI service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`); Render/Railway/Fly all work with `DATABASE_URL` pointing at a managed PostgreSQL.
