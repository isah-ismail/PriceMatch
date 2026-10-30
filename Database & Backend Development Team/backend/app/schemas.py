"""Pydantic response models = the JSON contract with the frontend (see API.md)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SortOption(str, Enum):
    relevance = "relevance"
    price_asc = "price_asc"
    price_desc = "price_desc"
    name_asc = "name_asc"
    name_desc = "name_desc"


class OfferSortOption(str, Enum):
    price_asc = "price_asc"
    price_desc = "price_desc"


# ---------------------------------------------------------------- shared bits


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


# ------------------------------------------------------------------ catalog


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    name: str
    parent_category_id: int | None = None
    product_count: int = 0


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    name: str
    product_count: int = 0


class RetailerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    retailer_id: int
    name: str
    website_url: str
    offer_count: int = 0


class RetailerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    retailer_id: int
    name: str


class BrandRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    name: str


class CategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    name: str
    parent_category_id: int | None = None


# ----------------------------------------------------------------- products


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: int
    retailer: RetailerRef
    retailer_product_id: str | None = None
    retailer_product_name: str | None = None
    product_url: str
    price: Decimal = Field(description="Current price, 2 decimals")
    currency: str
    in_stock: bool | None = Field(None, description="true/false, or null when the store does not say")
    last_updated: datetime
    is_lowest: bool = Field(False, description="True for the cheapest in-stock offer of the product")


class ProductSummary(BaseModel):
    """One search-result card."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    name: str
    brand: BrandRef | None = None
    category: CategoryRef
    model: str | None = None
    variant: str | None = None
    image_url: str | None = None
    lowest_price: Decimal | None = Field(None, description="Cheapest in-stock offer; null if no offer")
    currency: str = "TRY"
    offer_count: int = 0
    retailer_count: int = 0


class ProductDetail(ProductSummary):
    barcode: str | None = None
    offers: list[OfferOut] = Field(default_factory=list, description="Sorted by price ascending")


class PricePoint(BaseModel):
    recorded_at: datetime
    price: Decimal


class OfferHistory(BaseModel):
    offer_id: int
    retailer: RetailerRef
    currency: str
    points: list[PricePoint]


class ProductHistory(BaseModel):
    product_id: int
    days: int
    series: list[OfferHistory]


# ------------------------------------------------------------------- health


class HealthOut(BaseModel):
    status: str
    database: str
    version: str
