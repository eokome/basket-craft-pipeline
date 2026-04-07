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
