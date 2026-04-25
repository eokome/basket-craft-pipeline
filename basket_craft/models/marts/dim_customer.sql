WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

first_order AS (
    SELECT
        user_id,
        MIN(created_at) AS first_order_at
    FROM orders
    GROUP BY user_id
),

all_users AS (
    SELECT DISTINCT user_id FROM orders
)

SELECT
    u.user_id,
    f.first_order_at,
    CASE
        WHEN DATEDIFF('day', f.first_order_at, CURRENT_DATE()) <= 30
        THEN 'new'
        ELSE 'returning'
    END                             AS customer_segment
FROM all_users u
LEFT JOIN first_order f ON u.user_id = f.user_id
