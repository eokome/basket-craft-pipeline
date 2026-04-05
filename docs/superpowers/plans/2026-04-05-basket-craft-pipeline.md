# Basket Craft Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-script ELT pipeline that copies three MySQL tables into a local PostgreSQL (Docker) `raw` schema, then runs a SQL aggregation to produce `marts.monthly_sales_summary` (revenue, order count, and AOV by category and month).

**Architecture:** `extract_load.py` pulls full tables from MySQL with PyMySQL and writes them into PostgreSQL with psycopg2. `transform.py` reads `sql/monthly_sales.sql` from disk and executes it against PostgreSQL to build the summary table. No shared state between the two scripts — run them in sequence manually.

**Tech Stack:** Python 3, PyMySQL, psycopg2-binary, python-dotenv, pytest, Docker (postgres:16)

---

## File Map

| Path | Action | Responsibility |
|---|---|---|
| `docker-compose.yml` | Create | Postgres 16 container on port 5432 with named volume |
| `.env.example` | Create | Documents required env vars (safe to commit) |
| `.env` | Create (do not commit) | Real credentials for local use |
| `requirements.txt` | Create | All Python dependencies including pytest |
| `sql/monthly_sales.sql` | Create | JOIN + GROUP BY aggregation query |
| `extract_load.py` | Create | Config loaders, type inference, table copy, main() |
| `transform.py` | Create | Config loader, SQL runner, main() |
| `tests/test_sql.py` | Create | SQL file structure tests |
| `tests/test_extract_load.py` | Create | Unit tests for config and type inference |
| `tests/test_transform.py` | Create | Unit tests for config and SQL execution wiring |

---

## Task 1: Scaffold — Docker, dependencies, credentials

**Files:**
- Create: `docker-compose.yml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.env` (do not commit — already gitignored)

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: student
      POSTGRES_PASSWORD: student123
      POSTGRES_DB: basket_craft
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

- [ ] **Step 2: Write `requirements.txt`**

```
PyMySQL==1.1.1
psycopg2-binary==2.9.9
python-dotenv==1.0.1
pytest==8.3.5
```

- [ ] **Step 3: Write `.env.example`**

```
# MySQL source — fill in values from professor's credentials
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DB=

# PostgreSQL destination — matches docker-compose.yml defaults
PG_HOST=localhost
PG_PORT=5432
PG_USER=student
PG_PASSWORD=student123
PG_DB=basket_craft
```

- [ ] **Step 4: Create `.env` with real credentials**

Copy `.env.example` to `.env` and fill in the MySQL values from the professor's credentials. The Postgres values match the docker-compose defaults above.

```bash
cp .env.example .env
# Edit .env and fill in MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
```

- [ ] **Step 5: Create and activate virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: `Successfully installed PyMySQL psycopg2-binary python-dotenv pytest` (and their deps).

- [ ] **Step 6: Start the Postgres container**

```bash
docker compose up -d
```

Expected output:
```
✔ Container basket-craft-pipeline-postgres-1  Started
```

- [ ] **Step 7: Verify Postgres is reachable**

```bash
docker compose exec postgres psql -U student -d basket_craft -c "SELECT version();"
```

Expected: one row showing `PostgreSQL 16.x ...`.

- [ ] **Step 8: Verify `.env` is gitignored**

```bash
git status
```

Expected: `.env` does not appear in untracked files. If it does, add it:

```bash
echo ".env" >> .gitignore
```

- [ ] **Step 9: Commit scaffold**

```bash
git add docker-compose.yml requirements.txt .env.example .gitignore
git commit -m "feat: add project scaffold — docker, deps, env template"
```

---

## Task 2: SQL aggregation query

**Files:**
- Create: `sql/monthly_sales.sql`
- Create: `tests/test_sql.py`

- [ ] **Step 1: Create `tests/test_sql.py` with failing tests**

