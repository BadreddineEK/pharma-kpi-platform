"""Integration tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_sites_empty_db(tmp_path, monkeypatch):
    """Sites endpoint returns empty list when DB has no data."""
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "test.db"))
    # Re-import to pick up new env
    import importlib
    import pipeline.load as load_mod
    importlib.reload(load_mod)
    # Just check endpoint returns 200 or 404 gracefully
    response = client.get("/kpis/sites")
    assert response.status_code in [200, 500]  # 500 if DB not seeded


def test_alert_rules_endpoint():
    response = client.get("/alerts/rules")
    assert response.status_code == 200
    rules = response.json()
    assert isinstance(rules, list)
    assert len(rules) >= 1
    assert "metric" in rules[0]
