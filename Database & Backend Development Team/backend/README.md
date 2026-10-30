# PriceMatch Backend API (Team 03 — Yake)

FastAPI service that sits between Fatima's PostgreSQL schema and Isah's frontend.
It answers three questions: *which products match my search?*, *who sells this
product and for how much?*, *how did its price change?*

| | |
|---|---|
| Framework | FastAPI + SQLAlchemy 2 + psycopg 3, Python 3.12 |
| Schema | `../database/migrations` (owned by the database team; the ORM in `app/models.py` mirrors it) |
| Contract | [`API.md`](API.md) — every endpoint with sample requests/responses |
| Other teams | [`INTEGRATION.md`](INTEGRATION.md) — what the backend needs from / gives to each team |
| Interactive docs | `http://127.0.0.1:8000/docs` once running |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + database check |
| GET | `/api/v1/products` | Search with filters, sort, pagination |
| GET | `/api/v1/products/{id}` | Product + all offers, cheapest first |
| GET | `/api/v1/products/{id}/offers` | Offers only (sort, in-stock filter) |
| GET | `/api/v1/products/{id}/history` | Price history per offer |
| GET | `/api/v1/categories` · `/brands` · `/retailers` | Filter lists with counts |

All errors share one envelope: `{"error": {"code", "message", "details"}}`.

## Run it locally

```bash
# 1. database (once) — see ../database/README.md
createdb pricematch_db
python3 ../scripts/run_migrations.py

# 2. backend
cd backend
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # edit DATABASE_URL if needed

# 3. demo data (optional, needs the inflation study's Datas folder)
python scripts/seed_demo_data.py --reset --days 14 --datas /path/to/InflationResearchStudy/InflationItems/Datas

# 4. serve
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs>. `requests.http` has ready-made calls
(VS Code *REST Client* / JetBrains HTTP client).

No local PostgreSQL? Run one in Docker:

```bash
docker run -d --name pricematch-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=pricematch_db -p 5432:5432 postgres:17-alpine
docker exec -i pricematch-pg psql -U postgres -d pricematch_db < ../database/migrations/000_migration_tracking.sql
docker exec -i pricematch-pg psql -U postgres -d pricematch_db < ../database/migrations/001_initial_schema.sql
```

### Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/pricematch_db` | SQLAlchemy URL |
| `CORS_ORIGINS` | `*` | Comma-separated browser origins allowed to call the API |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | Pagination |
| `INFLATION_DATAS` | — | Daily price CSV root, only for the seed script |

`.env` is git-ignored. Commit `.env.example` instead.

## Demo data

`scripts/seed_demo_data.py` fills Fatima's tables from what already exists:

* **Team 01 spec files** (`Data Collection & Processing Team/data/specs/*_specs.csv`) → `products`, `brands`, `categories`, `offers` (name, model code, colour, storage, link, image).
* **Inflation study daily prices** (`InflationItems/Datas/08_Communication/{PozitifTeknoloji,Samsung,Beymen}`) → `offers.current_price` and `price_history`, joined on the store's own product id.

Until Team 02 delivers the matcher, listings with the same manufacturer
`model_code` (and the same condition) are merged into one product. With 14 days
of prices (2026‑10‑17 … 2026‑10‑30) this gives:

| retailers | brands | categories | products | offers | history points | products sold by 2+ listings |
|---|---|---|---|---|---|---|
| 3 | 47 | 146 | 13,002 | 13,571 | 176,112 | 385 |

Rerunning with `--reset` replaces everything; without it the script refuses to
touch a non-empty database.

## Tests

```bash
pytest                       # 23 tests on an in-memory SQLite copy of the schema, < 1 s
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pricematch_test pytest   # same tests on PostgreSQL
```

The GitHub Actions workflow `.github/workflows/backend-tests.yml` runs them on every push/PR that touches the backend.

## Layout

```
backend/
  app/
    main.py            FastAPI app factory, CORS, routers
    config.py          Settings from .env / environment
    database.py        engine + session dependency
    models.py          ORM mirror of database/migrations/001_initial_schema.sql
    schemas.py         Pydantic response models (= JSON contract)
    errors.py          one error envelope for 404 / 422 / 500 / 503
    routers/           health, products, catalog (thin HTTP layer)
    services/          SQL queries (search, offers, history, catalog lists)
  scripts/seed_demo_data.py
  tests/               pytest + FastAPI TestClient
  API.md  INTEGRATION.md  requests.http  .env.example  requirements.txt
```

## Status against the 8-week plan

| Week | Task (Yake) | Status |
|---|---|---|
| 1 | Compare frameworks, draft endpoints, request/response flow, DB + matcher integration outline | done — `API.md`, `INTEGRATION.md` |
| 2 | Backend project + config, health endpoint, search/offer formats, DB via env vars, local setup docs | done |
| 3 | DB access functions, search + offer endpoints, validation/errors, sample requests/responses | done |
| 4 | Search on real DB, offer retrieval + price sorting, standard response, pagination, missing-product handling | done (demo data) |
| 5 | Complete search, alternatives, standard errors, representative tests, endpoint docs | done; relevance ranking is a heuristic |
| 6 | Integrate Team 02 matching output, response times | **waiting on Team 02** (format agreed in `INTEGRATION.md`) |
| 7 | Edge-case tests, response times, defects | partial: tests exist; perf work (pg_trgm, indexes) not started |
| 8 | Final docs + demo | — |

Known gaps / next steps:

* Search ranking is `retailer_count desc, name length, price`. Proper relevance needs `pg_trgm` similarity (also handles Turkish `İ/ı`).
* Schema needs `offers.condition` (new/display/used) and a unique key on `(retailer_id, retailer_product_id)` — requested from Fatima in `INTEGRATION.md`.
* Some Beymen model codes are parsed from names, so a few "matched" products are wrong (example in `INTEGRATION.md`). That is the matching team's input, not something the API should hide.
