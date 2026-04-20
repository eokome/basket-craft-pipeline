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
        "SNOWFLAKE_ACCOUNT":   "xy12345.us-east-1",
        "SNOWFLAKE_USER":      "student",
        "SNOWFLAKE_PASSWORD":  "secret",
        "SNOWFLAKE_DATABASE":  "BASKET_CRAFT",
        "SNOWFLAKE_SCHEMA":    "RAW",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
        "SNOWFLAKE_ROLE":      "SYSADMIN",
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
        "SNOWFLAKE_ACCOUNT":   "xy12345.us-east-1",
        "SNOWFLAKE_USER":      "student",
        "SNOWFLAKE_PASSWORD":  "secret",
        "SNOWFLAKE_DATABASE":  "BASKET_CRAFT",
        "SNOWFLAKE_SCHEMA":    "RAW",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_snowflake_config
        cfg = get_snowflake_config()
    assert "role" not in cfg


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
    assert any("DROP TABLE IF EXISTS" in c for c in sf_calls)
    assert any("CREATE TABLE" in c for c in sf_calls)
    mock_sf_cur.executemany.assert_called_once()
    mock_sf_conn.commit.assert_called_once()
