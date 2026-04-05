# Basket Craft Pipeline — Design Spec

**Date:** 2026-04-05
**Project:** basket-craft-pipeline
**Goal:** Monthly sales dashboard with revenue, order counts, and average order value by product category and month.

---

## 1. Architecture

ELT pattern: Extract raw tables from MySQL → Load into PostgreSQL (Docker) → Transform in-place with SQL.

Two PostgreSQL schemas keep raw data separate from dashboard-ready output:

- `raw` — exact copies of MySQL source tables, replaced on each run
- `marts` — aggregated, dashboard-ready output

```
┌─────────────────────────────────────────────────────────────┐
│                      SOURCE (MySQL)                          │
│                                                             │
│   orders ──┐                                                │
│            ├──► extract_load.py ──► PyMySQL connection      │
│ order_items┤                                                │
│            │                                                │
│  products ─┘                                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          │  (full table copy, 3 raw tables)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               DESTINATION (PostgreSQL in Docker)             │
│                                                             │
│   raw.orders        ◄── landed by extract_load.py          │
│   raw.order_items   ◄── landed by extract_load.py          │
│   raw.products      ◄── landed by extract_load.py          │
│                                                             │
│                          │                                  │
│                          │  transform.py runs SQL           │
│                          ▼                                  │
│   marts.monthly_sales_summary  ◄── aggregated output        │
│   (category, month, revenue,                                │
│    order_count, avg_order_value)                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Dashboard / SQL queries
```

---

## 2. Components

```
basket-craft-pipeline/
├── docker-compose.yml        # PostgreSQL container definition
├── .env                      # MySQL + Postgres credentials (gitignored)
├── extract_load.py           # Connects to MySQL, writes raw.* tables to Postgres
├── transform.py              # Runs SQL to build marts.monthly_sales_summary
├── sql/
│   └── monthly_sales.sql     # The aggregation query (imported by transform.py)
└── requirements.txt          # PyMySQL, psycopg2-binary, python-dotenv
```

| File | Responsibility |
|---|---|
| `docker-compose.yml` | Spins up Postgres on port 5432 with a named volume so data persists between container restarts |
| `.env` | Holds MySQL + Postgres credentials — never committed to git. Expected variables: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB` |
| `extract_load.py` | Opens MySQL connection → `SELECT *` from each table → writes to `raw` schema in Postgres, replacing tables each run |
| `transform.py` | Connects to Postgres → reads `sql/monthly_sales.sql` → executes it to create/replace `marts.monthly_sales_summary` |
| `sql/monthly_sales.sql` | The JOIN + GROUP BY query — kept in its own file so it is readable and editable without touching Python |

---

## 3. Data Flow

### Step 1 — Extract & Load (`extract_load.py`)

```
For each table in [orders, order_items, products]:
  1. Open MySQL connection (credentials from .env)
  2. SELECT * FROM <table>
  3. DROP TABLE IF EXISTS raw.<table> in Postgres
  4. CREATE TABLE raw.<table> + INSERT all rows
  5. Print row count confirmation
  6. Close connections
```

### Step 2 — Transform (`transform.py`)

```
1. Open Postgres connection
2. Read sql/monthly_sales.sql from disk
3. Execute: CREATE TABLE marts.monthly_sales_summary AS ...
4. Print row count confirmation
5. Close connection
```

### Aggregation Query (`sql/monthly_sales.sql`)

```sql
DROP TABLE IF EXISTS marts.monthly_sales_summary;

CREATE TABLE marts.monthly_sales_summary AS
SELECT
    p.category,
    DATE_TRUNC('month', o.order_date)  AS month,
    SUM(oi.line_total)                 AS revenue,
    COUNT(DISTINCT o.order_id)         AS order_count,
    SUM(oi.line_total)
        / NULLIF(COUNT(DISTINCT o.order_id), 0) AS avg_order_value
FROM raw.orders o
JOIN raw.order_items oi ON o.order_id   = oi.order_id
JOIN raw.products    p  ON oi.product_id = p.product_id
GROUP BY p.category, DATE_TRUNC('month', o.order_date)
ORDER BY month, p.category;
```

> **Note:** Column names (`line_total`, `product_id`, `order_date`) may need adjusting once the real MySQL schema is confirmed. The query structure stays the same.

---

## 4. Error Handling

Three rules — kept minimal for a manual, single-user script:

1. **Fail loud, fail early** — connection failures raise immediately with a clear message.
2. **All-or-nothing per table** — if one table fails mid-copy, the script exits. No partial loads.
3. **Credentials from `.env` only** — `python-dotenv` loads the `.env` file. Missing variables raise `KeyError` before any connection is attempted.

No retry logic, no file logging, no alerting. Terminal output is sufficient for this use case.

---

## 5. Verification

Each script prints a row count after each operation:

```
[extract_load] raw.orders        → 4,821 rows loaded
[extract_load] raw.order_items   → 12,304 rows loaded
[extract_load] raw.products      → 87 rows loaded

[transform]    marts.monthly_sales_summary → 36 rows
```

Manual spot-check after both scripts complete:

```sql
SELECT * FROM marts.monthly_sales_summary ORDER BY month, category LIMIT 10;
```

---

## 6. Run Order

```bash
# 1. Start Postgres
docker compose up -d

# 2. Extract from MySQL and load raw tables into Postgres
python extract_load.py

# 3. Transform raw tables into dashboard summary
python transform.py
```

---

## 7. Out of Scope

- Incremental/delta extraction (full replace each run)
- Scheduling or automation
- Dashboard front-end (output is a queryable Postgres table)
- dbt or other transformation frameworks
