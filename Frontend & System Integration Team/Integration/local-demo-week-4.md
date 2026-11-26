# Week 4 Local Demo & Integration Run Guide

**Author:** System Integration, Testing & Deployment (Ayşe Özmen)  
**Milestone:** Week 4 Team Meeting & Progress Demonstration  
**Target:** Local Execution, Multi-Store Comparison Verification & Smoke Runner

---

## 1. Overview

This guide provides step-by-step instructions for running the integrated PriceMatch system locally. It demonstrates that the Week 4 deliverables—**repeatable pipeline, multi-offer comparison, ID traceability, and robust edge-case handling**—are fully operational.

---

## 2. Fast Track: Automated Integration Smoke Test

To verify all system integration contracts and edge cases in under 3 seconds without needing a running PostgreSQL instance, execute the in-process test runner:

```powershell
# Open terminal in repository root
cd "C:\Users\Lenovo\Desktop\cimri\PriceMatch"

# Run smoke test runner using project virtual environment
& ".venv\Scripts\python.exe" "Frontend & System Integration Team\Integration\smoke_test.py"
```

**Expected Output:**
```
======================================================================
        PRICEMATCH SYSTEM INTEGRATION TEST SUITE (WEEK 4)
        Author: Ayşe Özmen (System Integration & Testing)
======================================================================
[INFO] Initializing in-process TestClient with SQLite test fixture...
[PASS] GET /health                                (status=ok)
[PASS] GET /docs                                  (Swagger UI accessible)
[PASS] GET /api/v1/categories                     (2 categories returned)
[PASS] GET /api/v1/brands                         (1 brands returned)
[PASS] GET /api/v1/retailers                      (Stores: Beymen, Pozitif Teknoloji, Samsung)
[PASS] GET /api/v1/products?q=iPhone              (2 matching products found)
[PASS] GET /api/v1/products/1 (Multi-Offer)       (3 offers, cheapest flagged: True)
[PASS] Verify listing_id & condition              (listing_ids present, conditions=['new', 'display', 'new'])
[PASS] Verify Nullable product_url                (Offer loaded with product_url=None without 500 error)
[PASS] GET /api/v1/products/999999 (404)          (Standard error envelope: code='not_found')
----------------------------------------------------------------------
RESULT: 10/10 CHECKS PASSED!
>> ALL INTEGRATION CHECKS GREEN — SYSTEM HEALTHY <<
======================================================================
```

---

## 3. Running Backend API Locally

To start the FastAPI backend server with full interactive documentation:

```powershell
cd "C:\Users\Lenovo\Desktop\cimri\PriceMatch\Database & Backend Development Team\backend"
& "..\..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

* **API Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
* **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Product Catalog:** [http://127.0.0.1:8000/api/v1/products](http://127.0.0.1:8000/api/v1/products)

---

## 4. Running the Smoke Test Against a Live Server

Once the backend (or live server) is running, you can test live endpoints by supplying the `--url` argument:

```powershell
# Against local running backend:
python "Frontend & System Integration Team\Integration\smoke_test.py" --url http://127.0.0.1:8000

# Against live deployment:
python "Frontend & System Integration Team\Integration\smoke_test.py" --url http://87.248.157.147:8001
```

---

## 5. Meeting Demo Scenarios (What to Present to the Team)

During the Friday 4:30 PM progress meeting, Ayşe can present the following 4 key achievements:

### Scenario A: Closed Week 3 Defects (DEF-01, DEF-02, DEF-03)
* **Explanation:** Show `defects-week-4.md`. Explain that through our defect tracking, Yake was able to resolve all 3 backend inconsistencies in PR #10, aligning `Offer` models with Migration 002.
* **Evidence:** Show that 25/25 backend unit tests pass.

### Scenario B: Multi-Store Comparison & Cheapest Flag
* **Explanation:** Show `GET /api/v1/products/1` in Swagger UI or test output.
* **Demonstration:** Point out that 1 canonical product aggregates offers from 3 different stores (Beymen, Pozitif, Samsung), and the system automatically identifies and flags the lowest price (`is_lowest: true` for Beymen at 119,999 ₺).

### Scenario C: Cross-Layer ID Traceability
* **Explanation:** Show `consistency-report-week-4.md`. Explain how `listing_id` (e.g. `BEYMEN-1865304`) is uniquely maintained from Scraper to Database, API, and Frontend, eliminating variant collisions.

### Scenario D: Edge Case Resilience (Null URLs & Shared URLs)
* **Explanation:** Show that listings without an online URL (e.g. store-only products) no longer crash the backend with 500 errors, returning a clean `null` that the frontend can handle gracefully.
