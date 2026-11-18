"""PriceMatch System Integration Smoke Test Runner.

Author: System Integration, Testing & Deployment (Ayşe Özmen)
Description: Standalone CLI smoke test tool to verify backend API, database connectivity,
catalog routes, offer comparison, and error envelopes.

Usage:
    python smoke_test.py [--url http://127.0.0.1:8000]
    or run in-process against SQLite test fixture:
    python smoke_test.py
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

        p1 = Product(name="iPhone 17 Pro 256GB Kozmik Turuncu", brand=apple, category=iphone,
                     model="MG8Q4TU/A", variant="256 GB · Kozmik Turuncu", image_url="https://img/1.webp")
        db.add(p1)
        db.flush()

        o1 = Offer(product=p1, retailer=pozitif, retailer_product_id="367283", product_url="https://www.pt.com.tr/iphone-17-pro",
                   current_price=Decimal("125999.00"), in_stock=True, last_updated=now)
        o2 = Offer(product=p1, retailer=beymen, retailer_product_id="1865304", product_url="https://www.beymen.com/tr/p_x_1865304",
                   current_price=Decimal("119999.00"), in_stock=False, last_updated=now)
        o3 = Offer(product=p1, retailer=samsung, retailer_product_id="X1", product_url="https://www.samsung.com/tr/x1",
                   current_price=Decimal("122679.38"), in_stock=None, last_updated=now)
        db.add_all([o1, o2, o3])
        db.commit()

    def _override_get_db():
        with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def run_standalone_smoke(base_url: str | None = None, in_memory: bool = False):
    print("=" * 65)
    print("        PRICEMATCH SYSTEM INTEGRATION SMOKE TEST")
    print("=" * 65)

    if in_memory or not base_url:
        print("[INFO] Initializing in-process TestClient with test database...")
        try:
            client = setup_in_memory_db()
            get = client.get
        except Exception as e:
            print(f"[FAIL] Failed to initialize in-process test client: {e}")
            sys.exit(1)
    else:
        print(f"[INFO] Running smoke checks against live backend: {base_url}")
        import urllib.request
        import json

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
                        data = {}
                    return type("Resp", (), {"status_code": e.code, "json": lambda: data, "text": str(e)})()

        get = LiveClient().get

    checks = []

    def check(name, success, details=""):
        status = "PASS" if success else "FAIL"
        checks.append(success)
        print(f"[{status}] {name:35} {details}")

    # 1. Health check
    r = get("/health")
    check("GET /health", r.status_code == 200 and r.json().get("status") == "ok", f"(status={r.json().get('status')}, db={r.json().get('database')})")

    # 2. Interactive documentation
    r = get("/docs")
    check("GET /docs", r.status_code == 200, "(Swagger UI accessible)")

    # 3. Categories
    r = get("/api/v1/categories")
    cats = r.json() if r.status_code == 200 else []
    check("GET /api/v1/categories", r.status_code == 200 and len(cats) > 0, f"({len(cats)} categories returned)")

    # 4. Brands
    r = get("/api/v1/brands")
    brands = r.json() if r.status_code == 200 else []
    check("GET /api/v1/brands", r.status_code == 200 and len(brands) > 0, f"({len(brands)} brands returned)")

    # 5. Retailers
    r = get("/api/v1/retailers")
    ret = r.json() if r.status_code == 200 else []
    stores = {s.get("name") for s in ret}
    check("GET /api/v1/retailers", r.status_code == 200 and len(ret) >= 3, f"(Stores: {', '.join(sorted(stores))})")

    # 6. Product Search
    r = get("/api/v1/products")
    prods = r.json().get("items", []) if r.status_code == 200 else []
    check("GET /api/v1/products", r.status_code == 200 and len(prods) > 0, f"({len(prods)} products in catalog)")

    # 7. Query Search
    r = get("/api/v1/products?q=iPhone")
    query_items = r.json().get("items", []) if r.status_code == 200 else []
    check("GET /api/v1/products?q=iPhone", r.status_code == 200 and len(query_items) > 0, f"({len(query_items)} matching products)")

    # 8. Product Detail & Offers
    p_id = query_items[0]["product_id"] if query_items else (prods[0]["product_id"] if prods else 1)
    r = get(f"/api/v1/products/{p_id}")
    detail = r.json() if r.status_code == 200 else {}
    offers = detail.get("offers", [])
    has_lowest = any(o.get("is_lowest") for o in offers)
    check(f"GET /api/v1/products/{p_id}", r.status_code == 200 and len(offers) > 0, f"({len(offers)} offers, lowest flagged: {has_lowest})")

    # 9. Error Envelope
    r = get("/api/v1/products/999999")
    err = r.json().get("error", {})
    check("GET /api/v1/products/999999 (404)", r.status_code == 404 and err.get("code") == "not_found", f"(Error envelope: {err.get('code')})")

    print("-" * 65)
    passed_count = sum(1 for c in checks if c)
    total_count = len(checks)
    if passed_count == total_count:
        print(f"RESULT: ALL {total_count} SMOKE CHECKS PASSED! [System Integration Healthy]")
        print("=" * 65)
        return 0
    else:
        print(f"RESULT: {passed_count}/{total_count} CHECKS PASSED. [Failures Detected]")
        print("=" * 65)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PriceMatch Smoke Test Runner")
    parser.add_argument("--url", help="URL of running backend server (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--in-memory", action="store_true", help="Run in-process against test database")
    args = parser.parse_args()

    sys.exit(run_standalone_smoke(base_url=args.url, in_memory=args.in_memory or not args.url))