```python
import os

SQL_PATH = os.path.join(os.path.dirname(__file__), "..", "sql", "monthly_sales.sql")


def test_sql_file_exists():
    assert os.path.isfile(SQL_PATH), f"Expected SQL file at {SQL_PATH}"


def test_sql_file_has_required_clauses():
    with open(SQL_PATH) as f:
        sql = f.read().upper()
    assert "SELECT" in sql
    assert "GROUP BY" in sql
    assert "DATE_TRUNC" in sql
    assert "SUM" in sql
    assert "COUNT" in sql
    assert "NULLIF" in sql
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_sql.py -v
```

Expected: both tests FAIL with `AssertionError` or `FileNotFoundError` — the SQL file doesn't exist yet.

- [ ] **Step 3: Create `sql/` directory and write `sql/monthly_sales.sql`**

```bash
mkdir sql
```

```sql
DROP TABLE IF EXISTS marts.monthly_sales_summary;

CREATE TABLE marts.monthly_sales_summary AS
SELECT
    p.category,
    DATE_TRUNC('month', o.order_date)           AS month,
    SUM(oi.line_total)                          AS revenue,
    COUNT(DISTINCT o.order_id)                  AS order_count,
    SUM(oi.line_total)
        / NULLIF(COUNT(DISTINCT o.order_id), 0) AS avg_order_value
FROM raw.orders o
JOIN raw.order_items oi ON o.order_id    = oi.order_id
JOIN raw.products    p  ON oi.product_id = p.product_id
GROUP BY p.category, DATE_TRUNC('month', o.order_date)
ORDER BY month, p.category;
```

> **Note:** If the real MySQL schema uses different column names than `line_total`, `product_id`, or `order_date`, update them here before running `transform.py`. The query structure stays the same.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_sql.py -v
```

Expected:
```
tests/test_sql.py::test_sql_file_exists PASSED
tests/test_sql.py::test_sql_file_has_required_clauses PASSED
```

- [ ] **Step 5: Commit**

```bash
git add sql/monthly_sales.sql tests/test_sql.py
git commit -m "feat: add SQL aggregation query and tests"
```

---

## Task 3: `extract_load.py` — config and type inference

**Files:**
- Create: `extract_load.py` (config + type inference only — no DB calls yet)
- Create: `tests/test_extract_load.py`

- [ ] **Step 1: Write `tests/test_extract_load.py` with failing tests**

```python
import os
import pytest
from unittest.mock import patch
from datetime import date, datetime
from decimal import Decimal


def test_get_mysql_config_raises_on_missing_host():
    with patch.dict(os.environ, {}, clear=True):
        from extract_load import get_mysql_config
        with pytest.raises(KeyError):
            get_mysql_config()


def test_get_pg_config_raises_on_missing_host():
    with patch.dict(os.environ, {}, clear=True):
        from extract_load import get_pg_config
        with pytest.raises(KeyError):
            get_pg_config()


def test_infer_pg_type_datetime():
    from extract_load import infer_pg_type
    assert infer_pg_type(datetime(2024, 1, 1)) == "TIMESTAMP"


def test_infer_pg_type_date():
    from extract_load import infer_pg_type
    assert infer_pg_type(date(2024, 1, 1)) == "DATE"


def test_infer_pg_type_int():
    from extract_load import infer_pg_type
    assert infer_pg_type(42) == "BIGINT"


def test_infer_pg_type_float():
    from extract_load import infer_pg_type
    assert infer_pg_type(3.14) == "DOUBLE PRECISION"


def test_infer_pg_type_decimal():
    from extract_load import infer_pg_type
    assert infer_pg_type(Decimal("9.99")) == "NUMERIC"


def test_infer_pg_type_string_fallback():
    from extract_load import infer_pg_type
    assert infer_pg_type("hello") == "TEXT"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_extract_load.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError` — `extract_load.py` doesn't exist yet.

- [ ] **Step 3: Write `extract_load.py` with config functions and type inference**

```python
import os
import decimal
from datetime import date, datetime


def get_mysql_config():
    return {
        "host":     os.environ["MYSQL_HOST"],
        "port":     int(os.environ.get("MYSQL_PORT", "3306")),
        "user":     os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.environ["MYSQL_DB"],
    }


def get_pg_config():
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }


