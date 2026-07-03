"""REST liveness check (US2)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_landing_lists_mcp_surface():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "search_documents" in body
    assert "documents://all" in body
