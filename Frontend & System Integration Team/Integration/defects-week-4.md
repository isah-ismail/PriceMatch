# Week 4 Integration Defect & Issue Tracker

**Author:** System Integration, Testing & Deployment (Ayşe Özmen)  
**Date:** 26 November 2026 (Week 4 Milestone)  
**Status:** Open for Team Review & Component Owner Action  
**Component Scope:** Cross-layer Integration (Scrapers ➔ Database ➔ Backend API ➔ Frontend UI)

---

## 1. Executive Summary

During Week 4, the primary objective is to **make the data pipeline repeatable, verify ID consistency across layers, and connect matching results to database-backed search and offer retrieval**.

Following the Week 3 Defect Tracker, the Backend team (Yake) successfully integrated Migration 002 into the Backend ORM and Pydantic schemas via PR #10 (commit `bd48bf4`), resolving **DEF-01**, **DEF-02**, and **DEF-03**. All 25 backend integration tests are now passing.

This tracker documents the verification of closed issues and prioritizes active integration defects and architectural risks identified during Week 4 testing.

---

## 2. Status of Previous Defects (Week 3 ➔ Week 4)

| Issue ID | Original Severity | Component | Summary | Week 4 Status | Resolution Details |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **DEF-01** | **Critical** | Backend ORM (`models.py`) | `Offer` model missing `listing_id` and `condition`. | **CLOSED** | Resolved in commit `bd48bf4` (PR #10). `listing_id` and `condition` added to `Offer` with `uq_offers_listing_id` index and check constraints. |
| **DEF-02** | **Critical** | Backend API (`schemas.py`) | `product_url` was non-nullable in schema, causing 500 on null URLs. | **CLOSED** | Resolved in commit `bd48bf4` (PR #10). `product_url: str \| None = None` in `OfferOut` and `nullable=True` in `Offer` model. |
| **DEF-03** | **High** | Backend ORM (`models.py`) | Obsolete `UniqueConstraint("retailer_id", "product_url")` blocked variant imports. | **CLOSED** | Resolved in commit `bd48bf4` (PR #10). Dropped composite unique constraint. Multiple variants can now safely share store page URLs. |
| **DEF-04** | **Medium** | Matching ➔ Importer | Matching outputs pairwise comparisons rather than canonical ID groupings. | **IN PROGRESS** | Product Matching team (Iftikhar, Yake, Esra, Umut) completed 250-pair evaluation sets (Phones, Cosmetics, Cars, Dorms, Bikes). Next step: generate `(listing_id, canonical_product_id)` mapping table for the DB importer. |

---

## 3. Active Week 4 Defects & Integration Risks

| Issue ID | Severity | Component | Summary | Impact | Recommended Action / Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-05** | **High** | Frontend UI (`ProductDetail.jsx` / `ProductCard.jsx`) | Handling of nullable `product_url`: UI must not render broken `href="null"` or unclickable links. | If a listing has `product_url: null`, clicking "Mağazaya Git" leads to an invalid URL (`/null` or current page refresh). | Add conditional rendering: if `offer.product_url` is null/empty, render disabled badge *"Mağaza Linki Bulunmuyor"* instead of an active `<a>` link. (Frontend / Isah) |
| **DEF-06** | **High** | Database & Importer (`import_week3.py`) | Conservative 1-to-1 listing-to-product mapping creates duplicate cards in search results. | Search returns 3 separate cards for the same iPhone model across 3 stores instead of 1 product card with 3 comparison offers. | Once Matching team provides canonical mapping (DEF-04), update `import_week4.py` to group multiple `offers` under single `product_id`. (Database / Fatima & Matching) |
| **DEF-07** | **Medium** | Backend API & Frontend Contract | Query parameter naming consistency for price sorting. | Backend expects `sort_by` (`price_asc`, `price_desc`) or sort parameter. If Frontend passes `sort=asc`, it defaults to unsorted. | Ensure `integration-contract.md` query parameters are strictly honored: `/api/v1/products?q=...&sort=price_asc`. (Integration & Backend / Ayşe & Yake) |
| **DEF-08** | **Medium** | Scraper ➔ DB Pipeline | Currency standardization across stores. Watsons prices contained Turkish Lira symbols (`419,90 ₺`) whereas Gratis used float (`419.9`). | Database `current_price` column is `NUMERIC(12,2)`. Non-numeric currency strings fail DB import without custom parsing. | Standardize cleaner output so all price columns in `clean/` are plain numeric floats (`419.90`) before importer execution. (Data Cleaning / Esra & Fatima) |

---

## 4. Priority Matrix for Week 4 Sprint

```
    CRITICAL (Blocker for Demo)
    └── None currently blocking (Backend tests 25/25 passing)

    HIGH (Must Resolve for End-to-End Search & Comparison)
    ├── DEF-05: Frontend graceful fallback for nullable product_url
    └── DEF-06: Transition from 1:1 listings to multi-offer product grouping

    MEDIUM (Quality of Life & Contract Consistency)
    ├── DEF-04: Finalize canonical mapping table from matching sets
    ├── DEF-07: Verify sort parameter contract between Frontend and API
    └── DEF-08: Standardize scraper currency parsing across all retailers
```

---

## 5. Verification Checklist

- [x] Backend model mirrors Migration 002 (`listing_id`, `condition`, nullable `product_url`).
- [x] Backend schemas serialize `listing_id` and allow null `product_url` without validation error.
- [x] All 25 unit/integration tests in Backend test suite pass.
- [x] Smoke test runner passes all in-process health, catalog, and product checks.
- [ ] Frontend handles nullable `product_url` without broken anchor tags (DEF-05).
- [ ] Canonical product mapping applied to at least one category (Phones) to verify multi-offer UI (DEF-06).
