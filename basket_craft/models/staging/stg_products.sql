WITH source AS (
    SELECT * FROM {{ source('raw', 'products') }}
),

renamed AS (
    SELECT
        PRODUCT_ID                              AS product_id,
        PRODUCT_NAME                            AS product_name,
        DESCRIPTION                             AS description
    FROM source
)

SELECT * FROM renamed
