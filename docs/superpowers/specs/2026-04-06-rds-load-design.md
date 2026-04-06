# RDS Load Design Spec

**Date:** 2026-04-06
**Project:** basket-craft-pipeline
**Goal:** Allow `extract_load.py` to target either local Docker Postgres or AWS RDS Postgres by reading a `TARGET` env var, with credentials for both stored in `.env`.

---

## 1. Architecture

No structural change to the ELT pipeline. This is a targeted modification to `get_pg_config()` in `extract_load.py` to support two destination environments.

```
TARGET=rds python extract_load.py   → reads RDS_* vars → AWS RDS Postgres
python extract_load.py              → reads PG_* vars  → local Docker Postgres
```

---

## 2. Change

**File:** `.worktrees/implement/extract_load.py`
**Function:** `get_pg_config()`

Current behavior: always reads `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB`.

New behavior: checks `os.environ.get("TARGET", "local")`:
- If `"rds"` → reads `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE`
- Otherwise → reads `PG_*` keys unchanged

```python
def get_pg_config():
    if os.environ.get("TARGET") == "rds":
        return {
            "host":     os.environ["RDS_HOST"],
            "port":     int(os.environ.get("RDS_PORT", "5432")),
            "user":     os.environ["RDS_USER"],
            "password": os.environ["RDS_PASSWORD"],
            "dbname":   os.environ["RDS_DATABASE"],
        }
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }
```

---

## 3. `.env` — no changes needed

The `.env` already contains both credential sets:

```
# Local Docker Postgres
PG_HOST=localhost
PG_PORT=5432
PG_USER=student
PG_PASSWORD=student123
PG_DB=basket_craft

# AWS RDS Postgres
RDS_HOST=basket-craft-db.cg7eky00i67b.us-east-1.rds.amazonaws.com
RDS_PORT=5432
RDS_USER=student
RDS_PASSWORD=go_lions
RDS_DATABASE=basket_craft
```

---

## 4. Tests

Existing tests for `get_pg_config()` mock `os.environ` with `PG_*` keys — they remain valid for the non-RDS path.

One new test covers the RDS path:

```python
def test_get_pg_config_rds_returns_rds_keys():
    rds_env = {
        "TARGET": "rds",
        "RDS_HOST": "rds.example.com",
        "RDS_USER": "u",
        "RDS_PASSWORD": "p",
        "RDS_DATABASE": "db",
    }
    with patch.dict(os.environ, rds_env, clear=True):
        from extract_load import get_pg_config
        cfg = get_pg_config()
    assert cfg["host"] == "rds.example.com"
    assert cfg["dbname"] == "db"
```

---

## 5. Run

```bash
# Load raw tables into RDS
TARGET=rds python extract_load.py

# Load raw tables into local Docker (unchanged)
python extract_load.py
```

Expected output (row counts will vary):
```
[extract_load] raw.orders      → 4,821 rows loaded
[extract_load] raw.order_items → 12,304 rows loaded
[extract_load] raw.products    → 87 rows loaded
```

---

## 6. Out of Scope

- Incremental/delta extraction
- RDS security group configuration
- Running `transform.py` against RDS (separate concern)
