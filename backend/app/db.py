"""Database connection and first-time setup."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DB_FOLDER = Path(__file__).resolve().parents[2] / "db"


def get_conn():
    """Open a connection to PostgreSQL. Rows come back as dictionaries."""
    url = os.environ.get("DATABASE_URL", "postgresql://localhost/smart_parking")
    return psycopg.connect(url, autocommit=True, row_factory=dict_row)


def setup_database(conn):
    """Create the tables and the 50 demo slots. Safe to run many times."""
    conn.execute((DB_FOLDER / "schema.sql").read_text())
    conn.execute((DB_FOLDER / "seed.sql").read_text())
