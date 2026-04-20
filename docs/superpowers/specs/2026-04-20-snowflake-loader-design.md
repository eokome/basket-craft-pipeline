# Snowflake Loader Design Spec

**Date:** 2026-04-20
**Project:** basket-craft-pipeline
**Goal:** New standalone script `rds_to_snowflake.py` that reads the three Basket Craft raw tables from AWS RDS PostgreSQL and loads them into Snowflake's `BASKET_CRAFT.RAW` schema using the official Snowflake Python connector.

---

## 1. Architecture

New standalone script — no changes to `extract_load.py` or `transform.py`.

```
RDS PostgreSQL (raw.orders / raw.order_items / raw.products)
        ↓  psycopg2  SELECT *
rds_to_snowflake.py
        ↓  snowflake-connector-python  executemany INSERT
Snowflake (BASKET_CRAFT.RAW.orders / .order_items / .products)
```

Full-refresh pattern: each run drops and recreates the three tables in Snowflake's `RAW` schema, then inserts all rows fresh. Mirrors the behavior of `extract_load.py`.

---

## 2. Script: `rds_to_snowflake.py`

### Functions

| Function | Purpose |
|---|---|
| `get_rds_config()` | Returns psycopg2 connection dict from `RDS_*` env vars |
| `get_snowflake_config()` | Returns Snowflake connection dict from `SF_*` env vars |
| `infer_sf_type(value)` | Maps Python types → Snowflake column type strings |
| `copy_table(pg_conn, sf_conn, table_name)` | Full refresh of one table: SELECT from RDS → DROP/CREATE/INSERT in Snowflake |
| `main()` | Loads `.env`, opens both connections, loops over 3 tables |

### Type mapping (`infer_sf_type`)

| Python type | Snowflake type |
|---|---|
| `int` | `NUMBER` |
| `float` | `FLOAT` |
| `decimal.Decimal` | `NUMBER` |
| `datetime` | `TIMESTAMP` |
| `date` | `DATE` |
| anything else | `TEXT` |

### `copy_table` behavior

1. `SELECT *` from `raw.<table_name>` in RDS via psycopg2
2. Infer column types using `infer_sf_type` + `first_non_null` (same helper as `extract_load.py`)
3. In Snowflake: `CREATE SCHEMA IF NOT EXISTS RAW`
4. `DROP TABLE IF EXISTS RAW.<table_name>`
5. `CREATE TABLE RAW.<table_name> (<col_defs>)`
6. `executemany("INSERT INTO RAW.<table> VALUES (%s, ...)", rows)`
7. Commit and print row count

### `main()` behavior

- Calls `load_dotenv()` first (so config functions are importable in tests without `.env`)
- Initializes both connections to `None` before `try` block (avoids `UnboundLocalError` if connection fails)
- Loops over `["orders", "order_items", "products"]`
- Per-table errors caught, printed, and re-raised as `SystemExit(1)`
- `finally` block closes both connections if they were opened

---

## 3. Credentials

New `SF_*` env vars added to `.env.example` and `.env`:

```
# Snowflake destination
SF_ACCOUNT=        # account identifier (e.g. xy12345.us-east-1)
SF_USER=
SF_PASSWORD=
SF_DATABASE=BASKET_CRAFT
SF_SCHEMA=RAW
SF_WAREHOUSE=
SF_ROLE=           # optional — leave blank to use account default
```

`get_snowflake_config()` omits `role` from the dict when `SF_ROLE` is not set (avoids passing `None` to the connector).

---

## 4. Dependency

Add to `requirements.txt`:

```
snowflake-connector-python==3.11.0
```

---

## 5. Tests: `tests/test_rds_to_snowflake.py`

Follows the same `unittest.mock.patch` style as `tests/test_extract_load.py`.

| Test | What it covers |
|---|---|
| `test_get_rds_config_returns_correct_keys` | All `RDS_*` env vars read correctly; key is `dbname` (not `database`) |
| `test_get_snowflake_config_returns_correct_keys` | All `SF_*` env vars read correctly |
| `test_get_snowflake_config_omits_role_when_unset` | `role` key absent when `SF_ROLE` not in env |
| `test_infer_sf_type_int` | `int` → `NUMBER` |
| `test_infer_sf_type_float` | `float` → `FLOAT` |
| `test_infer_sf_type_decimal` | `decimal.Decimal` → `NUMBER` |
| `test_infer_sf_type_date` | `date` → `DATE` |
| `test_infer_sf_type_datetime` | `datetime` → `TIMESTAMP` |
| `test_infer_sf_type_str` | `str` → `TEXT` |
| `test_copy_table_creates_schema_drops_and_inserts` | Mocks both connections; verifies CREATE SCHEMA, DROP, CREATE TABLE, executemany all called |

---

## 6. Run

```bash
python rds_to_snowflake.py
```

Expected output:
```
[rds_to_snowflake] RAW.orders      → 4,821 rows loaded
[rds_to_snowflake] RAW.order_items → 12,304 rows loaded
[rds_to_snowflake] RAW.products    → 87 rows loaded
```

---

## 7. Out of Scope

- Incremental/delta loading
- Running `transform.py` against Snowflake
- Snowflake Stage + COPY INTO optimization
- Schema inference for nested/complex types
