"""ORM models mirroring ``database/migrations/001_initial_schema.sql``.

Keep these in sync with the migrations. If the database team adds a migration,
update the matching model here.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# BIGINT identity on PostgreSQL; plain INTEGER on SQLite so autoincrement works in tests.
PK = BigInteger().with_variant(Integer, "sqlite")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "parent_category_id IS NULL OR parent_category_id <> category_id",
            name="categories_not_own_parent",
        ),
    )

    category_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    parent_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.category_id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    parent: Mapped[Category | None] = relationship(remote_side=[category_id], back_populates="children")
    children: Mapped[list[Category]] = relationship(back_populates="parent")
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Brand(Base):
    __tablename__ = "brands"

    brand_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    products: Mapped[list[Product]] = relationship(back_populates="brand")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("idx_products_name", "name"),
        Index("idx_products_category", "category_id"),
    )

    product_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.brand_id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(50), unique=True)
    model: Mapped[str | None] = mapped_column(String(150))
    variant: Mapped[str | None] = mapped_column(String(150))
    image_url: Mapped[str | None] = mapped_column(Text)

    category: Mapped[Category] = relationship(back_populates="products")
    brand: Mapped[Brand | None] = relationship(back_populates="products")
    offers: Mapped[list[Offer]] = relationship(back_populates="product")


class Retailer(Base):
    __tablename__ = "retailers"

    retailer_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    website_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    offers: Mapped[list[Offer]] = relationship(back_populates="retailer")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("retailer_id", "product_url"),
        CheckConstraint("current_price > 0", name="offers_current_price_positive"),
        Index("idx_offers_product_price", "product_id", "current_price"),
    )

    offer_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.retailer_id"), nullable=False)
    retailer_product_id: Mapped[str | None] = mapped_column(String(150))
    retailer_product_name: Mapped[str | None] = mapped_column(String(255))
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY", server_default="TRY")
    in_stock: Mapped[bool | None] = mapped_column(Boolean)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )

    product: Mapped[Product] = relationship(back_populates="offers")
    retailer: Mapped[Retailer] = relationship(back_populates="offers")
    history: Mapped[list[PriceHistory]] = relationship(back_populates="offer")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint("price > 0", name="price_history_price_positive"),
        Index("idx_price_history_offer_date", "offer_id", "recorded_at"),
    )

    history_id: Mapped[int] = mapped_column(PK, Identity(always=True), primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.offer_id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )

    offer: Mapped[Offer] = relationship(back_populates="history")
