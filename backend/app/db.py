"""Database connection. Reads DATABASE_URL from the environment."""
import os

import psycopg
from psycopg.rows import dict_row


def get_conn(url=None):
    """Open a connection. Rows come back as dicts.

    autocommit is on, so `with conn.transaction():` starts a real transaction
    and commits or rolls back exactly at the end of the block.
    """
    return psycopg.connect(
        url or os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row
    )
