import os
import pytest
from unittest.mock import patch, MagicMock


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
        "SNOWFLAKE_DATABASE":  "basket_craft",
        "SNOWFLAKE_SCHEMA":    "raw",
        "SNOWFLAKE_WAREHOUSE": "basket_craft_wh",
        "SNOWFLAKE_ROLE":      "basket_craft_loader",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_snowflake_config
        cfg = get_snowflake_config()
    assert cfg["account"]   == "xy12345.us-east-1"
    assert cfg["user"]      == "student"
    assert cfg["password"]  == "secret"
    assert cfg["database"]  == "basket_craft"
    assert cfg["schema"]    == "raw"
    assert cfg["warehouse"] == "basket_craft_wh"
    assert cfg["role"]      == "basket_craft_loader"


def test_get_snowflake_config_omits_role_when_unset():
    env = {
        "SNOWFLAKE_ACCOUNT":   "xy12345.us-east-1",
        "SNOWFLAKE_USER":      "student",
        "SNOWFLAKE_PASSWORD":  "secret",
        "SNOWFLAKE_DATABASE":  "basket_craft",
        "SNOWFLAKE_SCHEMA":    "raw",
        "SNOWFLAKE_WAREHOUSE": "basket_craft_wh",
    }
    with patch.dict(os.environ, env, clear=True):
        from rds_to_snowflake import get_snowflake_config
        cfg = get_snowflake_config()
    assert "role" not in cfg


def test_copy_table_uses_write_pandas_with_uppercase_names():
    """copy_table must use write_pandas, uppercase the table name and all
    column names, set overwrite=True, and set quote_identifiers=False."""
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

    mock_sf_conn = MagicMock()

    with patch("rds_to_snowflake.write_pandas", return_value=(True, 1, 2, None)) as mock_wp:
        from rds_to_snowflake import copy_table
        copy_table(mock_pg_conn, mock_sf_conn, "products")

    mock_wp.assert_called_once()
    _, kwargs = mock_wp.call_args
    positional = mock_wp.call_args[0]

    # Table name must be UPPERCASE
    assert positional[2] == "PRODUCTS"

    # All DataFrame columns must be UPPERCASE
    df_arg = positional[1]
    assert list(df_arg.columns) == ["PRODUCT_ID", "PRODUCT_NAME", "PRICE_USD"]

    # write_pandas flags
    assert kwargs.get("overwrite") is True
    assert kwargs.get("quote_identifiers") is False
