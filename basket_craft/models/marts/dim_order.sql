WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
)

SELECT
    order_id,
    user_id,
    website_session_id,
    primary_product_id,
    created_at
FROM orders
