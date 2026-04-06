import os
import pytest
from unittest.mock import patch, MagicMock, mock_open


def test_get_pg_config_raises_on_missing_host():
    with patch.dict(os.environ, {}, clear=True):
        from transform import get_pg_config
        with pytest.raises(KeyError):
            get_pg_config()


def test_run_transform_reads_sql_and_executes():
    """run_transform must read the SQL file and pass its contents to execute()."""
    sql_content = "DROP TABLE IF EXISTS marts.monthly_sales_summary; CREATE TABLE marts.monthly_sales_summary AS SELECT 1 AS n;"

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (36,)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("builtins.open", mock_open(read_data=sql_content)):
        from transform import run_transform
        run_transform(mock_conn, "fake/path.sql")

    # The SQL content must have been passed to execute
    calls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any(sql_content in c for c in calls), \
        "Expected run_transform to execute the SQL file contents"

    mock_conn.commit.assert_called_once()
