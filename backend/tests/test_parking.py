"""Tests for the parking rules, the routes and the API."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reservations import ParkingError, arrive, cancel, depart, free_expired_holds, get_availability, reserve
from app.routing import EDGES, NODES, build_route, road_start_for, shortest_path
from app.simulator import tick


def slot_status(conn, slot_id):
    return conn.execute("SELECT status FROM slots WHERE id = %s", (slot_id,)).fetchone()["status"]


def error_code(action):
    with pytest.raises(ParkingError) as error:
        action()
    return error.value.code


# ---- reserving ----
def test_sedan_gets_smallest_sedan_slot(conn):
    r = reserve(conn, "TN01", 2)
    assert r["label"] == "S1" and slot_status(conn, r["slot_id"]) == "reserved"


def test_next_size_up_when_class_is_full(conn):
    conn.execute("UPDATE slots SET status = 'occupied' WHERE size_class = 2")
    assert reserve(conn, "TN01", 2)["label"] == "U1"  # an SUV slot


def test_never_a_smaller_slot(conn):
    conn.execute("UPDATE slots SET status = 'occupied' WHERE size_class >= 3")
    assert error_code(lambda: reserve(conn, "TN01", 4)) == "no_valid_slot"


def test_lot_full(conn):
    conn.execute("UPDATE slots SET status = 'occupied'")
    assert error_code(lambda: reserve(conn, "TN01", 1)) == "lot_full"


def test_bad_input(conn):
    for plate, vehicle_class in [("  ", 1), ("TN01", 9), ("TN37AB1234567", 1), ("TN@1", 1)]:
        assert error_code(lambda: reserve(conn, plate, vehicle_class)) == "invalid_request"


def test_one_plate_cannot_hold_two_slots(conn):
    first = reserve(conn, " tn 01 ", 1)
    assert first["plate"] == "TN01"
    assert error_code(lambda: reserve(conn, "TN-01", 2)) == "already_reserved"
    cancel(conn, first["reservation_id"])
    reserve(conn, "TN01", 1)  # allowed again after cancelling


# ---- arrive, depart, cancel, expire ----
def test_arrive_then_depart(conn):
    r = reserve(conn, "TN01", 1)
    assert arrive(conn, r["reservation_id"])["slot_status"] == "occupied"
    assert depart(conn, r["reservation_id"])["status"] == "completed"
    assert slot_status(conn, r["slot_id"]) == "free"


def test_cancel_frees_the_slot(conn):
    r = reserve(conn, "TN01", 1)
    assert cancel(conn, r["reservation_id"])["status"] == "cancelled"
    assert slot_status(conn, r["slot_id"]) == "free"


def test_wrong_order_is_refused(conn):
    r = reserve(conn, "TN01", 1)
    assert error_code(lambda: depart(conn, r["reservation_id"])) == "invalid_state"  # not arrived yet
    arrive(conn, r["reservation_id"])
    assert error_code(lambda: cancel(conn, r["reservation_id"])) == "invalid_state"  # already parked
    assert error_code(lambda: arrive(conn, 999)) == "not_found"


def test_expired_hold_frees_the_slot(conn):
    r = reserve(conn, "TN01", 1)
    conn.execute("UPDATE reservations SET expires_at = now() - interval '1 minute'")
    assert error_code(lambda: arrive(conn, r["reservation_id"])) == "invalid_state"
    assert slot_status(conn, r["slot_id"]) == "free"


def test_parked_car_never_expires(conn):
    r = reserve(conn, "TN01", 1)
    arrive(conn, r["reservation_id"])
    free_expired_holds(conn)
    assert slot_status(conn, r["slot_id"]) == "occupied"


def test_availability_equation(conn):
    reserve(conn, "TN01", 2)
    assert get_availability(conn)["lot"] == {"free": 49, "max": 50}  # Available = Max - Occupied


# ---- routes ----
def test_every_slot_has_a_route_along_the_one_way_roads(conn):
    for slot in conn.execute("SELECT * FROM slots").fetchall():
        path = shortest_path("ENTRY", road_start_for((slot["access_x"], slot["access_y"])))
        assert all(piece in EDGES for piece in zip(path, path[1:]))  # never against the arrows
        route = build_route(slot)
        assert route["points"][0] == NODES["ENTRY"]
        assert route["steps"][-1]["text"].endswith("You have arrived.")


def test_directions(conn):
    slot = conn.execute("SELECT * FROM slots WHERE label = 'S1'").fetchone()
    assert [step["text"] for step in build_route(slot)["steps"]] == [
        "Enter through the entry gate and drive straight for 74 m.",
        "Turn right and drive 25 m.",
        "Turn right into bay S1. You have arrived.",
    ]


# ---- pretend traffic ----
def test_traffic_fills_to_40_percent_and_leaves_app_cars_alone(conn):
    mine = reserve(conn, "TN01", 2)
    for _ in range(100):
        tick(conn)
    assert slot_status(conn, mine["slot_id"]) == "reserved"
    others = conn.execute("SELECT count(*) AS n FROM slots WHERE status = 'occupied'").fetchone()["n"]
    assert others in (19, 20)  # 40% of 50


# ---- the API ----
def test_api(conn):
    client = TestClient(app)
    assert client.get("/availability").json()["lot"]["free"] == 50
    assert client.get("/layout").json()["nodes"]["ENTRY"] == [14, 86]
    assert len(client.get("/slots").json()) == 50

    reply = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2})
    assert reply.status_code == 201 and reply.json()["label"] == "S1"
    rid = reply.json()["reservation_id"]
    assert len(client.get(f"/reservations/{rid}/route").json()["steps"]) == 3
    assert client.post(f"/reservations/{rid}/arrive").json()["slot_status"] == "occupied"
    assert client.post(f"/reservations/{rid}/depart").json()["status"] == "completed"

    assert client.post("/reserve", json={"plate": "TN01"}).status_code == 400
    assert client.get("/reservations/999").status_code == 404
    assert client.post(f"/reservations/{rid}/cancel").json()["error"] == "invalid_state"
