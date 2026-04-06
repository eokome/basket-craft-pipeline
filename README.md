# Basket Craft Pipeline

An ELT pipeline that extracts sales data from a MySQL source database, loads it into a local PostgreSQL instance (Docker), and transforms it into a monthly sales summary dashboard table.

**Output:** `marts.monthly_sales_summary` — revenue, order count, and average order value by product and month.

---

## How It Works

```
MySQL (remote)          PostgreSQL (Docker)
─────────────           ─────────────────────────────────────
orders          ──►     raw.orders
order_items     ──►     raw.order_items          ──►   marts.monthly_sales_summary
products        ──►     raw.products
         extract_load.py              transform.py
```

1. `extract_load.py` — copies three MySQL tables into a `raw` schema in Postgres (full refresh each run)
2. `transform.py` — runs `sql/monthly_sales.sql` to aggregate the raw tables into `marts.monthly_sales_summary`

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

The Postgres values are pre-filled to match the Docker container — leave them as-is unless you change `docker-compose.yml`.

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

Run the two scripts in order:

```bash
python extract_load.py
python transform.py
```

Expected output:

```
[extract_load] raw.orders       → 32,313 rows loaded
[extract_load] raw.order_items  → 40,025 rows loaded
[extract_load] raw.products     → 4 rows loaded
[transform]    marts.monthly_sales_summary → 94 rows
```

Both scripts are safe to re-run — they fully replace the output tables each time.

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

15 unit tests covering config loading, type inference, SQL structure, and core pipeline functions. No live database required.

---

## Project Structure

```
basket-craft-pipeline/
├── extract_load.py       # Step 1: MySQL → raw.* in Postgres
├── transform.py          # Step 2: raw.* → marts.monthly_sales_summary
├── sql/
│   └── monthly_sales.sql # Aggregation query
├── tests/                # Unit tests (pytest)
├── docker-compose.yml    # Postgres 16 container
├── requirements.txt      # Python dependencies
└── .env.example          # Credential template
```
