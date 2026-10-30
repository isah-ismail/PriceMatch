from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert "version" in body


def test_health_reports_database_failure():
    class BrokenSession:
        def execute(self, *_):
            raise RuntimeError("boom")

        def close(self):
            pass

    def _broken():
        yield BrokenSession()

    app.dependency_overrides[get_db] = _broken
    try:
        r = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert set(r.json()["error"]) == {"code", "message", "details"}
