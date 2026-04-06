DROP TABLE IF EXISTS marts.monthly_sales_summary;

CREATE TABLE marts.monthly_sales_summary AS
SELECT
    p.category,
    DATE_TRUNC('month', o.order_date)           AS month,
    SUM(oi.line_total::NUMERIC)                 AS revenue,
    COUNT(DISTINCT o.order_id)                  AS order_count,
    SUM(oi.line_total::NUMERIC)
        / NULLIF(COUNT(DISTINCT o.order_id), 0) AS avg_order_value
FROM raw.orders o
JOIN raw.order_items oi ON o.order_id    = oi.order_id
JOIN raw.products    p  ON oi.product_id = p.product_id
GROUP BY p.category, DATE_TRUNC('month', o.order_date)
ORDER BY month, p.category;
