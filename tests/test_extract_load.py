import os
import pytest
from unittest.mock import patch
from datetime import date, datetime
from decimal import Decimal


def test_get_mysql_config_raises_on_missing_env_vars():
    with patch.dict(os.environ, {}, clear=True):
        from extract_load import get_mysql_config
        with pytest.raises(KeyError):
            get_mysql_config()


def test_get_pg_config_raises_on_missing_env_vars():
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


def test_get_mysql_config_returns_correct_keys():
    env = {
        "MYSQL_HOST": "db.example.com",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "user",
        "MYSQL_PASSWORD": "pass",
        "MYSQL_DB": "mydb",
    }
    with patch.dict(os.environ, env, clear=True):
        from extract_load import get_mysql_config
        config = get_mysql_config()
    assert config["host"] == "db.example.com"
    assert config["port"] == 3306          # must be int, not string
    assert config["user"] == "user"
    assert config["password"] == "pass"
    assert config["database"] == "mydb"    # PyMySQL requires "database", not "dbname"


def test_get_pg_config_returns_correct_keys():
    env = {
        "PG_HOST": "localhost",
        "PG_PORT": "5432",
        "PG_USER": "student",
        "PG_PASSWORD": "student123",
        "PG_DB": "basket_craft",
    }
    with patch.dict(os.environ, env, clear=True):
        from extract_load import get_pg_config
        config = get_pg_config()
    assert config["host"] == "localhost"
    assert config["port"] == 5432          # must be int, not string
    assert config["user"] == "student"
    assert config["password"] == "student123"
    assert config["dbname"] == "basket_craft"  # psycopg2 requires "dbname", not "database"
