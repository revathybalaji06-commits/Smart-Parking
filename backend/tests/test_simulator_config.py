"""The traffic setting can be tested without connecting to PostgreSQL."""

from app.simulator import traffic_is_enabled


def test_traffic_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv("SIMULATE_TRAFFIC", raising=False)
    assert traffic_is_enabled() is True


def test_traffic_can_be_disabled(monkeypatch):
    monkeypatch.setenv("SIMULATE_TRAFFIC", "0")
    assert traffic_is_enabled() is False
