"""Tests that call the real URLs."""
from fastapi.testclient import TestClient

from app.main import app


def test_reserve_and_availability(conn):
    client = TestClient(app)
    assert client.get("/availability").json()["lot"]["free"] == 50

    reply = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 2})
    assert reply.status_code == 201
    assert reply.json()["label"] == "S1"
    assert client.get("/availability").json()["lot"]["free"] == 49


def test_bad_request_is_400(conn):
    client = TestClient(app)
    reply = client.post("/reserve", json={"plate": "TN01"})
    assert reply.status_code == 400
    assert reply.json()["error"] == "invalid_request"


def test_lot_full_is_409(conn):
    conn.execute("UPDATE slots SET status = 'occupied'")
    client = TestClient(app)
    reply = client.post("/reserve", json={"plate": "TN01", "vehicle_class": 1})
    assert reply.status_code == 409
    assert reply.json()["error"] == "lot_full"
