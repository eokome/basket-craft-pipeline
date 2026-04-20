# Basket Craft Pipeline

An ELT pipeline that extracts sales data from a MySQL source database, loads it into PostgreSQL (local Docker or AWS RDS), and transforms it into a monthly sales summary dashboard table. A separate loader script copies the raw RDS tables into Snowflake.

**Output:** `marts.monthly_sales_summary` — revenue, order count, and average order value by product and month.

**AWS RDS:** Raw Basket Craft data (`raw.orders`, `raw.order_items`, `raw.products`) is available on a hosted PostgreSQL 17 instance at `basket-craft-db.cg7eky00i67b.us-east-1.rds.amazonaws.com`.

---

## How It Works

```
MySQL (remote)          PostgreSQL (Docker or RDS)
─────────────           ──────────────────────────────────────────────────────
orders          ──►     raw.orders
order_items     ──►     raw.order_items    ──►   marts.monthly_sales_summary
products        ──►     raw.products
         extract_load.py              transform.py

                        PostgreSQL (RDS)           Snowflake
                        ────────────────           ──────────────────────────
                        raw.orders         ──►     BASKET_CRAFT.RAW.orders
                        raw.order_items    ──►     BASKET_CRAFT.RAW.order_items
                        raw.products       ──►     BASKET_CRAFT.RAW.products
                                  rds_to_snowflake.py
```

1. `extract_load.py` — copies three MySQL tables into a `raw` schema in Postgres (full refresh each run). Set `TARGET=rds` to load into AWS RDS instead of local Docker.
2. `transform.py` — runs `sql/monthly_sales.sql` to aggregate the raw tables into `marts.monthly_sales_summary`.
3. `rds_to_snowflake.py` — reads the three raw tables from AWS RDS and loads them (full refresh) into Snowflake's `BASKET_CRAFT.RAW` schema.

---

## Setup

**Prerequisites:** Python 3, Docker Desktop

### 1. Clone and install dependencies

```bash
git clone https://github.com/eokome/basket-craft-pipeline.git
cd basket-craft-pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in the MySQL source credentials:

```
MYSQL_HOST=<host>
MYSQL_PORT=3306
MYSQL_USER=<user>
MYSQL_PASSWORD=<password>
MYSQL_DB=<database>
```

The local Postgres values are pre-filled to match the Docker container. To target AWS RDS instead, fill in the `RDS_*` section of `.env` and run with `TARGET=rds`.

To load into Snowflake, fill in the `SF_*` section of `.env`:

```
SF_ACCOUNT=<account-identifier>   # e.g. xy12345.us-east-1
SF_USER=<user>
SF_PASSWORD=<password>
SF_DATABASE=BASKET_CRAFT
SF_SCHEMA=RAW
SF_WAREHOUSE=<warehouse>
SF_ROLE=<role>                    # optional — leave blank for default role
```

### 3. Start the database

```bash
docker compose up -d
```

Verify it's running:

```bash
docker compose exec postgres psql -U student -d basket_craft -c "SELECT version();"
```

---

## Running the Pipeline

### MySQL → Postgres → mart

```bash
# Load into local Docker Postgres (default)
python extract_load.py
python transform.py

# Load into AWS RDS Postgres
TARGET=rds python extract_load.py
python transform.py
```

Expected output:

```
[extract_load] raw.orders       → 32,313 rows loaded
[extract_load] raw.order_items  → 40,025 rows loaded
[extract_load] raw.products     → 4 rows loaded
[transform]    marts.monthly_sales_summary → 94 rows
```

### RDS → Snowflake

Requires the `RDS_*` and `SF_*` vars to be set in `.env`.

```bash
python rds_to_snowflake.py
```

Expected output:

```
[rds_to_snowflake] RAW.orders      → 32,313 rows loaded
[rds_to_snowflake] RAW.order_items → 40,025 rows loaded
[rds_to_snowflake] RAW.products    → 4 rows loaded
```

All scripts are safe to re-run — they fully replace the output tables each time.

---

## Querying the Results

```bash
docker compose exec postgres psql -U student -d basket_craft
```

```sql
-- Monthly revenue by product
SELECT product_name, TO_CHAR(month, 'YYYY-MM') AS month, revenue, order_count, avg_order_value
FROM marts.monthly_sales_summary
ORDER BY month, product_name;

-- Top products by total revenue
SELECT product_name, ROUND(SUM(revenue)::NUMERIC, 2) AS total_revenue
FROM marts.monthly_sales_summary
GROUP BY product_name
ORDER BY total_revenue DESC;

-- Busiest months by order volume
SELECT TO_CHAR(month, 'YYYY-MM') AS month, SUM(order_count) AS total_orders
FROM marts.monthly_sales_summary
GROUP BY month
ORDER BY total_orders DESC;
```

---

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

20 unit tests covering config loading, SQL structure, and core pipeline functions across all three scripts. No live database required.

---

## Project Structure

```
basket-craft-pipeline/
├── extract_load.py         # Step 1: MySQL → raw.* in Postgres (Docker or RDS)
├── transform.py            # Step 2: raw.* → marts.monthly_sales_summary
├── rds_to_snowflake.py     # Step 3: RDS raw.* → Snowflake BASKET_CRAFT.RAW
├── sql/
│   └── monthly_sales.sql   # Aggregation query
├── tests/                  # Unit tests (pytest, 20 tests)
├── docker-compose.yml      # Postgres 16 container
├── requirements.txt        # Python dependencies
└── .env.example            # Credential template (MySQL, Postgres, RDS, Snowflake)
```
