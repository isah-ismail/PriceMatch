# Week 3 Integration & Schema Consistency Report

**Author:** System Integration, Testing & Deployment (Ayşe Özmen)  
**Date:** 17 November 2026  
**Scope:** Verification of field names, identifiers, database schema, matching pipeline, backend models, and frontend contracts following the Week 3 updates.

---

## 1. Executive Summary

During Week 3, the project underwent significant architecture and data restructuring across three major teams:
1. **Data Collection Team (Umut):** Merged scrapers and cleaners, standardized to 3 key retailers (Beymen, Pozitif, Samsung), and introduced a two-tier identification scheme: `retailer_product_id` and unique `listing_id`.
2. **Database Team (Fatima):** Applied **Migration 002** (`002_listing_identity.sql`), added `listing_id` and `condition` to `offers`, made `product_url` nullable, relaxed uniqueness constraints, and imported 12,557 listings via `import_week3.py`.
3. **Product Matching Team (Iftikhar & Poyraz):** Implemented baseline matching on identifiers and normalized names, producing pairwise match CSVs (`product_matches.csv`, `unmatched_listings.csv`).

This audit evaluates whether data flows seamlessly across all boundaries:
`Scraper Data (CSV) ➔ Database (PostgreSQL) ➔ Backend ORM & API (FastAPI) ➔ Frontend (Web UI)`.

---

## 2. Identifier Consistency Matrix

| Entity / Concept | Data Collection (Clean CSV) | Database (PostgreSQL / Migration 002) | Backend ORM (`models.py`) | Backend API Schema (`schemas.py`) | Frontend UI (`components.js`) | Status / Alignment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Listing Identifier** | `listing_id` (`BEYMEN-xxx`, `POZITIF-xxx`, `SAMSUNG-xxx`) | `offers.listing_id` (VARCHAR(255), UNIQUE) | ❌ **Missing** in `Offer` model | ❌ **Missing** in `OfferOut` | Not displayed directly | **CRITICAL DEFECT (DEF-01)** |
| **Store Source Product ID** | `retailer_product_id` | `offers.retailer_product_id` (VARCHAR(150)) | `Offer.retailer_product_id` | `OfferOut.retailer_product_id` | Optional reference | ✅ **Aligned** |
| **Canonical Product ID** | None (Raw listings) | `products.product_id` (PK) | `Product.product_id` | `ProductSummary.product_id` | `product.product_id` (URL param `?id=`) | ✅ **Aligned** |
| **Product URL** | `url` (can be empty/missing) | `offers.product_url` (**Nullable** via Migration 002) | ⚠️ `product_url` still marked **`nullable=False`** | ❌ `product_url: str` (**Not Nullable**) | `if (offer.product_url) link.href = ...` (Safely handles null) | **CRITICAL DEFECT (DEF-02)** |
| **Offer Condition** | `condition` (`new`, etc.) | `offers.condition` (DEFAULT `'new'`, CHECK `new/display/used`) | ❌ **Missing** in `Offer` model | ❌ **Missing** in `OfferOut` | Not yet rendered | **DEFECT (DEF-03)** |
| **Retailer Name** | `retailer` (`Beymen`, `Pozitif`, `Samsung`) | `retailers.name` | `Retailer.name` | `RetailerRef.name` | `offer.retailer.name` | ✅ **Aligned** |
| **Current Price** | `price` (Numeric TRY) | `offers.current_price` (NUMERIC(12,2)) | `Offer.current_price` | `OfferOut.price` | `formatPrice(offer.price, offer.currency)` | ✅ **Aligned** |
| **Stock Status** | Scraper dependent (`quality_status`) | `offers.in_stock` (BOOLEAN, nullable) | `Offer.in_stock` | `OfferOut.in_stock` (bool \| None) | `offer.in_stock === true / false` | ✅ **Aligned** |

---

## 3. Detailed Component Audits & Gap Analysis

### 3.1 Data Collection ➔ Database Importer
- **Input:** 3 spec CSVs (`beymen_specs.csv`, `pozitif_specs.csv`, `samsung_specs.csv`) and timestamped price CSVs.
- **Verification:** All 3 spec files provide `listing_id`, `retailer_product_id`, `name`, `model_code`, `condition`, `quality_status`, `is_bundle`.
- **Importer behavior (`import_week3.py`):**
  - Filters `condition == 'new'`, `quality_status == 'ok'`, `is_bundle == 'False'`.
  - Creates products and offers mapping `listing_id` into `offers.listing_id`.
  - **Verdict:** Consistent and functional. 12,557 listings imported cleanly.

### 3.2 Database Schema ➔ Backend ORM & API (FastAPI)
- **Database state:** Migration 001 + Migration 002 applied.
  - `ALTER TABLE offers ADD COLUMN listing_id VARCHAR(255);`
  - `ALTER TABLE offers ADD COLUMN condition VARCHAR(10) NOT NULL DEFAULT 'new';`
  - `ALTER TABLE offers ALTER COLUMN product_url DROP NOT NULL;`
  - `ALTER TABLE offers DROP CONSTRAINT IF EXISTS offers_retailer_id_product_url_key;`
  - `CREATE UNIQUE INDEX uq_offers_listing_id ON offers(listing_id) WHERE listing_id IS NOT NULL;`
- **Backend Model Gaps (`models.py`):**
  - Line 96 still enforces `UniqueConstraint("retailer_id", "product_url")`. If multiple listings share a retailer URL (or have null URLs), insertion fails.
  - Line 106 defines `product_url: Mapped[str] = mapped_column(Text, nullable=False)`. It must be `nullable=True`.
  - `listing_id` and `condition` attributes are absent from the `Offer` class.
- **Backend Schema Gaps (`schemas.py`):**
  - `OfferOut` defines `product_url: str`. When a listing with a null URL is fetched from PostgreSQL, Pydantic raises a validation error (`500 Internal Server Error`).
  - `listing_id` and `condition` should be exposed in `OfferOut` for frontend clarity and debugging.

### 3.3 Product Matching Output ➔ Database Grouping
- **Current output:** Pairwise CSVs (`product_matches.csv`, e.g., `beymen_listing_id` paired with `pozitif_listing_id`).
- **Integration need:** The database currently isolates each store's listing as an individual canonical product (`product_id`) to avoid premature merging.
- **Action required for Week 4:** The matching team must export a consolidated mapping table: `(listing_id, canonical_product_id, confidence_score)`. The database team can then update `offers.product_id` to point equivalent retailer offers to the same canonical product.

---

## 4. Remediation Plan

1. **Immediate Backend Fix:**
   - Update `models.py` to mirror Migration 002 (`listing_id`, `condition`, nullable `product_url`, drop obsolete URL unique constraint).
   - Update `schemas.py` to allow `product_url: str | None = None` and add `listing_id: str | None = None`, `condition: str = "new"`.
2. **Contract Update:**
   - Revise `integration-contract.md` with Week 3 schema changes and updated sample JSON payloads.
3. **Smoke Tests:**
   - Implement `test_smoke.py` to automatically assert that all endpoints return valid schemas and handle nullable fields without server crashes.
