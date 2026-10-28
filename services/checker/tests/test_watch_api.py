"""Watch endpoints: who may scan, resolve and register pages. Database calls are faked."""

import pytest
from fastapi.testclient import TestClient

from plumbline import api, auth, watch
from plumbline.config import Settings
from tests.test_api import KEY, token

TID = "11111111-1111-1111-1111-111111111111"
VID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def w(monkeypatch):
    monkeypatch.setattr(
        api,
        "settings",
        Settings(_env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="a"),
    )
    state = {"role": "reviewer", "resolved": [], "set": [], "scans": 0}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-A", "role": state["role"]}
    )
    jwks = type(
        "J",
        (),
        {"get_signing_key_from_jwt": lambda self, t: type("K", (), {"key": KEY.public_key()})()},
    )()
    monkeypatch.setattr(auth, "_jwks", lambda _u: jwks)
    me = "11111111-1111-1111-1111-111111111111"  # the id token() signs
    live = [
        {"version_id": VID, "title": "Mine", "n": 1, "owner": me, "owner_name": "Me"},
        {
            "version_id": "other",
            "title": "Theirs",
            "n": 1,
            "owner": "someone",
            "owner_name": "Else",
        },
    ]
    tasks = [
        {"id": TID, "owner": me, "title": "Mine"},
        {"id": "33333333-3333-3333-3333-333333333333", "owner": "someone", "title": "Theirs"},
    ]

    def scan(s, org, today):
        state["scans"] += 1
        return {"posts": 2, "needing_attention": 0, "new_tasks": 0}

    monkeypatch.setattr(watch, "scan", scan)
    monkeypatch.setattr(watch, "live", lambda s, org: live)
    monkeypatch.setattr(
        watch,
        "tasks",
        lambda s, org, status="open", owner=None: [t for t in tasks if owner in (None, t["owner"])],
    )
    monkeypatch.setattr(watch, "urls", lambda s, org: [])
    monkeypatch.setattr(
        watch,
        "resolve_task",
        lambda s, org, tid, by, st, note: state["resolved"].append((tid, st, note)) or 1,
    )
    monkeypatch.setattr(watch, "set_url", lambda *a: state["set"].append(a) or 1)
    monkeypatch.setattr(
        watch,
        "check_registered_url",
        lambda s, org, vid: {"status": "ok", "checked": 1, "missing": []},
    )

    def public_only(url, resolve=None):
        if "internal" in url:
            raise watch.UnsafeUrl("That address isn't a public website.")

    monkeypatch.setattr(watch, "check_url_is_public", public_only)
    c = TestClient(api.app)
    c.state, c.bearer = state, {"Authorization": f"Bearer {token()}"}
    return c


def test_reviewers_see_everything_and_the_scan_runs_on_open(w):
    r = w.get("/v1/watch/overview", headers=w.bearer).json()
    assert r["everyone"] and len(r["tasks"]) == 2 and len(r["posts"]) == 2 and w.state["scans"] == 1


def test_a_writer_sees_only_their_own_and_triggers_no_scan(w):
    w.state["role"] = "creator"
    r = w.get("/v1/watch/overview", headers=w.bearer).json()
    assert not r["everyone"] and [t["title"] for t in r["tasks"]] == ["Mine"]
    assert [p["title"] for p in r["posts"]] == ["Mine"] and w.state["scans"] == 0
    assert w.post("/v1/watch/scan", headers=w.bearer).status_code == 403


def test_dismissing_needs_a_reason_and_a_writer_can_only_act_on_their_own(w):
    w.state["role"] = "creator"
    assert (
        w.post(
            f"/v1/watch/tasks/{TID}/resolve", headers=w.bearer, json={"status": "dismissed"}
        ).status_code
        == 422
    )
    ok = w.post(
        f"/v1/watch/tasks/{TID}/resolve",
        headers=w.bearer,
        json={"status": "done", "note": "updated"},
    )
    assert ok.status_code == 200 and w.state["resolved"] == [(TID, "done", "updated")]
    theirs = "33333333-3333-3333-3333-333333333333"
    assert (
        w.post(
            f"/v1/watch/tasks/{theirs}/resolve", headers=w.bearer, json={"status": "done"}
        ).status_code
        == 404
    )
    assert (
        w.post(
            f"/v1/watch/tasks/{TID}/resolve", headers=w.bearer, json={"status": "weird"}
        ).status_code
        == 422
    )
    w.state["role"] = "reviewer"
    assert (
        w.post(
            f"/v1/watch/tasks/{theirs}/resolve",
            headers=w.bearer,
            json={"status": "dismissed", "note": "n/a"},
        ).status_code
        == 200
    )


def test_registering_a_page_checks_ownership_and_refuses_internal_addresses(w):
    w.state["role"] = "creator"
    good = w.post(
        "/v1/watch/urls",
        headers=w.bearer,
        json={"version_id": VID, "url": "https://shop.example/serum"},
    )
    assert good.status_code == 200 and good.json()["status"] == "ok" and w.state["set"]
    not_mine = w.post(
        "/v1/watch/urls",
        headers=w.bearer,
        json={"version_id": "other", "url": "https://shop.example/x"},
    )
    assert not_mine.status_code == 404
    bad = w.post(
        "/v1/watch/urls",
        headers=w.bearer,
        json={"version_id": VID, "url": "http://internal.local/"},
    )
    assert bad.status_code == 422 and bad.json()["code"] == "unsafe_url"
    assert w.post(f"/v1/watch/urls/{VID}/check", headers=w.bearer).json()["status"] == "ok"
    assert w.post("/v1/watch/urls/other/check", headers=w.bearer).status_code == 404


def test_the_watch_needs_a_sign_in(w):
    assert w.get("/v1/watch/overview").status_code == 401
