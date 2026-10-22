"""Tests for the map, routes and simulated traffic."""
import pytest
from fastapi.testclient import TestClient

from app import layout
from app.main import app
from app.reservations import arrive, reserve
from app.routing import build_route, edge_containing
from app.simulator import tick, warm_up


def test_every_slot_has_a_route_that_starts_at_the_gate_and_ends_in_its_bay(conn):
    slots = conn.execute("SELECT * FROM slots").fetchall()
    assert len(slots) == 50
    gate = layout.NODES["ENTRY"]
    for slot in slots:
        route = build_route(slot)
        first, last = route["points"][0], route["points"][-1]
        assert (first["x"], first["y"]) == gate
        # the last point is the middle of the bay
        assert last["x"] == pytest.approx(slot["x"] + slot["width"] / 2, abs=0.01)
        assert last["y"] == pytest.approx(slot["y"] + slot["height"] / 2, abs=0.01)
        assert route["steps"][-1]["text"].endswith("You have arrived.")


def test_routes_only_follow_one_way_roads(conn):
    """Every straight piece of a route must lie on a road, going the allowed way."""
    for slot in conn.execute("SELECT * FROM slots").fetchall():
        points = [(p["x"], p["y"]) for p in build_route(slot)["points"]]
        for a, b in zip(points[:-2], points[1:-1]):  # leave out the final step into the bay
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            start, end = edge_containing(mid)
            direction_ok = (layout.NODES[end][0] - layout.NODES[start][0]) * (b[0] - a[0]) \
                + (layout.NODES[end][1] - layout.NODES[start][1]) * (b[1] - a[1]) > 0
            assert direction_ok, (slot["label"], a, b)


def test_first_slot_directions(conn):
    slot = conn.execute("SELECT * FROM slots WHERE label = 'C1'").fetchone()
    steps = [s["text"] for s in build_route(slot)["steps"]]
    assert steps[0].startswith("Enter through the entry gate")
    assert "bay C1 is on your left" in steps[0]  # Row 1 is on the west side of the left road


def test_route_api(conn):
    client = TestClient(app)
    r = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2}).json()
    route = client.get(f"/reservations/{r['reservation_id']}/route")
    assert route.status_code == 200
    assert route.json()["slot"]["label"] == r["label"]
    assert route.json()["length_m"] > 0


def test_route_needs_an_active_reservation(conn):
    client = TestClient(app)
    assert client.get("/reservations/999/route").status_code == 404
    r = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2}).json()
    client.post(f"/reservations/{r['reservation_id']}/cancel")
    assert client.get(f"/reservations/{r['reservation_id']}/route").status_code == 409


def test_layout_and_slots_api(conn):
    client = TestClient(app)
    data = client.get("/layout").json()
    assert data["gates"]["entry"] and data["gates"]["exit"] and len(data["edges"]) == 9
    first = client.get("/slots").json()[0]
    assert {"x", "y", "width", "height", "row_name"} <= set(first)


def test_simulator_never_touches_app_reservations(conn):
    mine = reserve(conn, "TN01", 2)
    arrived = reserve(conn, "TN02", 2)
    arrive(conn, arrived["reservation_id"])
    for _ in range(300):
        tick(conn)
    status = lambda slot_id: conn.execute("SELECT status FROM slots WHERE id = %s", (slot_id,)).fetchone()["status"]
    assert status(mine["slot_id"]) == "reserved"
    assert status(arrived["slot_id"]) == "occupied"


def test_simulator_keeps_the_lot_partly_full(conn):
    for _ in range(300):
        tick(conn)
    occupied = conn.execute("SELECT count(*) AS n FROM slots WHERE status = 'occupied'").fetchone()["n"]
    assert 10 <= occupied <= 30  # around 40% of 50


def test_warm_up_puts_cars_in_an_empty_lot(conn):
    warm_up(conn)
    occupied = conn.execute("SELECT count(*) AS n FROM slots WHERE status = 'occupied'").fetchone()["n"]
    assert occupied >= 18
