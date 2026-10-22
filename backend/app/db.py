"""Database connection and first-time setup."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# The db/ folder sits two levels above this file: Smart-Parking/db
DB_FOLDER = Path(__file__).resolve().parents[2] / "db"


def get_conn():
    """Open a connection to PostgreSQL.

    autocommit=True means nothing is saved until we say so with
    `with conn.transaction():` - that block saves everything together,
    or nothing at all if an error happens inside it.
    """
    url = os.environ.get("DATABASE_URL", "postgresql://localhost/smart_parking")
    return psycopg.connect(url, autocommit=True, row_factory=dict_row)


def setup_database(conn):
    """Create the tables and the 50 demo slots. Safe to run many times."""
    for name in ("schema.sql", "seed.sql"):
        conn.execute((DB_FOLDER / name).read_text())
