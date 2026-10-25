-- PriceMatch Database
-- Migration 001: Initial database schema

CREATE TABLE categories (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_category_id BIGINT REFERENCES categories(category_id),
    name VARCHAR(150) NOT NULL CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT categories_not_own_parent
        CHECK (parent_category_id IS NULL OR parent_category_id <> category_id)
);

CREATE TABLE brands (
    brand_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
        CHECK (LENGTH(TRIM(name)) > 0)
);

CREATE TABLE products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES categories(category_id),
    brand_id BIGINT REFERENCES brands(brand_id),
    name VARCHAR(255) NOT NULL CHECK (LENGTH(TRIM(name)) > 0),
    barcode VARCHAR(50) UNIQUE,
    model VARCHAR(150),
    variant VARCHAR(150),
    image_url TEXT
);

CREATE TABLE retailers (
    retailer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(150) NOT NULL CHECK (LENGTH(TRIM(name)) > 0),
    website_url TEXT NOT NULL UNIQUE
        CHECK (LENGTH(TRIM(website_url)) > 0)
);

CREATE TABLE offers (
    offer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    retailer_id BIGINT NOT NULL REFERENCES retailers(retailer_id),
    retailer_product_id VARCHAR(150),
    retailer_product_name VARCHAR(255),
    product_url TEXT NOT NULL CHECK (LENGTH(TRIM(product_url)) > 0),
    current_price NUMERIC(12,2) NOT NULL CHECK (current_price > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'TRY',
    in_stock BOOLEAN,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (retailer_id, product_url)
);

CREATE TABLE price_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offer_id BIGINT NOT NULL REFERENCES offers(offer_id),
    price NUMERIC(12,2) NOT NULL CHECK (price > 0),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_name ON products(name);

CREATE INDEX idx_products_category ON products(category_id);

CREATE INDEX idx_offers_product_price
    ON offers(product_id, current_price);

CREATE INDEX idx_price_history_offer_date
    ON price_history(offer_id, recorded_at DESC);