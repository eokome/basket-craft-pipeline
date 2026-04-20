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
        "account":   os.environ["SNOWFLAKE_ACCOUNT"],
        "user":      os.environ["SNOWFLAKE_USER"],
        "password":  os.environ["SNOWFLAKE_PASSWORD"],
        "database":  os.environ["SNOWFLAKE_DATABASE"],
        "schema":    os.environ["SNOWFLAKE_SCHEMA"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
    }
    role = os.environ.get("SNOWFLAKE_ROLE")
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


def copy_table(pg_conn, sf_conn, table_name):
    """Copy one RDS raw table into the RAW schema in Snowflake."""
    with pg_conn.cursor() as pc:
        pc.execute(f'SELECT * FROM raw."{table_name}"')
        rows = pc.fetchall()
        col_names = [d[0] for d in pc.description]

    if not rows:
        print(f"[rds_to_snowflake] RAW.{table_name} → 0 rows (empty source)")
        return

    sf_types     = [infer_sf_type(first_non_null(rows, i)) for i in range(len(col_names))]
    col_defs     = ", ".join(f'"{c}" {t}' for c, t in zip(col_names, sf_types))
    placeholders = ", ".join(["%s"] * len(col_names))

    with sf_conn.cursor() as sc:
        sc.execute(f'DROP TABLE IF EXISTS "RAW"."{table_name}"')
        sc.execute(f'CREATE TABLE "RAW"."{table_name}" ({col_defs})')
        sc.executemany(
            f'INSERT INTO "RAW"."{table_name}" VALUES ({placeholders})',
            rows,
        )
    sf_conn.commit()
    print(f"[rds_to_snowflake] RAW.{table_name} → {len(rows):,} rows loaded")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    pg_conn = None
    sf_conn = None
    try:
        pg_conn = psycopg2.connect(**get_rds_config())
        sf_conn = snowflake.connector.connect(**get_snowflake_config())
        for table in ["orders", "order_items", "products"]:
            try:
                copy_table(pg_conn, sf_conn, table)
            except Exception as e:
                print(f"[rds_to_snowflake] ERROR copying {table}: {e}")
                raise SystemExit(1)
    finally:
        if pg_conn is not None:
            pg_conn.close()
        if sf_conn is not None:
            sf_conn.close()


if __name__ == "__main__":
    main()
