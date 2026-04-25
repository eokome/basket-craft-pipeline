WITH order_items AS (
    SELECT * FROM {{ ref('fct_order_items') }}
)

SELECT
    order_id,
    user_id,
    ordered_at,
    COUNT(*)                        AS line_item_count,
    COUNT(DISTINCT product_id)      AS distinct_product_count,
    SUM(is_primary_item)            AS primary_item_count,
    SUM(CASE WHEN is_refunded THEN 1 ELSE 0 END) AS refunded_item_count
FROM order_items
GROUP BY order_id, user_id, ordered_at
