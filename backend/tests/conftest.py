"""Shared fixtures. Needs a scratch Postgres DB:

    createdb smart_parking_test
    export TEST_DATABASE_URL=postgresql://localhost/smart_parking_test
    pytest backend

WARNING: the fixture drops and recreates the slots/reservations tables.
"""
import os
from pathlib import Path

import pytest

from app.db import get_conn

URL = os.environ.get("TEST_DATABASE_URL")
DB_DIR = Path(__file__).resolve().parents[2] / "db"


@pytest.fixture()
def conn():
    if not URL:
        pytest.skip("TEST_DATABASE_URL not set")
    c = get_conn(URL)
    c.execute("DROP TABLE IF EXISTS reservations, slots CASCADE")
    c.execute((DB_DIR / "schema.sql").read_text())
    c.execute((DB_DIR / "seed.sql").read_text())
    yield c
    c.close()
