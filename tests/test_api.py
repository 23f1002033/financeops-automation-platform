"""Smoke tests for the API surface."""
from __future__ import annotations

from fastapi.testclient import TestClient

from financeops.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_snapshot_endpoint():
    r = client.get("/kpis/snapshot?days=30")
    assert r.status_code == 200
    assert r.json()["revenue"] >= 0


def test_anomalies_endpoint_filter():
    r = client.get("/anomalies?severity=high&limit=10")
    assert r.status_code == 200
    for a in r.json():
        assert a["severity"] == "high"


def test_executive_summary_endpoint():
    r = client.get("/reports/executive-summary")
    assert r.status_code == 200
    assert "headline" in r.json()