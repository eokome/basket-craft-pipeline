WITH order_items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
),

orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
)

SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    o.user_id,
    CAST(o.created_at AS DATE)      AS ordered_at,
    oi.is_primary_item,
    FALSE                           AS is_refunded
FROM order_items oi
LEFT JOIN orders o ON oi.order_id = o.order_id
