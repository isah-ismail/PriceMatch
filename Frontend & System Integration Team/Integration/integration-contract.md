# Integration contract and decision register

Status: draft for cross-team review. No schema or algorithm decisions are enacted here.
Baseline: `f53cb3c`, reviewed 2026-11-05.

## Existing source interfaces

| Source | Daily join column | Specification column |
|---|---|---|
| Pozitif | product_id | retailer_product_id |
| Samsung | id | retailer_product_id |
| Beymen | UrunID | retailer_product_id |
| Marketzade, Hakmar, Sariyer, HappyCenter, Ideal | product_name, with source-specific legacy formats | name, resolving to retailer_product_id |

Joins are scoped to a retailer. Existing grocery documentation says names resolving to multiple listing IDs must not be linked. Joining daily prices to retailer listings is distinct from matching products across stores.

Electronics specification fields are defined by `SPEC_FIELDS`; groceries use `GROCERY_FIELDS` in [common.py](../../Data%20Collection%20%26%20Processing%20Team/scrapers/specs/common.py). Both include retailer, listing ID, name, brand, category, URLs, attributes and first/last seen dates. Electronics additionally include model and variant details; groceries include barcode and size.

Existing CSV readers use UTF-8 with BOM support. Preserve IDs and barcodes as strings. Specification first/last seen values are dates in Europe/Istanbul; they are not the price observation timestamp.

## Candidate mapping: requires approval

| Source concept | Existing database location | Unresolved point |
|---|---|---|
| retailer | retailers | Stable source-to-retailer lookup |
| retailer_product_id | offers.retailer_product_id | Requiredness and uniqueness |
| name | products.name / offers.retailer_product_name | Canonical versus retailer name ownership |
| model_code | products.model | Whether meaning and length are sufficient |
| barcode | products.barcode | Validation, conflicting evidence, empty string versus NULL |
| category / TÜİK codes | categories | Canonical mapping and hierarchy |
| url | offers.product_url | Missing URL policy |
| image_url | products.image_url | Provenance and fallback policy |
| price and source date | offers / price_history | Parsing, currency, observation time and deduplication |
| storage, RAM, colour, condition, bundle, size, attributes | No dedicated mapping agreed | Preserve data without inventing a variant representation |

Do not silently drop unmapped fields or assume that one barcode proves product equivalence. Existing documentation warns that image-derived barcodes can be misleading.

## Open decisions

Every item below is **open**. Suggested reviewers identify relevant roles, not confirmed assignees.

| ID | Decision needed | Evidence / risk | Suggested reviewers |
|---|---|---|---|
| INT-01 | Canonical listing identity and uniqueness | Data team specifies retailer + listing ID; schema currently uses retailer + URL uniqueness and nullable listing ID | Data, database/backend |
| INT-02 | Missing or invalid URL handling | Schema requires nonempty URL; daily sources may lack URLs; enrichment sometimes supplies them | Data, database/backend |
| INT-03 | Variant and condition representation | Current schema has model and variant text, without dedicated spec columns | Matching, database/backend |
| INT-04 | Grocery join normalization and ambiguity policy | Existing documentation rejects ambiguous names; legacy formats differ | Data, matching, integration |
| INT-05 | Canonical category mapping | Retailer paths and TÜİK codes differ from canonical categories | Matching/hierarchy, data, database |
| INT-06 | Price parsing, currency and observation time | History defaults to insertion time; source dates may have day-level precision | Data, database/backend |
| INT-07 | Import identity and replay behavior | History has no source-record deduplication constraint | Database/backend, integration |
| INT-08 | Late data, corrections and atomic updates | No importer currently coordinates current price and history | Database/backend, integration |
| INT-09 | Unresolved matching results and provenance | No matching output or confidence/review contract exists | Matching, integration, database |
| INT-10 | Stock and freshness semantics | Nullable in_stock and last_updated exist; missing listings do not prove out-of-stock | Data, backend, frontend |
| INT-11 | API request/response and error contracts | Existing read-only v1 API and samples are ready for frontend/backend confirmation | Backend, frontend, integration |
| INT-12 | Supported runtime and reproducible dependencies | Python minimum is documented; scraper dependencies use lower bounds | Component owners, integration |

## Frontend and backend API v1 review

