# PriceMatch API contract (v1)

Base URL (local): `http://127.0.0.1:8000`. All endpoints are `GET` and return JSON.
Prices are strings with two decimals (`"17999.00"`) so that nothing is lost to
floating point; `currency` is ISO‑4217 (`TRY`). Timestamps are ISO‑8601 with
timezone. Interactive version: `/docs`.

## Error envelope

Every non‑2xx response:

```json
{
  "error": {
    "code": "not_found",
    "message": "Product 42 not found",
    "details": null
  }
}
```

| HTTP | `code` | When | `details` |
|---|---|---|---|
| 404 | `not_found` | unknown product id / route | `null` |
| 422 | `validation_error` | bad query/path parameter | list of `{field, in, message, type}` |
| 503 | `service_unavailable` | database unreachable (`/health`) | exception class name |
| 500 | `internal_error` | unexpected | `null` |

Example 422:

```json
{"error": {"code": "validation_error", "message": "Request validation failed",
  "details": [{"field": "page", "in": "query", "message": "Input should be greater than or equal to 1", "type": "greater_than_equal"}]}}
```

---

## `GET /health`

```json
{"status": "ok", "database": "ok", "version": "0.1.0"}
```
`503` with the error envelope if the database cannot be reached.

---

## `GET /api/v1/products` — search

| Query param | Type | Default | Notes |
|---|---|---|---|
| `q` | string ≤200 | — | Every word must match name, model code, variant or brand (case‑insensitive). `iphone 17 pro 256` |
| `category_id` | int ≥1 | — | The category or any of its direct sub‑categories |
| `brand_id` | int ≥1 | — | |
| `retailer_id` | int ≥1 | — | Only products this store sells |
| `min_price`, `max_price` | decimal ≥0 | — | Applied to the product's lowest in‑stock price; `min > max` → 422 |
| `in_stock` | bool | — | `true`: has ≥1 in‑stock offer; `false`: none |
| `sort` | `relevance` · `price_asc` · `price_desc` · `name_asc` · `name_desc` | `relevance` | Products without offers go last in price sorts |
| `page` | int ≥1 | 1 | |
| `page_size` | int ≥1 | 20 | Capped at 100 |

Response `200`:

```json
{
  "items": [
    {
      "product_id": 2909,
      "name": "iPhone 17 Pro 256GB Kozmik Turuncu",
      "brand": {"brand_id": 1, "name": "Apple"},
      "category": {"category_id": 12, "name": "iPhone 17 Pro", "parent_category_id": 9},
      "model": "MG8Q4TU/A",
      "variant": "256 GB · Kozmik Turuncu",
      "image_url": "https://www.pt.com.tr/wp-content/uploads/....webp",
      "lowest_price": "122679.38",
      "currency": "TRY",
      "offer_count": 3,
      "retailer_count": 2
    }
  ],
  "meta": {"page": 1, "page_size": 20, "total_items": 15, "total_pages": 1, "has_next": false, "has_prev": false}
}
```

* `lowest_price` = cheapest offer whose `in_stock` is not `false` (unknown stock counts). `null` when the product has no offer.
* `brand` and `image_url` may be `null` (Beymen has no images; show another store's image or a placeholder).
* An empty result is `200` with `items: []`, never `404`.

Examples:

```
/api/v1/products?q=galaxy%20s25&sort=price_asc
/api/v1/products?category_id=9&min_price=40000&max_price=60000&page=2&page_size=12
/api/v1/products?retailer_id=1&in_stock=true
```

---

## `GET /api/v1/products/{product_id}` — product + offers

`404` if unknown; `422` if the id is not a positive integer.

```json
{
  "product_id": 2909,
  "name": "USB-C 3,5 mm Kulaklık Jakı Adaptörü MW2Q3ZM/A",
  "brand": {"brand_id": 1, "name": "Apple"},
  "category": {"category_id": 1, "name": "Bilgi ve iletişim aksesuarları", "parent_category_id": null},
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
      "retailer": {"retailer_id": 1, "name": "Pozitif Teknoloji"},
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
      "retailer": {"retailer_id": 3, "name": "Beymen"},
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

* `offers` are sorted by price ascending **including** out‑of‑stock ones, so the UI can grey them out.
* Exactly one offer has `is_lowest: true` (the cheapest with `in_stock != false`), or none if all are out of stock.
* `in_stock`: `true` / `false` / `null` (store did not say).

---

## `GET /api/v1/products/{product_id}/offers`

Same offer objects as above, as a bare list.

| Query param | Default | Notes |
|---|---|---|
| `sort` | `price_asc` | or `price_desc` |
| `in_stock_only` | `false` | drop offers with `in_stock == false` |

---

## `GET /api/v1/products/{product_id}/history`

| Query param | Default | Notes |
|---|---|---|
| `days` | 30 | 1…365 |
| `retailer_id` | — | only that store's offers |

```json
{
  "product_id": 2909,
  "days": 14,
  "series": [
    {
      "offer_id": 5120,
      "retailer": {"retailer_id": 1, "name": "Pozitif Teknoloji"},
      "currency": "TRY",
      "points": [
        {"recorded_at": "2026-10-17T09:00:00Z", "price": "399.00"},
        {"recorded_at": "2026-10-18T09:00:00Z", "price": "399.00"}
      ]
    }
  ]
}
```

One series per offer, points oldest → newest. An offer with no points in the window still appears with `points: []`.

---

## Catalog lists (for filter menus)

`GET /api/v1/categories` — parents first, then sub‑categories; `product_count` of a parent includes its sub‑categories.

```json
[{"category_id": 9, "name": "iPhone", "parent_category_id": null, "product_count": 112},
 {"category_id": 12, "name": "iPhone 17 Pro", "parent_category_id": 9, "product_count": 8}]
```

`GET /api/v1/brands`

```json
[{"brand_id": 1, "name": "Apple", "product_count": 950}]
```

`GET /api/v1/retailers`

```json
[{"retailer_id": 3, "name": "Beymen", "website_url": "https://www.beymen.com", "offer_count": 11840}]
```

---

## Conventions

* Read‑only API; no authentication for the MVP.
* CORS: configured by `CORS_ORIGINS` (default allow all during development).
* Versioned under `/api/v1`; breaking changes go to `/api/v2`.
* IDs in responses are the database's `product_id` / `offer_id` / … — the frontend should treat them as opaque integers.
