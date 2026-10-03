"""Tests for arrive / depart / cancel / expiry / availability."""
import pytest

from app.reservations import (
    ReservationError,
    arrive,
    cancel,
    depart,
    expire_stale,
    get_availability,
    get_reservation,
    reserve,
)


def slot_status(conn, slot_id):
    return conn.execute("SELECT status FROM slots WHERE id=%s", (slot_id,)).fetchone()["status"]


def expire_now(conn, reservation_id):
    conn.execute(
        "UPDATE reservations SET expires_at = now() - interval '1 minute' WHERE id=%s",
        (reservation_id,),
    )


def test_full_lifecycle(conn):
    r = reserve(conn, "A", 2)
    assert arrive(conn, r["reservation_id"])["slot_status"] == "occupied"
    assert slot_status(conn, r["slot_id"]) == "occupied"
    out = depart(conn, r["reservation_id"])
    assert out["status"] == "completed" and out["slot_status"] == "free"
    assert slot_status(conn, r["slot_id"]) == "free"
    assert get_reservation(conn, r["reservation_id"])["ended_at"] is not None


def test_cancel_frees_slot(conn):
    r = reserve(conn, "A", 1)
    assert cancel(conn, r["reservation_id"])["status"] == "cancelled"
    assert slot_status(conn, r["slot_id"]) == "free"
    assert reserve(conn, "B", 1)["slot_id"] == r["slot_id"]  # slot is reusable


def test_cannot_depart_before_arrive(conn):
    r = reserve(conn, "A", 1)
    with pytest.raises(ReservationError) as e:
        depart(conn, r["reservation_id"])
    assert e.value.error == "invalid_state"


def test_cannot_cancel_after_arrive(conn):
    r = reserve(conn, "A", 1)
    arrive(conn, r["reservation_id"])
    with pytest.raises(ReservationError) as e:
        cancel(conn, r["reservation_id"])
    assert e.value.error == "invalid_state"


def test_cannot_arrive_twice(conn):
    r = reserve(conn, "A", 1)
    arrive(conn, r["reservation_id"])
    with pytest.raises(ReservationError):
        arrive(conn, r["reservation_id"])


@pytest.mark.parametrize("action", [arrive, depart, cancel, get_reservation])
def test_unknown_reservation_is_404(conn, action):
    with pytest.raises(ReservationError) as e:
        action(conn, 99999)
    assert e.value.error == "not_found" and e.value.status == 404


def test_cannot_arrive_after_hold_expired(conn):
    r = reserve(conn, "A", 1)
    expire_now(conn, r["reservation_id"])
    with pytest.raises(ReservationError) as e:
        arrive(conn, r["reservation_id"])
    assert e.value.error == "invalid_state"


def test_expiry_frees_slot_and_marks_expired(conn):
    r = reserve(conn, "A", 1)
    expire_now(conn, r["reservation_id"])
    assert expire_stale(conn) == 1
    assert slot_status(conn, r["slot_id"]) == "free"
    assert get_reservation(conn, r["reservation_id"])["status"] == "expired"


def test_expiry_never_frees_an_occupied_slot(conn):
    r = reserve(conn, "A", 1)
    arrive(conn, r["reservation_id"])
    conn.execute("UPDATE reservations SET expires_at = now() - interval '1 hour'")
    expire_stale(conn)
    assert slot_status(conn, r["slot_id"]) == "occupied"


def test_reserve_reclaims_expired_slot(conn):
    conn.execute("UPDATE slots SET status='occupied' WHERE label <> 'C1'")
    r = reserve(conn, "A", 1)
    expire_now(conn, r["reservation_id"])
    assert reserve(conn, "B", 1)["label"] == "C1"  # lot was "full" but the hold expired


def test_availability_counts(conn):
    r = reserve(conn, "A", 2)
    a = get_availability(conn)
    assert a["lot"] == {"free": 49, "max": 50}
    sedan = next(c for c in a["classes"] if c["class"] == 2)
    assert sedan == {"class": 2, "name": "Sedan", "free": 19, "max": 20}
    arrive(conn, r["reservation_id"])
    depart(conn, r["reservation_id"])
    assert get_availability(conn)["lot"]["free"] == 50
