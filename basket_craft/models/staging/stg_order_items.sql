WITH source AS (
    SELECT * FROM {{ source('raw', 'order_items') }}
),

renamed AS (
    SELECT
        ORDER_ITEM_ID                           AS order_item_id,
        ORDER_ID                                AS order_id,
        PRODUCT_ID                              AS product_id,
        IS_PRIMARY_ITEM                         AS is_primary_item,
        TO_TIMESTAMP(CREATED_AT)                AS created_at
    FROM source
)

SELECT * FROM renamed
