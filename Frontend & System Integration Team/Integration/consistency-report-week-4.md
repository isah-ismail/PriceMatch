# Week 4 Schema Consistency & Cross-Layer ID Audit Report

**Author:** System Integration, Testing & Deployment (Ayşe Özmen)  
**Date:** 26 November 2026 (Week 4 Milestone)  
**Target Architecture:** Repeatable Pipeline, Multi-Offer Retrieval & Cross-Layer ID Traceability  
**Status:** Audit Completed — System Integration Operational

---

## 1. Executive Summary

In Week 4, the integration scope transitioned from initial schema synchronization to **cross-layer end-to-end data validation**. This report audits:
1. Complete traceability of entity identifiers (`listing_id`, `retailer_product_id`, `product_id`, `offer_id`) across all project layers.
2. Validation of multi-offer product aggregation (comparing prices of the same canonical product across multiple retailers).
3. Verification of edge cases: nullable URLs, variant collisions, condition attributes, and price sorting.

**Audit Result:** The synchronization between Migration 002 and the Backend ORM/Schemas is verified. All 25 automated backend tests and 10 standalone smoke test checks pass with zero regressions.

---

## 2. Cross-Layer ID Traceability Matrix

A common failure mode in multi-retailer aggregation is identifier confusion. Below is the authoritative field mapping verified across all 5 architectural layers:

```
[Retailer Website] 
       │ (Scraped by Team 1)
       ▼
[Clean Spec CSV] ──► listing_id: "BEYMEN-1865304", retailer_product_id: "1865304"
       │ (Imported by Database Team)
       ▼
[PostgreSQL Database] ──► offers.listing_id (UNIQUE), offers.retailer_product_id, offers.product_id (FK)
       │ (Queried by Backend API)
       ▼
[FastAPI Backend] ──► OfferOut { listing_id, condition, current_price, product_url, retailer }
       │ (Rendered by Frontend)
       ▼
[React Frontend UI] ──► Product comparison card showing cheapest offer badge and retailer list
```

### Detailed Traceability Specification

| Entity / Concept | Layer 1: Scraper CSV | Layer 2: Clean Specs | Layer 3: PostgreSQL | Layer 4: Backend API | Layer 5: Frontend UI | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Store Listing ID** | `product_id` (raw) | `listing_id` | `offers.listing_id` | `OfferOut.listing_id` | Offer item key | Authoritative unique listing identifier. Format: `<STORE>-<RAW_ID>`. |
| **Retailer Source ID** | `product_id` (raw) | `retailer_product_id` | `offers.retailer_product_id` | `OfferOut.retailer_product_id` | Not exposed (internal) | Raw ID assigned by the retailer. May duplicate across color variants. |
| **Canonical Product ID** | None (unmapped) | None | `products.product_id` | `ProductOut.product_id` | `/products/:id` route param | Primary key of the shared canonical product. Groups multiple store offers. |
| **Offer Primary Key** | Row index | Row index | `offers.offer_id` | `OfferOut.offer_id` | Table row key | Internal database surrogate key for individual seller listings. |
| **Category ID** | `category_number` | `category_number` | `categories.category_id` | `CategoryOut.category_id` | Category filter pill | References hierarchical category tree (`parent_category_id`). |

---

## 3. Multi-Offer Retrieval & Price Sorting Audit

A core requirement of Week 4 is connecting matching results to multi-offer retrieval. 

### In-Process Test Fixture Verification
Using a multi-store product fixture (`iPhone 17 Pro 256GB Kozmik Turuncu`), the API was tested for:
1. **Multi-Offer Retrieval:** `GET /api/v1/products/1` returned 3 distinct offers:
   - Pozitif Teknoloji: 125,999.00 ₺ (`listing_id: "367283"`, `in_stock: true`, `condition: "new"`)
   - Beymen: 119,999.00 ₺ (`listing_id: "1865304"`, `in_stock: false`, `condition: "new"`)
   - Samsung: 122,679.38 ₺ (`listing_id: "X1"`, `in_stock: null`, `condition: "display"`)
2. **Cheapest Offer Flagging:** The lowest price offer (Beymen at 119,999.00 ₺) was correctly flagged with `is_lowest: true`, enabling the UI to highlight the best deal.
3. **Price Sorting:** `GET /api/v1/products?sort_by=price_asc` orders results by minimum available offer price.

---

## 4. Edge-Case Validation & Robustness Analysis

| Test Case | Scenario / Condition | Expected Behavior | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **TC-01: Nullable Product URL** | An offer imported without a store page URL (`product_url: null`). | API returns `200 OK` with `"product_url": null`. No Pydantic validation error or 500 crash. | Passed (`test_products.py::test_product_detail_allows_null_url`). | **PASS** |
| **TC-02: Shared URL Variants** | Two distinct color/storage variants sharing the identical retailer URL. | Database accepts both offers without unique constraint violation; differentiated by `listing_id`. | Passed (`test_products.py::test_shared_product_url_across_offers`). | **PASS** |
| **TC-03: Offer Condition Enum** | Offers with condition `'new'`, `'display'`, or `'used'`. | Database enforces `CHECK (condition IN ('new', 'display', 'used'))`. API serializes condition. | Passed (`test_products.py::test_product_detail_exposes_condition`). | **PASS** |
| **TC-04: Nonexistent Product** | Querying an unassigned product ID (`GET /api/v1/products/999999`). | Returns `404 Not Found` with standardized RFC 7807 problem detail envelope (`type: "not_found"`). | Passed (Smoke test check 9). | **PASS** |
| **TC-05: Blank Listing ID** | Null listing_id in offer table. | Partial index `WHERE listing_id IS NOT NULL` allows nulls but enforces strict uniqueness for non-null values. | Passed in PostgreSQL Migration 002. | **PASS** |

---

## 5. Live Deployment Status Check

The team's live deployment was verified at `87.248.157.147:8001`:
* **Live UI Status:** Reachable on port `8001`.
* **Category Dropdown:** Synchronized with Week 3/4 categories.
* **Search Execution:** Live search queries are dispatched to the backend API.
* **Recommendation:** Run smoke test suite with `--url http://87.248.157.147:8001` during the deployment gate check before release.

---

## 6. Recommendations for Week 5 Transition

1. **Frontend Null URL Handling (DEF-05):** In `ProductDetail.jsx`, verify that `offer.product_url ? <a href={offer.product_url}> : <span>` prevents broken anchor tags.
2. **Canonical Mapping Integration (DEF-04 & DEF-06):** In Week 5, ingest the matching team's 250-pair results (Phones, Cosmetics, Cars, Dorms, Bikes) through an updated `import_week5.py` to merge listings into multi-store product cards in PostgreSQL.
3. **Automated CI/CD Integration:** Integrate `smoke_test.py` into a GitHub Actions workflow on pull requests to `main`.
