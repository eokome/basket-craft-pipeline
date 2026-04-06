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
