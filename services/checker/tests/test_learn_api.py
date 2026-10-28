"""Rule change endpoints: the database decides who may; its refusals become plain errors."""

import pytest
from fastapi.testclient import TestClient

from plumbline import api, auth, db
from plumbline.config import Settings
from tests.test_api import KEY, token


@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(
        api,
        "settings",
        Settings(_env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="a"),
    )
    role = {"v": "creator"}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-A", "role": role["v"]}
    )
    jwks = type(
        "J",
        (),
        {"get_signing_key_from_jwt": lambda self, t: type("K", (), {"key": KEY.public_key()})()},
    )()
    monkeypatch.setattr(auth, "_jwks", lambda _u: jwks)
    client = TestClient(api.app)
    client.headers["Authorization"] = f"Bearer {token()}"
    return client, role, monkeypatch


def test_a_database_refusal_is_a_plain_403_and_a_rule_state_conflict_a_409(c):
    client, role, mp = c

    def refuse(s, t, fn, args=None):
        raise db.RpcError(
            403 if args["p_rule"] == "TN-01" else 400,
            "not allowed"
            if args["p_rule"] == "TN-01"
            else "only an automatic graduation can be undone",
        )

    mp.setattr(db, "rpc", refuse)
    a = client.post("/v1/rules/TN-01/undo")
    assert a.status_code == 403 and "owner" in a.json()["message"]
    b = client.post("/v1/rules/TN-02/undo")
    assert b.status_code == 409 and "automatic" in b.json()["message"]


def test_changes_and_drafts_are_for_reviewer_roles_only(c):
    client, role, mp = c
    assert client.get("/v1/rules/changes").status_code == 403
    assert client.get("/v1/rules/TN-01/clarifications").status_code == 403
    role["v"] = "reviewer"
    mp.setattr(db, "rule_changes", lambda s, t, limit=50: [{"id": "x"}])
    mp.setattr(db, "pinned_rules", lambda s, t: ["TN-01"])
    assert client.get("/v1/rules/changes").json() == {"changes": [{"id": "x"}], "pinned": ["TN-01"]}
