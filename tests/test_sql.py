import os

SQL_PATH = os.path.join(os.path.dirname(__file__), "..", "sql", "monthly_sales.sql")


def test_sql_file_exists():
    assert os.path.isfile(SQL_PATH), f"Expected SQL file at {SQL_PATH}"


def test_sql_file_has_required_clauses():
    with open(SQL_PATH) as f:
        sql = f.read().upper()
    assert "SELECT" in sql
    assert "GROUP BY" in sql
    assert "DATE_TRUNC" in sql
    assert "SUM" in sql
    assert "COUNT" in sql
    assert "NULLIF" in sql
