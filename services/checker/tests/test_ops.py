import json
import logging

from fastapi.testclient import TestClient

from plumbline import api, ops
from plumbline.config import Settings

from .test_api import bearer, client, token  # noqa: F401  (client is a fixture)


def test_request_id_header_present(client):  # noqa: F811
    rid = client.get("/health").headers["X-Request-ID"]
    assert 8 <= len(rid) <= 64
    # A caller's id is kept when it is safe to echo, replaced when it isn't.
    assert (
        client.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
        == "abc-123"
    )
    assert (
        client.get("/health", headers={"X-Request-ID": "<script>"}).headers["X-Request-ID"]
        != "<script>"
    )


def test_errors_carry_the_request_id(client):  # noqa: F811
    r = client.post("/v1/checks", data={"text": "hi", "channel": "instagram", "region": "IN"})
    assert r.status_code == 401
    assert r.json()["request_id"] == r.headers["X-Request-ID"]


def test_unexpected_error_is_a_plain_500_with_a_reference(client, monkeypatch):  # noqa: F811
    def boom(_s):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(api, "db_ok", boom)
    r = TestClient(api.app, raise_server_exceptions=False).get("/health")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal" and "secret internals" not in body["message"]
    assert body["request_id"] == r.headers["X-Request-ID"] and body["request_id"] in body["message"]


def test_oversized_request_is_refused_before_reading(client):  # noqa: F811
    limit = api.cfg().max_upload_mb * 1024 * 1024
    r = client.post(
        "/v1/checks",
        headers=bearer(token()) | {"Content-Type": "text/plain"},
        content=b"x" * (limit + 64 * 1024 + 1),
    )
    assert r.status_code == 413
    assert r.json()["code"] == "too_large"


def test_checks_report_server_timing(client):  # noqa: F811
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Click here to shop!!!", "channel": "instagram", "region": "IN"},
    )
    assert r.status_code == 200
    timing = r.headers["Server-Timing"]
    for phase in ("auth", "check", "save", "total"):
        assert f"{phase};dur=" in timing


def test_one_structured_log_line_per_request_without_content(client, caplog):  # noqa: F811
    with caplog.at_level(logging.INFO, logger="plumbline.request"):
        r = client.post(
            "/v1/checks",
            headers=bearer(token()),
            data={"text": "Secret launch copy!!!", "channel": "instagram", "region": "IN"},
        )
    lines = [json.loads(m.getMessage()) for m in caplog.records if m.name == "plumbline.request"]
    assert len(lines) == 1
    line = lines[0]
    assert line["request_id"] == r.headers["X-Request-ID"]
    assert (line["method"], line["path"], line["status"]) == ("POST", "/v1/checks", 200)
    assert line["ms"] >= 0 and "check" in line["phases"]
    assert "Secret launch copy" not in json.dumps(line)


def test_rulebook_is_cached_per_org_and_role_and_cleared_by_import(monkeypatch, aurelle):
    # Its own settings: CI has no .env, and this test must not depend on one.
    monkeypatch.setattr(
        api,
        "settings",
        Settings(_env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="anon"),
    )
    calls = []
    monkeypatch.setattr(api.db, "load_org_context", lambda s, t, org: calls.append(org) or aurelle)
    user = lambda org, role: api.User(id="u", org_id=org, role=role, token="t")  # noqa: E731
    api.org_context(user("org-1", "creator"))
    api.org_context(user("org-1", "creator"))
    assert calls == ["org-1"]
    api.org_context(user("org-1", "compliance"))  # facts visible differ by role
    api.org_context(user("org-2", "creator"))
    assert calls == ["org-1", "org-1", "org-2"]
    ops.clear_cache()  # what a rule import does
    api.org_context(user("org-1", "creator"))
    assert len(calls) == 4


def test_startup_warms_the_slow_models_in_the_background(monkeypatch):
    import threading

    warmed = threading.Event()
    monkeypatch.setattr(api, "warm_up", warmed.set)
    with TestClient(api.app):  # runs the lifespan, as uvicorn does on boot
        assert warmed.wait(5)
