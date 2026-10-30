"""Database queries behind the product endpoints.

Everything that touches SQL for products/offers lives here so the routers stay
thin and the queries can be unit-tested on SQLite and run on PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Brand, Category, Offer, PriceHistory, Product, Retailer
from ..schemas import OfferSortOption, SortOption

# An offer counts towards the "lowest price" unless the store explicitly says it is out of stock.
_IN_STOCK = Offer.in_stock.isnot(False)


def offer_aggregate_subquery():
    """Per-product aggregates: lowest in-stock price, number of offers, number of stores."""
    return (
        select(
            Offer.product_id.label("product_id"),
            func.min(case((_IN_STOCK, Offer.current_price))).label("lowest_price"),
            func.count(Offer.offer_id).label("offer_count"),
            func.count(func.distinct(Offer.retailer_id)).label("retailer_count"),
        )
        .group_by(Offer.product_id)
        .subquery("offer_agg")
    )


def _apply_filters(
    stmt: Select,
    agg,
    *,
    q: str | None,
    category_id: int | None,
    brand_id: int | None,
    retailer_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    in_stock: bool | None,
) -> Select:
    if q:
        tokens = [t for t in q.strip().split() if t]
        for token in tokens:
            pattern = f"%{token}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern),
                    Product.model.ilike(pattern),
                    Product.variant.ilike(pattern),
                    Brand.name.ilike(pattern),
                )
            )
    if category_id is not None:
        # Match the category itself or its direct sub-categories.
        stmt = stmt.where(or_(Product.category_id == category_id, Category.parent_category_id == category_id))
    if brand_id is not None:
        stmt = stmt.where(Product.brand_id == brand_id)
    if retailer_id is not None:
        stmt = stmt.where(
            select(Offer.offer_id)
            .where(and_(Offer.product_id == Product.product_id, Offer.retailer_id == retailer_id))
            .exists()
        )
    if min_price is not None:
        stmt = stmt.where(agg.c.lowest_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(agg.c.lowest_price <= max_price)
    if in_stock is True:
        stmt = stmt.where(agg.c.lowest_price.isnot(None))
    elif in_stock is False:
        stmt = stmt.where(agg.c.lowest_price.is_(None))
    return stmt


def search_products(
    db: Session,
    *,
    q: str | None = None,
    category_id: int | None = None,
    brand_id: int | None = None,
    retailer_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    sort: SortOption = SortOption.relevance,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Return (rows, total). Each row is a dict ready for ``ProductSummary``."""
    agg = offer_aggregate_subquery()

    base = (
        select(Product, Brand, Category, agg.c.lowest_price, agg.c.offer_count, agg.c.retailer_count)
        .join(Category, Product.category_id == Category.category_id)
        .outerjoin(Brand, Product.brand_id == Brand.brand_id)
        .outerjoin(agg, agg.c.product_id == Product.product_id)
    )
    base = _apply_filters(
        base,
        agg,
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        retailer_id=retailer_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
    )

    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0

    lowest = agg.c.lowest_price
    if sort == SortOption.relevance:
        # Cheap heuristic until pg_trgm ranking: products sold by more stores first, then
        # shorter names (the phone itself beats "... Kılıfı" accessories), then price.
        order = [
            func.coalesce(agg.c.retailer_count, 0).desc(),
            func.length(Product.name).asc(),
            case((lowest.is_(None), 1), else_=0),
            lowest.asc(),
        ]
    elif sort == SortOption.price_asc:
        order = [case((lowest.is_(None), 1), else_=0), lowest.asc(), Product.name.asc()]
    elif sort == SortOption.price_desc:
        order = [case((lowest.is_(None), 1), else_=0), lowest.desc(), Product.name.asc()]
    elif sort == SortOption.name_desc:
        order = [Product.name.desc()]
    else:
        order = [Product.name.asc()]
    order.append(Product.product_id.asc())  # stable paging

    rows = db.execute(base.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()

    items = [
        {
            "product_id": product.product_id,
            "name": product.name,
            "brand": brand,
            "category": category,
            "model": product.model,
            "variant": product.variant,
            "image_url": product.image_url,
            "lowest_price": lowest_price,
            "currency": "TRY",
            "offer_count": offer_count or 0,
            "retailer_count": retailer_count or 0,
        }
        for product, brand, category, lowest_price, offer_count, retailer_count in rows
    ]
    return items, int(total)


def get_product(db: Session, product_id: int) -> Product | None:
    return db.scalar(
        select(Product)
        .where(Product.product_id == product_id)
        .options(
            selectinload(Product.brand),
            selectinload(Product.category),
            selectinload(Product.offers).selectinload(Offer.retailer),
        )
    )


def sorted_offers(
    offers: list[Offer], *, sort: OfferSortOption = OfferSortOption.price_asc, in_stock_only: bool = False
) -> list[dict]:
    """Serialize offers sorted by price and flag the cheapest in-stock one."""
    rows = [o for o in offers if not (in_stock_only and o.in_stock is False)]
    rows.sort(key=lambda o: (o.current_price, o.retailer.name), reverse=(sort == OfferSortOption.price_desc))

    lowest_id = None
    candidates = [o for o in offers if o.in_stock is not False]
    if candidates:
        lowest_id = min(candidates, key=lambda o: (o.current_price, o.retailer.name)).offer_id

    return [
        {
            "offer_id": o.offer_id,
            "retailer": o.retailer,
            "retailer_product_id": o.retailer_product_id,
            "retailer_product_name": o.retailer_product_name,
            "product_url": o.product_url,
            "price": o.current_price,
            "currency": o.currency,
            "in_stock": o.in_stock,
            "last_updated": o.last_updated,
            "is_lowest": o.offer_id == lowest_id,
        }
        for o in rows
    ]


def product_detail_dict(product: Product) -> dict:
    offers = sorted_offers(product.offers)
    in_stock_prices = [o["price"] for o in offers if o["in_stock"] is not False]
    return {
        "product_id": product.product_id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "model": product.model,
        "variant": product.variant,
        "barcode": product.barcode,
        "image_url": product.image_url,
        "lowest_price": min(in_stock_prices) if in_stock_prices else None,
        "currency": offers[0]["currency"] if offers else "TRY",
        "offer_count": len(product.offers),
        "retailer_count": len({o.retailer_id for o in product.offers}),
        "offers": offers,
    }


def price_history(
    db: Session, product: Product, *, days: int = 30, retailer_id: int | None = None
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    offer_ids = [o.offer_id for o in product.offers if retailer_id is None or o.retailer_id == retailer_id]
    if not offer_ids:
        return []

    rows = db.execute(
        select(PriceHistory.offer_id, PriceHistory.recorded_at, PriceHistory.price)
        .where(PriceHistory.offer_id.in_(offer_ids), PriceHistory.recorded_at >= since)
        .order_by(PriceHistory.offer_id, PriceHistory.recorded_at)
    ).all()

    by_offer: dict[int, list[dict]] = {oid: [] for oid in offer_ids}
    for offer_id, recorded_at, price in rows:
        by_offer[offer_id].append({"recorded_at": recorded_at, "price": price})

    offers_by_id = {o.offer_id: o for o in product.offers}
    return [
        {
            "offer_id": oid,
            "retailer": offers_by_id[oid].retailer,
            "currency": offers_by_id[oid].currency,
            "points": points,
        }
        for oid, points in by_offer.items()
    ]


# ------------------------------------------------------------------ catalog


def list_categories(db: Session) -> list[dict]:
    count_sq = (
        select(Product.category_id, func.count(Product.product_id).label("n"))
        .group_by(Product.category_id)
        .subquery()
    )
    rows = db.execute(
        select(Category, func.coalesce(count_sq.c.n, 0))
        .outerjoin(count_sq, count_sq.c.category_id == Category.category_id)
        .order_by(Category.parent_category_id.nulls_first(), Category.name)
    ).all()
    own = {c.category_id: int(n) for c, n in rows}
    totals = dict(own)
    for c, n in rows:  # a parent also counts the products of its direct sub-categories
        if c.parent_category_id is not None:
            totals[c.parent_category_id] = totals.get(c.parent_category_id, 0) + int(n)
    return [
        {
            "category_id": c.category_id,
            "name": c.name,
            "parent_category_id": c.parent_category_id,
            "product_count": totals[c.category_id],
        }
        for c, _ in rows
    ]


def list_brands(db: Session) -> list[dict]:
    count_sq = select(Product.brand_id, func.count(Product.product_id).label("n")).group_by(Product.brand_id).subquery()
    rows = db.execute(
        select(Brand, func.coalesce(count_sq.c.n, 0))
        .outerjoin(count_sq, count_sq.c.brand_id == Brand.brand_id)
        .order_by(Brand.name)
    ).all()
    return [{"brand_id": b.brand_id, "name": b.name, "product_count": int(n)} for b, n in rows]


def list_retailers(db: Session) -> list[dict]:
    count_sq = select(Offer.retailer_id, func.count(Offer.offer_id).label("n")).group_by(Offer.retailer_id).subquery()
    rows = db.execute(
        select(Retailer, func.coalesce(count_sq.c.n, 0))
        .outerjoin(count_sq, count_sq.c.retailer_id == Retailer.retailer_id)
        .order_by(Retailer.name)
    ).all()
    return [
        {"retailer_id": r.retailer_id, "name": r.name, "website_url": r.website_url, "offer_count": int(n)}
        for r, n in rows
    ]