def infer_pg_type(value):
    """Map a Python value to a PostgreSQL column type string."""
    if isinstance(value, datetime):        return "TIMESTAMP"
    if isinstance(value, date):            return "DATE"
    if isinstance(value, int):             return "BIGINT"
    if isinstance(value, float):           return "DOUBLE PRECISION"
    if isinstance(value, decimal.Decimal): return "NUMERIC"
    return "TEXT"


def copy_table(mysql_conn, pg_conn, table_name):
    pass  # implemented in Task 4


def main():
    pass  # implemented in Task 4


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_extract_load.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add extract_load.py tests/test_extract_load.py
git commit -m "feat: add extract_load config loaders and type inference"
```

---

## Task 4: `extract_load.py` — table copy + end-to-end run

**Files:**
- Modify: `extract_load.py` (fill in `copy_table` and `main`)

- [ ] **Step 1: Replace `copy_table` and `main` in `extract_load.py`**

Replace the two `pass` stubs with this implementation. Keep everything above `copy_table` (the imports and config functions) exactly as written in Task 3:

```python
import os
import decimal
from datetime import date, datetime

import pymysql
import psycopg2
import psycopg2.extras


def get_mysql_config():
    return {
        "host":     os.environ["MYSQL_HOST"],
        "port":     int(os.environ.get("MYSQL_PORT", "3306")),
        "user":     os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.environ["MYSQL_DB"],
    }


def get_pg_config():
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }


def infer_pg_type(value):
    """Map a Python value to a PostgreSQL column type string."""
    if isinstance(value, datetime):        return "TIMESTAMP"
    if isinstance(value, date):            return "DATE"
    if isinstance(value, int):             return "BIGINT"
    if isinstance(value, float):           return "DOUBLE PRECISION"
    if isinstance(value, decimal.Decimal): return "NUMERIC"
    return "TEXT"


def copy_table(mysql_conn, pg_conn, table_name):
    """Copy one MySQL table into the raw schema in PostgreSQL."""
    with mysql_conn.cursor() as mc:
        mc.execute(f"SELECT * FROM {table_name}")
        rows = mc.fetchall()
        col_names = [d[0] for d in mc.description]

    if not rows:
        print(f"[extract_load] raw.{table_name} → 0 rows (empty source)")
        return

    pg_types = [infer_pg_type(rows[0][i]) for i in range(len(col_names))]
    col_defs  = ", ".join(f'"{c}" {t}' for c, t in zip(col_names, pg_types))

    with pg_conn.cursor() as pc:
        pc.execute("CREATE SCHEMA IF NOT EXISTS raw")
        pc.execute(f'DROP TABLE IF EXISTS raw."{table_name}"')
        pc.execute(f'CREATE TABLE raw."{table_name}" ({col_defs})')
        psycopg2.extras.execute_values(
            pc,
            f'INSERT INTO raw."{table_name}" VALUES %s',
            rows,
        )
    pg_conn.commit()
    print(f"[extract_load] raw.{table_name} → {len(rows):,} rows loaded")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    mysql_conn = pymysql.connect(**get_mysql_config())
    pg_conn    = psycopg2.connect(**get_pg_config())

    try:
        for table in ["orders", "order_items", "products"]:
            try:
                copy_table(mysql_conn, pg_conn, table)
            except Exception as e:
                print(f"[extract_load] ERROR copying {table}: {e}")
                raise SystemExit(1)
    finally:
        mysql_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
pytest tests/test_extract_load.py tests/test_sql.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 3: Run `extract_load.py` end-to-end**

```bash
python extract_load.py
```

Expected output (row counts will differ based on actual data):
```
[extract_load] raw.orders       → 4,821 rows loaded
[extract_load] raw.order_items  → 12,304 rows loaded
[extract_load] raw.products     → 87 rows loaded
```

If you see a column name error in the SQL transform later (Task 5), this is the point to check actual column names:

```bash
docker compose exec postgres psql -U student -d basket_craft \
  -c "\d raw.orders"
```

That shows the real column names that landed. Adjust `sql/monthly_sales.sql` if needed.

- [ ] **Step 4: Verify raw tables in Postgres**

