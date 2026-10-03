"""Tests for reserve(). Needs a scratch Postgres DB:

    createdb smart_parking_test
    export TEST_DATABASE_URL=postgresql://localhost/smart_parking_test
    pytest backend/tests

WARNING: the fixture drops and recreates the slots/reservations tables.
"""
import os
import threading
from pathlib import Path

import pytest

from app.db import get_conn
from app.reservations import ReservationError, reserve

URL = os.environ.get("TEST_DATABASE_URL")
DB_DIR = Path(__file__).resolve().parents[2] / "db"

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def conn():
    c = get_conn(URL)
    c.execute("DROP TABLE IF EXISTS reservations, slots CASCADE")
    c.execute((DB_DIR / "schema.sql").read_text())
    c.execute((DB_DIR / "seed.sql").read_text())
    yield c
    c.close()


def fill_class(conn, size_class):
    conn.execute(
        "UPDATE slots SET status = 'occupied' WHERE size_class = %s", (size_class,)
    )


def test_gets_smallest_fitting_slot(conn):
    r = reserve(conn, "TN01A1", 2)
    assert r["label"] == "S1" and r["size_class"] == 2 and r["status"] == "active"
    assert conn.execute("SELECT status FROM slots WHERE label='S1'").fetchone()[
        "status"
    ] == "reserved"


def test_compact_gets_compact_slot(conn):
    assert reserve(conn, "TN01A2", 1)["label"] == "C1"


def test_same_class_gets_next_slot(conn):
    assert reserve(conn, "A", 2)["label"] == "S1"
    assert reserve(conn, "B", 2)["label"] == "S2"


def test_upgrades_to_next_larger_class_when_class_full(conn):
    fill_class(conn, 2)
    assert reserve(conn, "A", 2)["label"] == "U1"


def test_never_gets_a_smaller_slot(conn):
    fill_class(conn, 4)
    fill_class(conn, 3)
    # Compact/Sedan slots are free, but a Full-Size car does not fit them
    with pytest.raises(ReservationError) as e:
        reserve(conn, "A", 4)
    assert e.value.error == "no_valid_slot" and e.value.status == 409


def test_lot_full(conn):
    conn.execute("UPDATE slots SET status = 'occupied'")
    with pytest.raises(ReservationError) as e:
        reserve(conn, "A", 1)
    assert e.value.error == "lot_full" and e.value.status == 409


@pytest.mark.parametrize("plate,cls", [("", 1), ("  ", 1), (None, 1), ("A", 0), ("A", 5), ("A", "2")])
def test_invalid_request(conn, plate, cls):
    with pytest.raises(ReservationError) as e:
        reserve(conn, plate, cls)
    assert e.value.error == "invalid_request" and e.value.status == 400


def test_failed_reserve_changes_nothing(conn):
    conn.execute("UPDATE slots SET status = 'occupied'")
    with pytest.raises(ReservationError):
        reserve(conn, "A", 1)
    assert conn.execute("SELECT count(*) AS n FROM reservations").fetchone()["n"] == 0


def test_concurrent_requests_get_different_slots(conn):
    results, errors = [], []

    def worker(i):
        c = get_conn(URL)
        try:
            results.append(reserve(c, f"CAR{i}", 2)["slot_id"])
        except Exception as ex:  # noqa: BLE001
            errors.append(ex)
        finally:
            c.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(15)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert len(set(results)) == 15
