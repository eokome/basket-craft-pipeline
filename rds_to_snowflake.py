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
