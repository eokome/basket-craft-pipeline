import os

import pandas as pd
import psycopg2
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas


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


def copy_table(pg_conn, sf_conn, table_name):
    """Copy one RDS raw table into the RAW schema in Snowflake.

    Tables and columns are created UPPERCASE so they can be queried in
    Snowflake without double-quotes (e.g. SELECT * FROM orders).
    write_pandas stages the data as Parquet and uses COPY INTO internally,
    which is the production-standard Snowflake ingestion path.
    """
    with pg_conn.cursor() as pc:
        pc.execute(f'SELECT * FROM raw."{table_name}"')
        rows = pc.fetchall()
        col_names = [d[0] for d in pc.description]

    if not rows:
        print(f"[rds_to_snowflake] {table_name.upper()} → 0 rows (empty source)")
        return

    df = pd.DataFrame(rows, columns=col_names)
    df.columns = df.columns.str.upper()

    success, _nchunks, nrows, _ = write_pandas(
        sf_conn,
        df,
        table_name.upper(),
        overwrite=True,
        quote_identifiers=False,
    )
    print(f"[rds_to_snowflake] {table_name.upper()} → {nrows:,} rows loaded")


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
