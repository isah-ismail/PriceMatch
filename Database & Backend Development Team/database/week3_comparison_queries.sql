-- Set :product_id in psql, e.g. \set product_id 123
SELECT p.product_id, p.name AS canonical_product, r.name AS retailer,
       o.listing_id, o.retailer_product_id, o.current_price, o.currency,
       o.in_stock, o.product_url, o.last_updated
FROM products p
JOIN offers o ON o.product_id = p.product_id
JOIN retailers r ON r.retailer_id = o.retailer_id
WHERE p.product_id = :product_id
  AND o.condition = 'new'
  AND o.in_stock IS NOT FALSE
ORDER BY o.currency, o.current_price ASC, o.offer_id;

-- Integrity summary: orphaned references should be zero (FKs also enforce this).
SELECT (SELECT COUNT(*) FROM products) AS products,
       (SELECT COUNT(*) FROM offers) AS offers,
       (SELECT COUNT(*) FROM price_history) AS price_observations,
       (SELECT COUNT(*) FROM offers WHERE listing_id IS NULL) AS legacy_offers_without_listing_id;
