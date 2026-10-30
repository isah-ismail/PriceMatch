from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..errors import ApiError, NotFoundError
from ..schemas import (
    ErrorResponse,
    OfferOut,
    OfferSortOption,
    Page,
    PageMeta,
    ProductDetail,
    ProductHistory,
    ProductSummary,
    SortOption,
)
from ..services import products as svc

router = APIRouter(prefix="/products", tags=["products"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Product not found"}}
VALIDATION = {422: {"model": ErrorResponse, "description": "Invalid query parameters"}}


def _load_product(db: Session, product_id: int):
    product = svc.get_product(db, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


@router.get(
    "",
    response_model=Page[ProductSummary],
    responses=VALIDATION,
    summary="Search products",
    description=(
        "Full-text-ish search over product name, model code, variant and brand. "
        "Every word in `q` must match. Results carry the cheapest in-stock price. "
        "Default sort is `relevance`; use `price_asc` for cheapest first."
    ),
)
def search_products(
    q: Annotated[str | None, Query(max_length=200, description="Search text, e.g. `iphone 17 pro 256`")] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    brand_id: Annotated[int | None, Query(ge=1)] = None,
    retailer_id: Annotated[int | None, Query(ge=1, description="Only products sold by this store")] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    in_stock: Annotated[bool | None, Query(description="true = at least one in-stock offer")] = None,
    sort: SortOption = SortOption.relevance,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, description="Defaults to DEFAULT_PAGE_SIZE, capped at MAX_PAGE_SIZE")] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Page[ProductSummary]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ApiError(
            "min_price must be less than or equal to max_price",
            code="validation_error",
            status_code=422,
            details=[{"field": "min_price", "in": "query", "message": "greater than max_price"}],
        )
    size = min(page_size or settings.default_page_size, settings.max_page_size)

    items, total = svc.search_products(
        db,
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        retailer_id=retailer_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort=sort,
        page=page,
        page_size=size,
    )
    total_pages = (total + size - 1) // size if total else 0
    return Page[ProductSummary](
        items=[ProductSummary.model_validate(i) for i in items],
        meta=PageMeta(
            page=page,
            page_size=size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1 and total_pages > 0,
        ),
    )


@router.get(
    "/{product_id}",
    response_model=ProductDetail,
    responses={**NOT_FOUND, **VALIDATION},
    summary="Product with all offers (cheapest first)",
)
def get_product(product_id: Annotated[int, Path(ge=1)], db: Session = Depends(get_db)) -> ProductDetail:
    product = _load_product(db, product_id)
    return ProductDetail.model_validate(svc.product_detail_dict(product))


@router.get(
    "/{product_id}/offers",
    response_model=list[OfferOut],
    responses={**NOT_FOUND, **VALIDATION},
    summary="Offers of a product, sorted by price",
)
def get_offers(
    product_id: Annotated[int, Path(ge=1)],
    sort: OfferSortOption = OfferSortOption.price_asc,
    in_stock_only: bool = False,
    db: Session = Depends(get_db),
) -> list[OfferOut]:
    product = _load_product(db, product_id)
    return [OfferOut.model_validate(o) for o in svc.sorted_offers(product.offers, sort=sort, in_stock_only=in_stock_only)]


@router.get(
    "/{product_id}/history",
    response_model=ProductHistory,
    responses={**NOT_FOUND, **VALIDATION},
    summary="Price history per offer",
)
def get_history(
    product_id: Annotated[int, Path(ge=1)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    retailer_id: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
) -> ProductHistory:
    product = _load_product(db, product_id)
    series = svc.price_history(db, product, days=days, retailer_id=retailer_id)
    return ProductHistory.model_validate({"product_id": product_id, "days": days, "series": series})