```bash
docker compose exec postgres psql -U student -d basket_craft \
  -c "SELECT COUNT(*) FROM raw.orders;"
```

Expected: row count matches what `extract_load.py` printed.

- [ ] **Step 5: Commit**

```bash
git add extract_load.py
git commit -m "feat: implement copy_table and main in extract_load"
```

---

## Task 5: `transform.py` — SQL runner + end-to-end run

**Files:**
- Create: `transform.py`
- Create: `tests/test_transform.py`

- [ ] **Step 1: Write `tests/test_transform.py` with failing tests**

```python
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open


def test_get_pg_config_raises_on_missing_host():
    with patch.dict(os.environ, {}, clear=True):
        from transform import get_pg_config
        with pytest.raises(KeyError):
            get_pg_config()


def test_run_transform_reads_sql_and_executes():
    """run_transform must read the SQL file and pass its contents to execute()."""
    sql_content = "DROP TABLE IF EXISTS marts.monthly_sales_summary; CREATE TABLE marts.monthly_sales_summary AS SELECT 1 AS n;"

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (36,)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("builtins.open", mock_open(read_data=sql_content)):
        from transform import run_transform
        run_transform(mock_conn, "fake/path.sql")

    # The SQL content must have been passed to execute
    calls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any(sql_content in c for c in calls), \
        "Expected run_transform to execute the SQL file contents"

    mock_conn.commit.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_transform.py -v
```

Expected: both tests FAIL with `ModuleNotFoundError` — `transform.py` doesn't exist yet.

- [ ] **Step 3: Write `transform.py`**

```python
import os
import psycopg2


def get_pg_config():
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }


def run_transform(pg_conn, sql_path):
    """Execute the aggregation SQL and print the resulting row count."""
    with open(sql_path) as f:
        sql = f.read()

    with pg_conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS marts")
        cur.execute(sql)
        cur.execute("SELECT COUNT(*) FROM marts.monthly_sales_summary")
        row_count = cur.fetchone()[0]

    pg_conn.commit()
    print(f"[transform]    marts.monthly_sales_summary → {row_count:,} rows")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    sql_path = os.path.join(os.path.dirname(__file__), "sql", "monthly_sales.sql")
    pg_conn  = psycopg2.connect(**get_pg_config())

    try:
        run_transform(pg_conn, sql_path)
    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
pytest tests/ -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Run `transform.py` end-to-end**

```bash
python transform.py
```

Expected output:
```
[transform]    marts.monthly_sales_summary → 36 rows
```

(Row count = number of distinct category + month combinations in the data.)

- [ ] **Step 6: Commit**

```bash
git add transform.py tests/test_transform.py
git commit -m "feat: implement transform.py with SQL runner and tests"
```

---

## Task 6: Final verification and cleanup

- [ ] **Step 1: Run the full pipeline from scratch**

This confirms the scripts work independently and in sequence:

```bash
python extract_load.py && python transform.py
```

Expected: row counts print for all three raw tables, then the summary count.

- [ ] **Step 2: Spot-check the summary table**

```bash
docker compose exec postgres psql -U student -d basket_craft \
  -c "SELECT category, month, revenue, order_count, avg_order_value
      FROM marts.monthly_sales_summary
      ORDER BY month, category
      LIMIT 10;"
```

Expected: rows with recognizable categories, months as `YYYY-MM-01` dates, and numeric values for all three metrics.

- [ ] **Step 3: Run the full test suite one last time**

```bash
pytest tests/ -v
```

Expected: all 12 tests PASS, no warnings.

- [ ] **Step 4: Final commit**

```bash
git add -A
git status   # confirm no .env or venv/ files are staged
git commit -m "feat: complete basket-craft ELT pipeline"
```

---

## Run Order (reference)

```bash
# Start Postgres (once per session)
docker compose up -d

# Step 1 — Extract from MySQL, load raw tables
python extract_load.py

# Step 2 — Transform raw tables into dashboard summary
python transform.py

# Verify
docker compose exec postgres psql -U student -d basket_craft \
  -c "SELECT * FROM marts.monthly_sales_summary ORDER BY month, category LIMIT 10;"
```
