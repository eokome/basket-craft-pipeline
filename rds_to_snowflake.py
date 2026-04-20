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
