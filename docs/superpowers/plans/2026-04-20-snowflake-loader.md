# Snowflake Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `rds_to_snowflake.py` — a standalone script that reads `raw.orders`, `raw.order_items`, and `raw.products` from AWS RDS PostgreSQL and loads them (full refresh) into `BASKET_CRAFT.RAW` in Snowflake using the official Python connector.

**Architecture:** Mirrors `extract_load.py` exactly — `get_rds_config()` and `get_snowflake_config()` read env vars, `copy_table(pg_conn, sf_conn, table_name)` does SELECT from RDS then DROP/CREATE/INSERT in Snowflake, `main()` loops over three tables. No shared module with `extract_load.py` (intentional repo convention).

**Tech Stack:** Python 3, psycopg2-binary (RDS source), snowflake-connector-python (Snowflake destination), python-dotenv, pytest + unittest.mock

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `requirements.txt` | Modify | Add `snowflake-connector-python==3.11.0` |
| `.env.example` | Modify | Add `SF_*` credential keys |
| `rds_to_snowflake.py` | Create | New standalone loader script |
| `tests/test_rds_to_snowflake.py` | Create | Unit tests (10 tests, mock-based) |

---

## Task 1: Add Dependency and Credential Template

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add snowflake connector to requirements.txt**

Open `requirements.txt`. It currently contains:
```
PyMySQL==1.1.1
psycopg2-binary==2.9.11
python-dotenv==1.0.1
pytest==8.3.5
```

Add one line so the file reads:
```
PyMySQL==1.1.1
psycopg2-binary==2.9.11
python-dotenv==1.0.1
pytest==8.3.5
snowflake-connector-python==3.11.0
```

- [ ] **Step 2: Add SF_* vars to .env.example**

Open `.env.example`. Append this block at the end (after the existing RDS block):
```
# Snowflake destination — only needed when running rds_to_snowflake.py
# SF_ACCOUNT=        # account identifier (e.g. xy12345.us-east-1)
# SF_USER=
# SF_PASSWORD=
# SF_DATABASE=BASKET_CRAFT
# SF_SCHEMA=RAW
# SF_WAREHOUSE=
# SF_ROLE=           # optional — leave blank to use account default
```

- [ ] **Step 3: Install the new dependency**

```bash
pip install snowflake-connector-python==3.11.0
```

Expected: installs without error. `pip show snowflake-connector-python` confirms version 3.11.0.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: add snowflake-connector-python dependency and SF credential template"
```

---

## Task 2: Config Functions (TDD)

**Files:**
- Create: `tests/test_rds_to_snowflake.py`
- Create: `rds_to_snowflake.py` (skeleton only — add functions incrementally)

- [ ] **Step 1: Create the test file with config tests**

Create `tests/test_rds_to_snowflake.py`:

```python
import os
import decimal
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime


