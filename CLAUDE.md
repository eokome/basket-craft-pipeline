# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in MySQL credentials
docker compose up -d   # start Postgres
```

## Running the Pipeline

```bash
python extract_load.py            # extract MySQL → raw.* in local Docker Postgres
TARGET=rds python extract_load.py # extract MySQL → raw.* in AWS RDS Postgres
python transform.py               # transform raw.* → marts.monthly_sales_summary
```

## Tests

```bash
pytest tests/ -v                          # full suite (16 tests)
pytest tests/test_extract_load.py -v     # unit tests for extract_load
pytest tests/test_transform.py -v        # unit tests for transform
pytest tests/test_sql.py -v              # SQL file structure tests
pytest tests/test_extract_load.py::test_copy_table_creates_schema_drops_and_inserts -v  # single test
```

## Architecture

ELT pattern — two independent scripts run in sequence:

1. **`extract_load.py`** — connects to the remote MySQL source (`MYSQL_*` env vars), does a full `SELECT *` of three tables (`orders`, `order_items`, `products`), and writes them into a `raw` schema in local Postgres. Each run drops and recreates the raw tables (full refresh). Column types are inferred from Python types via `infer_pg_type`, with `first_non_null` used to skip NULL values in the first row.

2. **`transform.py`** — reads `sql/monthly_sales.sql` from disk and executes it against Postgres. The SQL builds `marts.monthly_sales_summary` (revenue, order count, avg order value by product and month). The SQL file is kept separate so it can be edited and tested without touching Python.

3. **`sql/monthly_sales.sql`** — the only transformation logic. The `products` table has no `category` column; it groups by `product_name` instead. Uses `price_usd::NUMERIC` for safe decimal arithmetic and `NULLIF` to guard division by zero.

**PostgreSQL schemas:**
- `raw` — exact copies of MySQL source tables, replaced on every run
- `marts` — aggregated dashboard output

**Key design decisions:**
- `get_pg_config()` is duplicated in both scripts (intentional — no shared module)
- `get_pg_config()` in `extract_load.py` checks `os.environ.get("TARGET") == "rds"` to switch between local Docker (`PG_*` vars) and AWS RDS (`RDS_*` vars). `transform.py` only has the local path.
- `load_dotenv()` is called inside `main()` so config functions are importable in tests without a `.env` file
- Both `main()` functions initialize connections to `None` before `try` blocks to avoid `UnboundLocalError` in `finally` when the connection itself fails
- `conftest.py` adds the project root to `sys.path` so pytest can import `extract_load` and `transform` without a package install

## Credential Keys

- MySQL: code reads `MYSQL_DB` (not `MYSQL_DATABASE`)
- Local Postgres: psycopg2 requires `dbname` (not `database`) — key is `PG_DB`
- RDS: key is `RDS_DATABASE` (not `RDS_DB`) — also maps to psycopg2 `dbname`

Tests `test_get_mysql_config_returns_correct_keys` and `test_get_pg_config_returns_correct_keys` enforce these key names.

## Querying the Output

```bash
# Local Docker
docker compose exec postgres psql -U student -d basket_craft \
  -c "SELECT * FROM marts.monthly_sales_summary ORDER BY month, product_name LIMIT 10;"

# AWS RDS (psql must be installed)
PGPASSWORD=<RDS_PASSWORD> psql -h <RDS_HOST> -U student -d basket_craft \
  -c "SELECT * FROM marts.monthly_sales_summary ORDER BY month, product_name LIMIT 10;"
```

---

## dbt Layer (Snowflake)

### Setup

```bash
cd basket_craft
../venv/bin/dbt debug        # confirm Snowflake connection
../venv/bin/dbt run          # build all models
../venv/bin/dbt test         # run data quality tests
../venv/bin/dbt docs generate && ../venv/bin/dbt docs serve  # open lineage docs
```

Profile lives at `~/.dbt/profiles.yml` (not committed). Target: `basket_craft` database, `ANALYTICS` schema, role `basket_craft_loader`.

### Architecture

Three-layer ELT in dbt on top of Snowflake:

1. **Staging** (`models/staging/` → views) — one model per raw source table. Renames columns to lowercase, casts `CREATED_AT` from Unix NUMBER to TIMESTAMP via `TO_TIMESTAMP()`. No JOINs, WHERE, or aggregations — boring on purpose.

2. **Marts** (`models/marts/` → tables) — star schema designed for Maya (head of merchandising).

3. **Sources** declared in `models/staging/sources.yml` — points dbt at `basket_craft.raw.{ORDERS,ORDER_ITEMS,PRODUCTS}`.

### Star Schema

| Model | Grain | Notes |
|---|---|---|
| `fct_order_items` | one row per line item | PK: `order_item_id`; measures: `is_primary_item`, `is_refunded` |
| `fct_orders` | one row per order | Rolls up from `fct_order_items` via `{{ ref() }}`; measures: `line_item_count`, `distinct_product_count` |
| `dim_product` | product | `product_id`, `product_name`, `description` |
| `dim_customer` | user | `user_id`, `first_order_at`, `customer_segment` (new/returning) |
| `dim_order` | order | `order_id`, `user_id`, `website_session_id`, `created_at` |
| `dim_date` | calendar day | Date spine 2023–2025; `month_label`, `quarter_num`, `year` |

### Key Design Decisions

- `fct_orders` reads from `fct_order_items`, never from staging — keeps aggregations consistent with the atomic fact.
- `CREATED_AT` in raw Snowflake tables is a NUMBER (Unix timestamp), not a TIMESTAMP — `TO_TIMESTAMP()` is applied once in staging.
- Raw tables are UPPERCASE in Snowflake (`ORDERS`, not `orders`) — staging references them without quotes via `source('raw', 'orders')`.
- `ANALYTICS` schema was pre-created by ACCOUNTADMIN and granted to `basket_craft_loader`; dbt does not need `CREATE SCHEMA` on the database.
- SQL convention: uppercase keywords, lowercase identifiers.

### Data Quality Tests

`models/marts/schema.yml` enforces `unique` + `not_null` on:
- `fct_order_items.order_item_id`
- `fct_orders.order_id`

### What's Next

- Add `not_null` tests on foreign keys (`product_id`, `user_id`) in `fct_order_items`
- Add a `customers` source table to Snowflake raw and build a proper `dim_customer` (currently derived from orders only)
- Add `price_usd` once a pricing table or column appears in the source data
- Wire `fct_order_items.ordered_at` to `dim_date.date_day` as a formal FK relationship in schema.yml
