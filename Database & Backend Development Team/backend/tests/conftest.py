"""Test fixtures: an in-memory SQLite database with a small, known dataset.

Set ``TEST_DATABASE_URL`` to run the same tests against PostgreSQL, e.g.
``TEST_DATABASE_URL=postgresql+psycopg://postgres:pw@localhost:5432/pricematch_test``.
The tables are created from the ORM models and dropped afterwards.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db, make_engine
from app.main import app
from app.models import Brand, Category, Offer, PriceHistory, Product, Retailer

TEST_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture(scope="session")
def engine():
    eng = make_engine(TEST_URL, echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="session")
def seeded(engine) -> dict:
    """Insert the dataset once per test session and return the ids the tests need."""
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        pozitif = Retailer(name="Pozitif Teknoloji", website_url="https://www.pt.com.tr")
        samsung = Retailer(name="Samsung", website_url="https://www.samsung.com/tr")
        beymen = Retailer(name="Beymen", website_url="https://www.beymen.com")
        apple = Brand(name="Apple")
        sams = Brand(name="Samsung")
        phones = Category(name="Telefon")
        iphone = Category(name="iPhone", parent=phones)
        accessories = Category(name="Aksesuar")
        db.add_all([pozitif, samsung, beymen, apple, sams, phones, iphone, accessories])
        db.flush()

        # Product sold by 3 stores; Beymen is cheapest but out of stock.
        p1 = Product(name="iPhone 17 Pro 256GB Kozmik Turuncu", brand=apple, category=iphone,
                     model="MG8Q4TU/A", variant="256 GB · Kozmik Turuncu", image_url="https://img/1.webp")
        # Product sold by one store.
        p2 = Product(name="Galaxy A18 128GB Açık Mavi", brand=sams, category=phones, model="SM-A185FLBDTUR")
        # Product with no offers at all.
        p3 = Product(name="iPhone 17 Pro Kılıfı", brand=None, category=accessories)
        # Cheap accessory to check price filters / sorting.
        p4 = Product(name="USB-C Kablo", brand=apple, category=accessories, model="MW2Q3ZM/A")
        db.add_all([p1, p2, p3, p4])
        db.flush()

        o1 = Offer(product=p1, retailer=pozitif, retailer_product_id="367283", product_url="https://www.pt.com.tr/iphone-17-pro",
                   current_price=Decimal("125999.00"), in_stock=True, last_updated=now)
        o2 = Offer(product=p1, retailer=beymen, retailer_product_id="1865304", product_url="https://www.beymen.com/tr/p_x_1865304",
                   current_price=Decimal("119999.00"), in_stock=False, last_updated=now)
        o3 = Offer(product=p1, retailer=samsung, retailer_product_id="X1", product_url="https://www.samsung.com/tr/x1",
                   current_price=Decimal("122679.38"), in_stock=None, last_updated=now)
        o4 = Offer(product=p2, retailer=samsung, retailer_product_id="SM-A185FLBDTUR", product_url="https://www.samsung.com/tr/a18",
                   current_price=Decimal("17999.00"), in_stock=True, last_updated=now)
        o5 = Offer(product=p4, retailer=pozitif, retailer_product_id="9", product_url="https://www.pt.com.tr/usb-c",
                   current_price=Decimal("399.00"), in_stock=True, last_updated=now)
        db.add_all([o1, o2, o3, o4, o5])
        db.flush()

        for i, price in enumerate(["129999.00", "127999.00", "125999.00"]):
            db.add(PriceHistory(offer=o1, price=Decimal(price), recorded_at=now - timedelta(days=2 - i)))
        db.add(PriceHistory(offer=o1, price=Decimal("139999.00"), recorded_at=now - timedelta(days=100)))
        db.add(PriceHistory(offer=o3, price=Decimal("122679.38"), recorded_at=now))
        db.commit()

        return {
            "p_multi": p1.product_id, "p_single": p2.product_id, "p_no_offers": p3.product_id, "p_cheap": p4.product_id,
            "r_pozitif": pozitif.retailer_id, "r_samsung": samsung.retailer_id, "r_beymen": beymen.retailer_id,
            "b_apple": apple.brand_id, "c_phones": phones.category_id, "c_iphone": iphone.category_id,
            "c_acc": accessories.category_id, "o_pozitif": o1.offer_id, "o_beymen": o2.offer_id,
        }


@pytest.fixture
def client(engine, seeded) -> TestClient:
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def ids(seeded) -> dict:
    return seeded
