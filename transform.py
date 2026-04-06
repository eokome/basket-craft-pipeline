import os
import psycopg2


def get_pg_config():
    return {
        "host":     os.environ["PG_HOST"],
        "port":     int(os.environ.get("PG_PORT", "5432")),
        "user":     os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "dbname":   os.environ["PG_DB"],
    }


def run_transform(pg_conn, sql_path):
    """Execute the aggregation SQL and print the resulting row count."""
    with open(sql_path) as f:
        sql = f.read()

    with pg_conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS marts")
        cur.execute(sql)
        cur.execute("SELECT COUNT(*) FROM marts.monthly_sales_summary")
        row_count = cur.fetchone()[0]

    pg_conn.commit()
    print(f"[transform]    marts.monthly_sales_summary → {row_count:,} rows")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    sql_path = os.path.join(os.path.dirname(__file__), "sql", "monthly_sales.sql")
    pg_conn  = psycopg2.connect(**get_pg_config())

    try:
        run_transform(pg_conn, sql_path)
    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