def test_get_rds_config_returns_correct_keys():
    env = {
        "RDS_HOST":     "rds.example.com",
        "RDS_PORT":     "5432",
        "RDS_USER":     "student",
        "RDS_PASSWORD": "secret",
        "RDS_DATABASE": "basket_craft",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_rds_config
        cfg = get_rds_config()
    assert cfg["host"]     == "rds.example.com"
    assert cfg["port"]     == 5432           # must be int, not string
    assert cfg["user"]     == "student"
    assert cfg["password"] == "secret"
    assert cfg["dbname"]   == "basket_craft" # psycopg2 requires "dbname", not "database"


def test_get_snowflake_config_returns_correct_keys():
    env = {
        "SF_ACCOUNT":   "xy12345.us-east-1",
        "SF_USER":      "student",
        "SF_PASSWORD":  "secret",
        "SF_DATABASE":  "BASKET_CRAFT",
        "SF_SCHEMA":    "RAW",
        "SF_WAREHOUSE": "COMPUTE_WH",
        "SF_ROLE":      "SYSADMIN",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_snowflake_config
        cfg = get_snowflake_config()
    assert cfg["account"]   == "xy12345.us-east-1"
    assert cfg["user"]      == "student"
    assert cfg["password"]  == "secret"
    assert cfg["database"]  == "BASKET_CRAFT"
    assert cfg["schema"]    == "RAW"
    assert cfg["warehouse"] == "COMPUTE_WH"
    assert cfg["role"]      == "SYSADMIN"


def test_get_snowflake_config_omits_role_when_unset():
    env = {
        "SF_ACCOUNT":   "xy12345.us-east-1",
        "SF_USER":      "student",
        "SF_PASSWORD":  "secret",
        "SF_DATABASE":  "BASKET_CRAFT",
        "SF_SCHEMA":    "RAW",
        "SF_WAREHOUSE": "COMPUTE_WH",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_snowflake_config
        cfg = get_snowflake_config()
    assert "role" not in cfg
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_rds_to_snowflake.py -v
```

Expected: 3 errors — `ModuleNotFoundError: No module named 'rds_to_snowflake'`

- [ ] **Step 3: Create rds_to_snowflake.py with config functions**

Create `rds_to_snowflake.py`:

```python
import os
import decimal
from datetime import date, datetime

import psycopg2
import psycopg2.extras
import snowflake.connector


def get_rds_config():
    return {
        "host":     os.environ["RDS_HOST"],
        "port":     int(os.environ.get("RDS_PORT", "5432")),
        "user":     os.environ["RDS_USER"],
        "password": os.environ["RDS_PASSWORD"],
        "dbname":   os.environ["RDS_DATABASE"],
    }


def get_snowflake_config():
    config = {
        "account":   os.environ["SF_ACCOUNT"],
        "user":      os.environ["SF_USER"],
        "password":  os.environ["SF_PASSWORD"],
        "database":  os.environ["SF_DATABASE"],
        "schema":    os.environ["SF_SCHEMA"],
        "warehouse": os.environ["SF_WAREHOUSE"],
    }
    role = os.environ.get("SF_ROLE")
    if role:
        config["role"] = role
    return config
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_rds_to_snowflake.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add rds_to_snowflake.py tests/test_rds_to_snowflake.py
git commit -m "feat: add config functions for RDS and Snowflake with tests"
```

---

## Task 3: Type Inference (TDD)

**Files:**
- Modify: `tests/test_rds_to_snowflake.py` (append tests)
- Modify: `rds_to_snowflake.py` (append functions)

- [ ] **Step 1: Append type inference tests to test file**

Add these tests to the bottom of `tests/test_rds_to_snowflake.py`:

```python
def test_infer_sf_type_int():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type(42) == "NUMBER"


def test_infer_sf_type_float():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type(3.14) == "FLOAT"


def test_infer_sf_type_decimal():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type(decimal.Decimal("9.99")) == "NUMBER"


def test_infer_sf_type_date():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type(date(2024, 1, 1)) == "DATE"


def test_infer_sf_type_datetime():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type(datetime(2024, 1, 1, 12, 0)) == "TIMESTAMP"


def test_infer_sf_type_str_fallback():
    from rds_to_snowflake import infer_sf_type
    assert infer_sf_type("hello") == "TEXT"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_rds_to_snowflake.py -v -k "infer"
```

Expected: 6 errors — `ImportError: cannot import name 'infer_sf_type'`

- [ ] **Step 3: Add infer_sf_type and first_non_null to rds_to_snowflake.py**

Append these two functions to `rds_to_snowflake.py` (after `get_snowflake_config`):

```python
def infer_sf_type(value):
    """Map a Python value to a Snowflake column type string."""
    if isinstance(value, datetime):        return "TIMESTAMP"
    if isinstance(value, date):            return "DATE"
    if isinstance(value, int):             return "NUMBER"
    if isinstance(value, float):           return "FLOAT"
    if isinstance(value, decimal.Decimal): return "NUMBER"
    return "TEXT"


def first_non_null(rows, col_index):
    """Return the first non-null value for a given column, or None."""
    for row in rows:
        if row[col_index] is not None:
            return row[col_index]
    return None
```

**Important:** `datetime` must be checked before `date` — `datetime` is a subclass of `date`, so reversing the order would misclassify timestamps as dates.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_rds_to_snowflake.py -v -k "infer"
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add rds_to_snowflake.py tests/test_rds_to_snowflake.py
git commit -m "feat: add infer_sf_type and first_non_null with tests"
```

---

## Task 4: copy_table (TDD)

**Files:**
- Modify: `tests/test_rds_to_snowflake.py` (append test)
- Modify: `rds_to_snowflake.py` (append function)

- [ ] **Step 1: Append copy_table test to test file**

Add this test to the bottom of `tests/test_rds_to_snowflake.py`:

```python
def test_copy_table_creates_schema_drops_and_inserts():
    """copy_table must: create RAW schema, drop existing table, create new table, bulk insert, commit."""
    # --- RDS (psycopg2) mock ---
    mock_pg_cur = MagicMock()
    mock_pg_cur.description = [("product_id",), ("product_name",), ("price_usd",)]
    mock_pg_cur.fetchall.return_value = [
        (1, "Gift Basket", 29.99),
        (2, "Fruit Basket", 19.99),
    ]
    mock_pg_conn = MagicMock()
    mock_pg_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_pg_cur)
    mock_pg_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # --- Snowflake mock ---
    mock_sf_cur = MagicMock()
    mock_sf_conn = MagicMock()
    mock_sf_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_sf_cur)
    mock_sf_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    from rds_to_snowflake import copy_table
    copy_table(mock_pg_conn, mock_sf_conn, "products")

    sf_calls = [str(c) for c in mock_sf_cur.execute.call_args_list]
    assert any("CREATE SCHEMA IF NOT EXISTS" in c for c in sf_calls)
    assert any("DROP TABLE IF EXISTS" in c for c in sf_calls)
    assert any("CREATE TABLE" in c for c in sf_calls)
    mock_sf_cur.executemany.assert_called_once()
    mock_sf_conn.commit.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rds_to_snowflake.py::test_copy_table_creates_schema_drops_and_inserts -v
```

Expected: FAIL — `ImportError: cannot import name 'copy_table'`

- [ ] **Step 3: Add copy_table to rds_to_snowflake.py**

Append this function to `rds_to_snowflake.py` (after `first_non_null`):

```python
def copy_table(pg_conn, sf_conn, table_name):
    """Copy one RDS raw table into the RAW schema in Snowflake."""
    with pg_conn.cursor() as pc:
        pc.execute(f'SELECT * FROM raw."{table_name}"')
        rows = pc.fetchall()
        col_names = [d[0] for d in pc.description]

    if not rows:
        print(f"[rds_to_snowflake] RAW.{table_name} → 0 rows (empty source)")
        return

    sf_types   = [infer_sf_type(first_non_null(rows, i)) for i in range(len(col_names))]
    col_defs   = ", ".join(f'"{c}" {t}' for c, t in zip(col_names, sf_types))
    placeholders = ", ".join(["%s"] * len(col_names))

    with sf_conn.cursor() as sc:
        sc.execute('CREATE SCHEMA IF NOT EXISTS "RAW"')
        sc.execute(f'DROP TABLE IF EXISTS "RAW"."{table_name}"')
        sc.execute(f'CREATE TABLE "RAW"."{table_name}" ({col_defs})')
        sc.executemany(
            f'INSERT INTO "RAW"."{table_name}" VALUES ({placeholders})',
            rows,
        )
    sf_conn.commit()
    print(f"[rds_to_snowflake] RAW.{table_name} → {len(rows):,} rows loaded")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rds_to_snowflake.py::test_copy_table_creates_schema_drops_and_inserts -v
```

Expected: PASSED

- [ ] **Step 5: Run all new tests together**

```bash
pytest tests/test_rds_to_snowflake.py -v
```

Expected: 10 PASSED

- [ ] **Step 6: Commit**

```bash
git add rds_to_snowflake.py tests/test_rds_to_snowflake.py
git commit -m "feat: add copy_table for RDS → Snowflake full refresh with test"
```

---

## Task 5: main() and Final Wiring

**Files:**
- Modify: `rds_to_snowflake.py` (append main)

- [ ] **Step 1: Add main() to rds_to_snowflake.py**

Append this to the bottom of `rds_to_snowflake.py`:

```python
def main():
    from dotenv import load_dotenv
    load_dotenv()

    pg_conn = None
    sf_conn = None
    try:
        pg_conn = psycopg2.connect(**get_rds_config())
        sf_conn = snowflake.connector.connect(**get_snowflake_config())
        for table in ["orders", "order_items", "products"]:
            try:
                copy_table(pg_conn, sf_conn, table)
            except Exception as e:
                print(f"[rds_to_snowflake] ERROR copying {table}: {e}")
                raise SystemExit(1)
    finally:
        if pg_conn is not None:
            pg_conn.close()
        if sf_conn is not None:
            sf_conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite (all 16 original + 10 new)**

```bash
pytest tests/ -v
```

Expected: 26 PASSED, 0 failed

- [ ] **Step 3: Fill in your actual SF_* credentials in .env**

Open `.env` and uncomment/fill in the Snowflake block:
```
SF_ACCOUNT=<your-account-identifier>
SF_USER=<your-username>
SF_PASSWORD=<your-password>
SF_DATABASE=BASKET_CRAFT
SF_SCHEMA=RAW
SF_WAREHOUSE=<your-warehouse>
SF_ROLE=<your-role-or-leave-blank>
```

- [ ] **Step 4: Do a live test run**

Make sure your RDS credentials are also set in `.env`, then run:

```bash
python rds_to_snowflake.py
```

Expected output (row counts will vary):
```
[rds_to_snowflake] RAW.orders      → 4,821 rows loaded
[rds_to_snowflake] RAW.order_items → 12,304 rows loaded
[rds_to_snowflake] RAW.products    → 87 rows loaded
```

- [ ] **Step 5: Final commit**

```bash
git add rds_to_snowflake.py
git commit -m "feat: add main() to rds_to_snowflake — RDS to Snowflake loader complete"
```
