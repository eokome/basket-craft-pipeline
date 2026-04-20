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
