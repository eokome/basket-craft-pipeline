import os
import decimal
from datetime import date, datetime


def get_mysql_config():
    return {
        "host":     os.environ["MYSQL_HOST"],
        "port":     int(os.environ.get("MYSQL_PORT", "3306")),
        "user":     os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.environ["MYSQL_DB"],
    }


def get_pg_config():
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }


def infer_pg_type(value):
    """Map a Python value to a PostgreSQL column type string."""
    if isinstance(value, datetime):        return "TIMESTAMP"
    if isinstance(value, date):            return "DATE"
    if isinstance(value, int):             return "BIGINT"
    if isinstance(value, float):           return "DOUBLE PRECISION"
    if isinstance(value, decimal.Decimal): return "NUMERIC"
    return "TEXT"


def copy_table(mysql_conn, pg_conn, table_name):
    pass  # implemented in Task 4


def main():
    pass  # implemented in Task 4


if __name__ == "__main__":
    main()
