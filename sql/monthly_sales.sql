-- NOTE: groups by product_name (not category) — the real products table has no category column.
-- Columns used: orders.created_at, order_items.price_usd, products.product_name, products.product_id

DROP TABLE IF EXISTS marts.monthly_sales_summary;

CREATE TABLE marts.monthly_sales_summary AS
SELECT
    p.product_name,
    DATE_TRUNC('month', o.created_at)              AS month,
    SUM(oi.price_usd::NUMERIC)                     AS revenue,
    COUNT(DISTINCT o.order_id)                     AS order_count,
    SUM(oi.price_usd::NUMERIC)
        / NULLIF(COUNT(DISTINCT o.order_id), 0)    AS avg_order_value
FROM raw.orders o
JOIN raw.order_items oi ON o.order_id    = oi.order_id
JOIN raw.products    p  ON oi.product_id = p.product_id
GROUP BY p.product_name, DATE_TRUNC('month', o.created_at)
ORDER BY month, p.product_name;
