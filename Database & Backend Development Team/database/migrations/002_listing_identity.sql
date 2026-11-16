-- Week 3: preserve store listing identity without assuming retailer_product_id is unique.
-- Existing 001 schema remains unchanged.
ALTER TABLE offers ADD COLUMN IF NOT EXISTS listing_id VARCHAR(255);
ALTER TABLE offers ADD COLUMN IF NOT EXISTS condition VARCHAR(10) NOT NULL DEFAULT 'new';
ALTER TABLE offers ADD CONSTRAINT offers_condition_allowed CHECK (condition IN ('new', 'display', 'used'));
-- Missing URLs must not prevent import. Existing URL uniqueness remains for non-null URLs.
ALTER TABLE offers ALTER COLUMN product_url DROP NOT NULL;
ALTER TABLE offers DROP CONSTRAINT IF EXISTS offers_product_url_check;
CREATE UNIQUE INDEX IF NOT EXISTS uq_offers_listing_id ON offers(listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_model ON products(model);
CREATE INDEX IF NOT EXISTS idx_offers_retailer_source_id ON offers(retailer_id, retailer_product_id);

-- Different variants may share the same retailer URL.
-- listing_id is the authoritative listing identifier.
ALTER TABLE offers
    DROP CONSTRAINT IF EXISTS offers_retailer_id_product_url_key;
