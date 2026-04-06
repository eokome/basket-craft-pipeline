import os
import decimal
from datetime import date, datetime

import pymysql
import psycopg2
import psycopg2.extras


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


def first_non_null(rows, col_index):
    """Return the first non-null value for a given column, or None."""
    for row in rows:
        if row[col_index] is not None:
            return row[col_index]
    return None


def copy_table(mysql_conn, pg_conn, table_name):
    """Copy one MySQL table into the raw schema in PostgreSQL."""
    with mysql_conn.cursor() as mc:
        mc.execute(f"SELECT * FROM `{table_name}`")
        rows = mc.fetchall()
        col_names = [d[0] for d in mc.description]

    if not rows:
        print(f"[extract_load] raw.{table_name} → 0 rows (empty source)")
        return

    pg_types = [infer_pg_type(first_non_null(rows, i)) for i in range(len(col_names))]
    col_defs  = ", ".join(f'"{c}" {t}' for c, t in zip(col_names, pg_types))

    with pg_conn.cursor() as pc:
        pc.execute("CREATE SCHEMA IF NOT EXISTS raw")
        pc.execute(f'DROP TABLE IF EXISTS raw."{table_name}"')
        pc.execute(f'CREATE TABLE raw."{table_name}" ({col_defs})')
        psycopg2.extras.execute_values(
            pc,
            f'INSERT INTO raw."{table_name}" VALUES %s',
            rows,
        )
    pg_conn.commit()
    print(f"[extract_load] raw.{table_name} → {len(rows):,} rows loaded")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    mysql_conn = None
    pg_conn    = None
    try:
        mysql_conn = pymysql.connect(**get_mysql_config())
        pg_conn    = psycopg2.connect(**get_pg_config())
        for table in ["orders", "order_items", "products"]:
            try:
                copy_table(mysql_conn, pg_conn, table)
            except Exception as e:
                print(f"[extract_load] ERROR copying {table}: {e}")
                raise SystemExit(1)
    finally:
        if mysql_conn is not None:
            mysql_conn.close()
        if pg_conn is not None:
            pg_conn.close()


if __name__ == "__main__":
    main()
