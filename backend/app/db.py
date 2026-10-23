"""Connect to PostgreSQL and create the demo database tables."""

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DATABASE_FOLDER = Path(__file__).resolve().parents[2] / "db"
DEFAULT_DATABASE_URL = "postgresql://localhost/smart_parking"


def get_conn():
    """Open a PostgreSQL connection that returns rows as dictionaries."""
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return psycopg.connect(database_url, autocommit=True, row_factory=dict_row)


def setup_database(conn):
    """Run the table definitions and add the demo parking spaces."""
    for filename in ("schema.sql", "seed.sql"):
        sql_file = DATABASE_FOLDER / filename
        conn.execute(sql_file.read_text())
