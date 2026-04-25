WITH source AS (
    SELECT * FROM {{ source('raw', 'orders') }}
),

renamed AS (
    SELECT
        ORDER_ID                                AS order_id,
        USER_ID                                 AS user_id,
        WEBSITE_SESSION_ID                      AS website_session_id,
        PRIMARY_PRODUCT_ID                      AS primary_product_id,
        TO_TIMESTAMP(CREATED_AT)                AS created_at
    FROM source
)

SELECT * FROM renamed
