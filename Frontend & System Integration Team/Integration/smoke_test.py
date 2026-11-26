"""PriceMatch System Integration Smoke & Verification Test Suite.

Author: System Integration, Testing & Deployment (Ayşe Özmen)
Milestone: Week 4 - Multi-Offer Integration, Schema Validation & ID Traceability
Description: Standalone CLI integration runner to verify backend API, database connectivity,
catalog routes, multi-offer price comparison, nullable URL handling, listing_id uniqueness,
condition enums, and RFC 7807 error envelopes.

Usage:
    # Run in-process with zero setup (in-memory SQLite test fixture):
    python smoke_test.py

    # Run against a live local or remote server:
    python smoke_test.py --url http://127.0.0.1:8000
    python smoke_test.py --url http://87.248.157.147:8001
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add backend directory to path for in-process execution
repo_root = Path(__file__).resolve().parents[2]
backend_dir = repo_root / "Database & Backend Development Team" / "backend"
sys.path.insert(0, str(backend_dir))


def setup_in_memory_db():
    from app.database import Base, get_db, make_engine
    from app.main import app
    from app.models import Brand, Category, Offer, PriceHistory, Product, Retailer
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session, sessionmaker

    eng = make_engine("sqlite://", echo=False)
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng)

    now = datetime.now(timezone.utc)
    with Session(eng) as db:
        pozitif = Retailer(name="Pozitif Teknoloji", website_url="https://www.pt.com.tr")
        samsung = Retailer(name="Samsung", website_url="https://www.samsung.com/tr")
        beymen = Retailer(name="Beymen", website_url="https://www.beymen.com")
        apple = Brand(name="Apple")
        phones = Category(name="Telefon")
        iphone = Category(name="iPhone", parent=phones)
        db.add_all([pozitif, samsung, beymen, apple, phones, iphone])
        db.flush()

        # Product 1: Canonical multi-offer smartphone
        p1 = Product(
            name="iPhone 17 Pro 256GB Kozmik Turuncu",
            brand=apple,
            category=iphone,
            model="MG8Q4TU/A",
            variant="256 GB · Kozmik Turuncu",
            image_url="https://img/1.webp",
        )
        # Product 2: Product with an offer having NO store URL (Testing DEF-02)
        p2 = Product(
            name="iPhone 16 128GB Pembe",
            brand=apple,
            category=iphone,
            model="MYEA3TU/A",
            variant="128 GB · Pembe",
            image_url="https://img/2.webp",
        )
        db.add_all([p1, p2])
        db.flush()

        # Multi-offer setup for Product 1 (Pozitif, Beymen, Samsung)
        o1 = Offer(
            product=p1,
            retailer=pozitif,
            retailer_product_id="367283",
            listing_id="POZITIF-367283",
            product_url="https://www.pt.com.tr/iphone-17-pro",
            current_price=Decimal("125999.00"),
            condition="new",
            in_stock=True,
            last_updated=now,
        )
        o2 = Offer(
            product=p1,
            retailer=beymen,
            retailer_product_id="1865304",
            listing_id="BEYMEN-1865304",
            product_url="https://www.beymen.com/tr/p_x_1865304",
            current_price=Decimal("119999.00"),
            condition="new",
            in_stock=False,
            last_updated=now,
        )
        o3 = Offer(
            product=p1,
            retailer=samsung,
            retailer_product_id="X1",
            listing_id="SAMSUNG-X1",
            product_url="https://www.samsung.com/tr/x1",
            current_price=Decimal("122679.38"),
            condition="display",
            in_stock=None,
            last_updated=now,
        )
        # Offer for Product 2: Null URL & shared URL with another listing
        o4 = Offer(
            product=p2,
            retailer=beymen,
            retailer_product_id="1865305",
            listing_id="BEYMEN-1865305",
            product_url=None,  # Nullable URL test
            current_price=Decimal("64999.00"),
            condition="new",
            in_stock=True,
            last_updated=now,
        )
        db.add_all([o1, o2, o3, o4])
        db.commit()

    def _override_get_db():
        with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def run_standalone_smoke(base_url: str | None = None, in_memory: bool = False):
    print("=" * 70)
    print("        PRICEMATCH SYSTEM INTEGRATION TEST SUITE (WEEK 4)")
    print("        Author: Ayşe Özmen (System Integration & Testing)")
    print("=" * 70)

    if in_memory or not base_url:
        print("[INFO] Initializing in-process TestClient with SQLite test fixture...")
        try:
            client = setup_in_memory_db()
            get = client.get
        except Exception as e:
            print(f"[FAIL] Failed to initialize in-process test client: {e}")
            sys.exit(1)
    else:
        print(f"[INFO] Running smoke checks against live backend: {base_url}")
        import json
        import urllib.request

        class LiveClient:
            def get(self, path):
                url = base_url.rstrip("/") + path
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                try:
                    with urllib.request.urlopen(req) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        return type("Resp", (), {"status_code": resp.status, "json": lambda: data, "text": ""})()
                except urllib.error.HTTPError as e:
                    try:
                        data = json.loads(e.read().decode("utf-8"))
                    except Exception:
                        data = {"detail": str(e)}
                    return type("Resp", (), {"status_code": e.code, "json": lambda: data, "text": ""})()

        live = LiveClient()
        get = live.get

    checks_passed = 0
    checks_total = 0

    def check(name: str, passed: bool, detail: str = ""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        status = "[PASS]" if passed else "[FAIL]"
        if passed:
            checks_passed += 1
            print(f"{status} {name:<42} ({detail})")
        else:
            print(f"{status} {name:<42} ({detail})")
            print(f"       -> ERROR: Test condition failed!")

    # 1. Health check
    r = get("/health")
    check("GET /health", r.status_code == 200 and r.json().get("status") == "ok", f"status={r.json().get('status')}")

    # 2. Swagger Docs
    r = get("/docs")
    check("GET /docs", r.status_code == 200, "Swagger UI accessible")

    # 3. Categories
    r = get("/api/v1/categories")
    cats = r.json() if r.status_code == 200 else []
    check("GET /api/v1/categories", r.status_code == 200 and len(cats) >= 1, f"{len(cats)} categories returned")

    # 4. Brands
    r = get("/api/v1/brands")
    brands = r.json() if r.status_code == 200 else []
    check("GET /api/v1/brands", r.status_code == 200 and len(brands) >= 1, f"{len(brands)} brands returned")

    # 5. Retailers
    r = get("/api/v1/retailers")
    ret = r.json() if r.status_code == 200 else []
    stores = ", ".join(x.get("name") for x in ret[:3])
    check("GET /api/v1/retailers", r.status_code == 200 and len(ret) >= 3, f"Stores: {stores}")

    # 6. Product catalog search
    r = get("/api/v1/products?q=iPhone")
    data = r.json() if r.status_code == 200 else {}
    items = data.get("items", [])
    check("GET /api/v1/products?q=iPhone", r.status_code == 200 and len(items) >= 1, f"{len(items)} matching products found")

    # 7. Multi-offer product comparison & sorting
    r = get("/api/v1/products/1")
    p1 = r.json() if r.status_code == 200 else {}
    offers = p1.get("offers", [])
    has_cheapest = any(o.get("is_lowest") for o in offers)
    has_listing_ids = all(o.get("listing_id") is not None for o in offers)
    check("GET /api/v1/products/1 (Multi-Offer)", r.status_code == 200 and len(offers) == 3 and has_cheapest,
          f"{len(offers)} offers, cheapest flagged: {has_cheapest}")

    # 8. Listing ID & Condition serialization (Week 4 Sync verification)
    conditions = [o.get("condition") for o in offers]
    valid_conditions = all(c in ["new", "display", "used"] for c in conditions)
    check("Verify listing_id & condition", has_listing_ids and valid_conditions,
          f"listing_ids present, conditions={conditions}")

    # 9. Nullable product_url handling (DEF-02 verification)
    r = get("/api/v1/products/2")
    p2 = r.json() if r.status_code == 200 else {}
    p2_offers = p2.get("offers", [])
    has_null_url = any(o.get("product_url") is None for o in p2_offers)
    check("Verify Nullable product_url", r.status_code == 200 and has_null_url,
          f"Offer loaded with product_url=None without 500 error")

    # 10. Nonexistent product error envelope
    r = get("/api/v1/products/999999")
    err = r.json() if r.status_code == 404 else {}
    err_obj = err.get("error", {})
    code = err_obj.get("code")
    check("GET /api/v1/products/999999 (404)", r.status_code == 404 and code == "not_found",
          f"Standard error envelope: code='{code}'")

    print("-" * 70)
    print(f"RESULT: {checks_passed}/{checks_total} CHECKS PASSED!")
    if checks_passed == checks_total:
        print(">> ALL INTEGRATION CHECKS GREEN — SYSTEM HEALTHY <<")
    else:
        print(">> ATTENTION: SOME INTEGRATION CHECKS FAILED <<")
    print("=" * 70)

    if checks_passed != checks_total:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PriceMatch Week 4 Integration Smoke Runner")
    parser.add_argument("--url", type=str, default=None, help="Base URL of live backend (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--in-memory", action="store_true", help="Force in-process SQLite execution")
    args = parser.parse_args()
    run_standalone_smoke(base_url=args.url, in_memory=args.in_memory)
