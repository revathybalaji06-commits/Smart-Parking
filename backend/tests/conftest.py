"""Test setup. Tests use their own database and WIPE its tables each time.

    createdb smart_parking_test
    export TEST_DATABASE_URL=postgresql://localhost/smart_parking_test
    cd backend && pytest
"""
import os

import pytest

from app.db import get_conn, setup_database


@pytest.fixture()
def conn():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run the tests")
    os.environ["DATABASE_URL"] = url
    c = get_conn()
    c.execute("DROP TABLE IF EXISTS reservations, slots CASCADE")
    setup_database(c)  # fresh tables + the 50 slots
    c.execute("UPDATE slots SET status = 'free'")  # the demo seed has some cars parked; start empty
    yield c
    c.close()