**Status:** Ready for review. Backend confirmation from Yake and frontend confirmation from Isah are pending. The examples below come from the existing [backend API reference](../../Database%20%26%20Backend%20Development%20Team/backend/API.md). They are sample responses, and product IDs are specific to each example. Try the endpoints in [local interactive docs](http://127.0.0.1:8000/docs) when the backend is running.

| UI action | Request | Expected response |
| --- | --- | --- |
| Search products | `GET /api/v1/products?q=iphone&page=1` | `200` with `items` and pagination `meta`. No matches returns `200` with an empty `items` array. |
| Open a product | `GET /api/v1/products/{product_id}` | `200` with the product and offers. Use the ID returned by search. |
| Fetch offers separately | `GET /api/v1/products/{product_id}/offers` | `200` with an array of offer objects. |
| Show price history | `GET /api/v1/products/{product_id}/history?days=14` | `200` with one series per offer. A series may have no points in the requested period. |
| Fill filter menus | `GET /api/v1/categories`, `/api/v1/brands`, `/api/v1/retailers` | `200` with an array of catalog entries. |

### Sample responses

**Search · HTTP 200**

```json
{
  "items": [
    {
      "product_id": 2909,
      "name": "iPhone 17 Pro 256GB Kozmik Turuncu",
      "brand": {
        "brand_id": 1,
        "name": "Apple"
      },
      "category": {
        "category_id": 12,
        "name": "iPhone 17 Pro",
        "parent_category_id": 9
      },
      "model": "MG8Q4TU/A",
      "variant": "256 GB · Kozmik Turuncu",
      "image_url": "https://www.pt.com.tr/wp-content/uploads/....webp",
      "lowest_price": "122679.38",
      "currency": "TRY",
      "offer_count": 3,
      "retailer_count": 2
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Product detail · HTTP 200**

```json
{
  "product_id": 2909,
  "name": "USB-C 3,5 mm Kulaklık Jakı Adaptörü MW2Q3ZM/A",
  "brand": {
    "brand_id": 1,
    "name": "Apple"
  },
  "category": {
    "category_id": 1,
    "name": "Bilgi ve iletişim aksesuarları",
    "parent_category_id": null
  },
  "model": "MW2Q3ZM/A",
  "variant": null,
  "barcode": null,
  "image_url": "https://www.pt.com.tr/wp-content/uploads/2024/06/....webp",
  "lowest_price": "399.00",
  "currency": "TRY",
  "offer_count": 2,
  "retailer_count": 2,
  "offers": [
    {
      "offer_id": 5120,
      "retailer": {
        "retailer_id": 1,
        "name": "Pozitif Teknoloji"
      },
      "retailer_product_id": "367283",
      "retailer_product_name": "USB-C 3,5 mm Kulaklık Jakı Adaptörü MW2Q3ZM/A",
      "product_url": "https://www.pt.com.tr/usb-c-35-mm-kulaklik-jaki-adaptoru-mw2q3zm-a",
      "price": "399.00",
      "currency": "TRY",
      "in_stock": true,
      "last_updated": "2026-10-30T09:00:00Z",
      "is_lowest": true
    },
    {
      "offer_id": 11873,
      "retailer": {
        "retailer_id": 3,
        "name": "Beymen"
      },
      "retailer_product_id": "1721012",
      "retailer_product_name": "Apple USB-C 3.5 mm Kulaklık Jakı Adaptörü",
      "product_url": "https://www.beymen.com/tr/p_x_1721012",
      "price": "499.00",
      "currency": "TRY",
      "in_stock": true,
      "last_updated": "2026-10-30T09:00:00Z",
      "is_lowest": false
    }
  ]
}
```

**Price history · HTTP 200**

```json
{
  "product_id": 2909,
  "days": 14,
  "series": [
    {
      "offer_id": 5120,
      "retailer": {
        "retailer_id": 1,
        "name": "Pozitif Teknoloji"
      },
      "currency": "TRY",
      "points": [
        {
          "recorded_at": "2026-10-17T09:00:00Z",
          "price": "399.00"
        },
        {
          "recorded_at": "2026-10-18T09:00:00Z",
          "price": "399.00"
        }
      ]
    }
  ]
}
```

**Unknown product · HTTP 404**

```json
{
  "error": {
    "code": "not_found",
    "message": "Product 42 not found",
    "details": null
  }
}
```

### Review decisions

- [ ] **Backend and frontend:** Confirm endpoint paths, pagination and the shared `error.code`, `error.message` and `error.details` fields. A bad parameter returns `422` and a missing product returns `404`.
- [ ] **Frontend:** Confirm that prices are decimal strings paired with a currency such as `TRY`, and history timestamps carry a timezone.
- [ ] **Frontend and backend:** Confirm display behavior for missing images, empty result lists and `in_stock: null`. The API treats unknown stock as eligible for lowest-price calculations. The UI should distinguish it from confirmed stock.
- [ ] **Frontend:** Confirm that the chart accepts a history series with `points: []`.

Record each reviewer's decision, date and any requested changes here or link to the team discussion. Close INT-11 once both reviewers confirm the contract.

## Stack confirmation

This table records the stack visible in the repository. Each team should confirm the tools and versions it intends to support for local development. Review is pending.

| Area | Current stack | Confirmation needed |
| --- | --- | --- |
| Frontend | Static HTML, CSS and JavaScript | Frontend team confirms browser support and how to serve pages locally. |
| Backend | Python 3.12 in CI, FastAPI, Uvicorn, SQLAlchemy 2 and psycopg 3 | Backend team confirms Python 3.12 as the shared development version and notes any additional constraints. |
| Database | PostgreSQL 17 in CI and the local setup guide | Database team confirms PostgreSQL 17 and the migration workflow. |
| Data collection | Python, requests, Beautiful Soup 4 and lxml | Data team confirms its Python version and scraper requirements. |
| Product matching | Python, pandas, NumPy, RapidFuzz and scikit-learn | Matching team confirms its Python version and requirements. |
| Tests and CI | pytest, GitHub Actions, SQLite and PostgreSQL 17 | Integration and backend teams confirm which checks are expected for each change. |

Record each team's confirmation, date and any requested changes here. The Python dependencies currently listed in requirements files may allow a range of package versions. Confirm any reproducibility requirements with the relevant team before choosing exact pins.

References: [frontend entry page](../frontend/index.html), [backend requirements](../../Database%20%26%20Backend%20Development%20Team/backend/requirements.txt), [backend CI](../../.github/workflows/backend-tests.yml), [scraper requirements](../../Data%20Collection%20%26%20Processing%20Team/scrapers/requirements.txt) and [matching requirements](../../Product%20Matching%20%26%20Hierarchy%20Problem%20Team/requirements.txt).

## Proposed contract acceptance process

For each decision, record alternatives, chosen behavior, approving roles, date and affected documents. Until approved, keep it open. Capture sample valid, invalid, missing and ambiguous records with expected handling. Schema changes belong in a separately reviewed new migration; existing migrations must remain intact.

Proposed import reports should distinguish read, accepted, rejected, ambiguous, unresolved and duplicate records, retaining source file and row identity. Exact fields and storage remain open.

This document defines review questions and candidate mappings, not an executable contract.
