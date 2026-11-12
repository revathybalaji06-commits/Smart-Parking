"""Tests for the parking logic."""
import pytest

from app.reservations import (
    ParkingError, arrive, cancel, depart, free_expired_holds, get_availability, reserve,
)


def slot_status(conn, slot_id):
    return conn.execute("SELECT status FROM slots WHERE id = %s", (slot_id,)).fetchone()["status"]


def test_sedan_gets_smallest_sedan_slot(conn):
    result = reserve(conn, "TN01", 2)
    assert result["label"] == "S1"
    assert slot_status(conn, result["slot_id"]) == "reserved"


def test_next_size_up_when_class_is_full(conn):
    conn.execute("UPDATE slots SET status = 'occupied' WHERE size_class = 2")
    assert reserve(conn, "TN01", 2)["label"] == "U1"  # an SUV slot


def test_never_a_smaller_slot(conn):
    conn.execute("UPDATE slots SET status = 'occupied' WHERE size_class >= 3")
    with pytest.raises(ParkingError) as error:
        reserve(conn, "TN01", 4)  # Full-Size car, only small slots are free
    assert error.value.code == "no_valid_slot"


def test_lot_full(conn):
    conn.execute("UPDATE slots SET status = 'occupied'")
    with pytest.raises(ParkingError) as error:
        reserve(conn, "TN01", 1)
    assert error.value.code == "lot_full"


def test_bad_input(conn):
    with pytest.raises(ParkingError):
        reserve(conn, "  ", 1)
    with pytest.raises(ParkingError):
        reserve(conn, "TN01", 9)


def test_arrive_then_depart(conn):
    r = reserve(conn, "TN01", 1)
    arrive(conn, r["reservation_id"])
    assert slot_status(conn, r["slot_id"]) == "occupied"
    depart(conn, r["reservation_id"])
    assert slot_status(conn, r["slot_id"]) == "free"


def test_cancel_frees_the_slot(conn):
    r = reserve(conn, "TN01", 1)
    cancel(conn, r["reservation_id"])
    assert slot_status(conn, r["slot_id"]) == "free"


def test_cannot_depart_before_arriving(conn):
    r = reserve(conn, "TN01", 1)
    with pytest.raises(ParkingError):
        depart(conn, r["reservation_id"])


def test_expired_hold_frees_the_slot(conn):
    r = reserve(conn, "TN01", 1)
    conn.execute("UPDATE reservations SET expires_at = now() - interval '1 minute'")
    free_expired_holds(conn)
    assert slot_status(conn, r["slot_id"]) == "free"


def test_availability_equation(conn):
    reserve(conn, "TN01", 2)
    lot = get_availability(conn)["lot"]
    assert lot == {"free": 49, "max": 50}  # Available = Max - Occupied


def test_plate_is_cleaned_up(conn):
    r = reserve(conn, " tn 37 ab-1234 ", 2)
    saved = conn.execute(
        "SELECT plate FROM reservations WHERE id = %s", (r["reservation_id"],)
    ).fetchone()["plate"]
    assert saved == "TN37AB1234"


def test_bad_plates_are_rejected(conn):
    for plate in ["TN37AB1234567", "TN37@AB", "---"]:
        with pytest.raises(ParkingError) as error:
            reserve(conn, plate, 1)
        assert error.value.code == "invalid_request"


def test_one_plate_cannot_hold_two_slots(conn):
    first = reserve(conn, "TN01", 1)
    with pytest.raises(ParkingError) as error:
        reserve(conn, "tn 01", 2)  # the same vehicle, typed differently
    assert error.value.code == "already_reserved"

    # after cancelling (or leaving), the vehicle can reserve again
    cancel(conn, first["reservation_id"])
    reserve(conn, "TN01", 1)
