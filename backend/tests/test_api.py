"""HTTP-level tests: status codes and JSON shapes from docs/api.md."""
import os

import pytest
from fastapi.testclient import TestClient

from app.db import get_conn
from app.main import app, get_db

URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture()
def client(conn):  # `conn` creates the clean schema first
    def override():
        c = get_conn(URL)
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_availability_shape(client):
    r = client.get("/availability")
    assert r.status_code == 200
    body = r.json()
    assert body["lot"] == {"free": 50, "max": 50}
    assert [c["class"] for c in body["classes"]] == [1, 2, 3, 4]


def test_slots_shape(client):
    r = client.get("/slots")
    assert r.status_code == 200 and len(r.json()) == 50
    assert set(r.json()[0]) == {"id", "label", "size_class", "status"}


def test_reserve_arrive_depart_flow(client):
    r = client.post("/reserve", json={"plate": "TN37AB1234", "vehicle_class": 2})
    assert r.status_code == 201
    rid = r.json()["reservation_id"]
    assert r.json()["label"] == "S1"
    assert client.get(f"/reservations/{rid}").json()["status"] == "active"
    assert client.post(f"/reservations/{rid}/arrive").json()["slot_status"] == "occupied"
    d = client.post(f"/reservations/{rid}/depart")
    assert d.status_code == 200 and d.json()["status"] == "completed"


def test_cancel(client):
    rid = client.post("/reserve", json={"plate": "A", "vehicle_class": 1}).json()["reservation_id"]
    assert client.post(f"/reservations/{rid}/cancel").json() == {
        "reservation_id": rid,
        "status": "cancelled",
    }


@pytest.mark.parametrize(
    "body",
    [{}, {"plate": "A"}, {"plate": "A", "vehicle_class": 9}, {"plate": "", "vehicle_class": 1},
     {"plate": "A", "vehicle_class": "x"}],
)
def test_bad_request_is_400_invalid_request(client, body):
    r = client.post("/reserve", json=body)
    assert r.status_code == 400 and r.json()["error"] == "invalid_request"


def test_lot_full_is_409(client, conn):
    conn.execute("UPDATE slots SET status='occupied'")
    r = client.post("/reserve", json={"plate": "A", "vehicle_class": 1})
    assert r.status_code == 409 and r.json()["error"] == "lot_full"


def test_unknown_reservation_is_404(client):
    r = client.post("/reservations/99999/arrive")
    assert r.status_code == 404 and r.json()["error"] == "not_found"


def test_invalid_state_is_409(client):
    rid = client.post("/reserve", json={"plate": "A", "vehicle_class": 1}).json()["reservation_id"]
    r = client.post(f"/reservations/{rid}/depart")
    assert r.status_code == 409 and r.json()["error"] == "invalid_state"


def test_cors_allows_react_dev_server(client):
    r = client.get("/availability", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
