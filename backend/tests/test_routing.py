"""Tests for the map, routes and pretend traffic."""
import pytest
from fastapi.testclient import TestClient

from app.layout import EDGES, NODES
from app.main import app
from app.reservations import arrive, reserve
from app.routing import build_route, road_start_for, shortest_path
from app.simulator import start_with_cars, tick


def count_occupied(conn):
    return conn.execute("SELECT count(*) AS n FROM slots WHERE status = 'occupied'").fetchone()["n"]


def test_every_slot_has_a_route_from_the_gate_to_its_bay(conn):
    for slot in conn.execute("SELECT * FROM slots").fetchall():
        route = build_route(slot)
        assert route["points"][0] == NODES["ENTRY"]
        assert route["points"][-1] == pytest.approx(
            (slot["x"] + slot["width"] / 2, slot["y"] + slot["height"] / 2)
        )
        assert route["steps"][-1]["text"].endswith("You have arrived.")


def test_routes_only_follow_the_one_way_roads(conn):
    for slot in conn.execute("SELECT * FROM slots").fetchall():
        path = shortest_path("ENTRY", road_start_for((slot["access_x"], slot["access_y"])))
        for a, b in zip(path, path[1:]):
            assert (a, b) in EDGES  # never against the arrows


def test_directions_to_a_bay_on_the_left_road(conn):
    slot = conn.execute("SELECT * FROM slots WHERE label = 'C1'").fetchone()
    steps = [s["text"] for s in build_route(slot)["steps"]]
    assert steps == [
        "Enter through the entry gate and drive straight for 45 m.",
        "Turn left into bay C1. You have arrived.",
    ]


def test_directions_to_a_bay_on_the_top_row(conn):
    slot = conn.execute("SELECT * FROM slots WHERE label = 'S1'").fetchone()
    steps = [s["text"] for s in build_route(slot)["steps"]]
    assert steps == [
        "Enter through the entry gate and drive straight for 74 m.",
        "Turn right and drive 25 m.",
        "Turn right into bay S1. You have arrived.",
    ]


def test_route_api(conn):
    client = TestClient(app)
    r = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2}).json()
    route = client.get(f"/reservations/{r['reservation_id']}/route")
    assert route.status_code == 200
    assert route.json()["length_m"] > 0


def test_route_needs_an_active_reservation(conn):
    client = TestClient(app)
    assert client.get("/reservations/999/route").status_code == 404
    r = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2}).json()
    client.post(f"/reservations/{r['reservation_id']}/cancel")
    assert client.get(f"/reservations/{r['reservation_id']}/route").status_code == 409


def test_layout_and_slots_api(conn):
    client = TestClient(app)
    layout = client.get("/layout").json()
    assert "ENTRY" in layout["nodes"] and len(layout["edges"]) == 9
    assert {"x", "y", "width", "height"} <= set(client.get("/slots").json()[0])


def test_pretend_traffic_never_touches_app_reservations(conn):
    mine = reserve(conn, "TN01", 2)
    parked = reserve(conn, "TN02", 2)
    arrive(conn, parked["reservation_id"])
    for _ in range(100):
        tick(conn)
    status = lambda slot_id: conn.execute("SELECT status FROM slots WHERE id = %s", (slot_id,)).fetchone()["status"]
    assert status(mine["slot_id"]) == "reserved"
    assert status(parked["slot_id"]) == "occupied"


def test_pretend_traffic_keeps_the_lot_about_40_percent_full(conn):
    start_with_cars(conn)
    assert count_occupied(conn) in (19, 20)  # 40% of 50 slots
