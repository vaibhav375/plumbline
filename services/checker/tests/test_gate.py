"""The publish gate: "go" only for an approved version with no open blocking finding and, when the tool
says what it will publish, exactly the approved text. The decision is pure, so most tests need no database."""

import pytest
from fastapi.testclient import TestClient

from plumbline import api, auth, connect
from plumbline.config import Settings

TEXT = "Shown to visibly reduce dark spots by 32% in 8 weeks*. Shop now."


def finding(fid, severity="blocking", advisory=False, rule="CL-01"):
    return {"id": fid, "severity": severity, "advisory": advisory, "rule_id": rule, "fact_id": None}


def snap(findings=(), decisions=(), status="approved", text=TEXT, report=True):
    rows = [
        {"id": f"rec-{f['id']}", "payload": {"group": "findings", "id": f["id"]}} for f in findings
    ]
    return {
        "version": {"id": "v1", "content_id": "c1", "n": 1, "text": text, "status": status},
        "report": {"findings": list(findings), "needs_human": []} if report else None,
        "findings": rows,
        "decisions": [
            {"finding_id": f"rec-{fid}", "action": action, "at": f"2026-10-28T10:0{i}:00Z"}
            for i, (fid, action) in enumerate(decisions)
        ],
        "approvals": [],
    }


def test_an_approved_version_with_nothing_blocking_goes():
    assert connect.decide(snap([finding("a", "minor", True)])) == ("go", [])
    assert connect.decide(snap([], status="published")) == ("go", [])


@pytest.mark.parametrize(
    "status", ["precheck", "submitted", "in_review", "changes_requested", "withdrawn", "recalled"]
)
def test_a_version_that_is_not_approved_never_goes(status):
    decision, reasons = connect.decide(snap([], status=status))
    assert decision == "not_yet" and "Not approved yet" in reasons[0]


def test_an_open_blocking_finding_stops_it_even_if_approved():
    decision, reasons = connect.decide(snap([finding("a"), finding("b", rule="CL-03")]))
    assert decision == "not_yet"
    assert reasons == ["2 blocking findings are open: CL-01, CL-03."]


def test_upheld_does_not_clear_a_blocking_finding_but_overruled_does():
    f = finding("a")
    assert connect.decide(snap([f], [("a", "uphold")]))[0] == "not_yet"
    assert connect.decide(snap([f], [("a", "escalate")]))[0] == "not_yet"
    assert connect.decide(snap([f], [("a", "overrule")])) == ("go", [])
    # The latest decision wins: overruled, then upheld again.
    assert connect.decide(snap([f], [("a", "overrule"), ("a", "uphold")]))[0] == "not_yet"


def test_advisory_findings_never_block():
    assert (
        connect.decide(snap([finding("a", "blocking", True), finding("b", "minor", False)]))[0]
        == "go"
    )


def test_a_version_with_no_saved_check_never_goes():
    decision, reasons = connect.decide(snap(report=False))
    assert decision == "not_yet" and any("No completed check" in r for r in reasons)


def test_the_text_hash_proves_it_is_the_approved_text():
    ok = connect.text_hash(TEXT)
    assert connect.decide(snap(), ok) == ("go", [])
    assert connect.decide(snap(), ok.upper()) == ("go", [])  # hex case doesn't matter
    assert connect.decide(snap(), f"  {TEXT}\n".strip() and connect.text_hash(f"  {TEXT}\n")) == (
        "go",
        [],
    )
    decision, reasons = connect.decide(snap(), connect.text_hash(TEXT + " Extra!"))
    assert decision == "not_yet" and "The text differs from the approved version." in reasons


def test_every_reason_is_given_not_just_the_first():
    decision, reasons = connect.decide(snap([finding("a")], status="submitted"), "0" * 64)
    assert decision == "not_yet" and len(reasons) == 3


# ---- the HTTP endpoints, with the database calls faked ----------------------------------------------


@pytest.fixture
def gate(monkeypatch):
    s = Settings(_env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="anon")
    monkeypatch.setattr(api, "settings", s)
    state = {"snaps": {}, "keys": {"plk_good": "org-A"}, "log": [], "latest": {}}
    monkeypatch.setattr(connect, "key_org", lambda s, k: state["keys"].get(k))
    monkeypatch.setattr(
        connect,
        "snapshot",
        lambda s, org, vid: state["snaps"].get((org, vid)),
    )
    monkeypatch.setattr(
        connect, "latest_version", lambda s, org, cid: state["latest"].get((org, cid))
    )
    monkeypatch.setattr(
        connect, "log_call", lambda s, org, vid, d, r: state["log"].append((org, vid, d, r))
    )
    c = TestClient(api.app)
    c.state = state
    return c


VID = "11111111-1111-1111-1111-111111111111"
CID = "22222222-2222-2222-2222-222222222222"
GOOD = {"Authorization": "Bearer plk_good"}


def test_the_gate_needs_a_valid_key(gate):
    assert gate.get(f"/v1/gate/versions/{VID}").status_code == 401
    assert (
        gate.get(
            f"/v1/gate/versions/{VID}", headers={"Authorization": "Bearer plk_bad"}
        ).status_code
        == 401
    )
    assert (
        gate.get(f"/v1/gate/versions/{VID}", headers={"Authorization": "Basic x"}).status_code
        == 401
    )
    assert gate.state["log"] == []


def test_go_and_not_yet_are_returned_and_logged(gate):
    gate.state["snaps"][("org-A", VID)] = snap()
    r = gate.get(f"/v1/gate/versions/{VID}", headers=GOOD)
    assert r.status_code == 200 and r.json()["decision"] == "go" and r.json()["reasons"] == []
    gate.state["snaps"][("org-A", VID)] = snap([finding("a")])
    r = gate.get(f"/v1/gate/versions/{VID}", headers=GOOD)
    assert r.json()["decision"] == "not_yet" and "CL-01" in r.json()["reasons"][0]
    assert r.json()["fix_url"].endswith(f"/review/{VID}")
    assert [d for _, _, d, _ in gate.state["log"]] == ["go", "not_yet"]


def test_another_orgs_version_is_a_404_not_a_hint(gate):
    gate.state["snaps"][("org-B", VID)] = snap()  # exists, but belongs to B
    r = gate.get(f"/v1/gate/versions/{VID}", headers=GOOD)
    assert r.status_code == 404 and "decision" not in r.json()
    assert gate.get("/v1/gate/versions/not-a-uuid", headers=GOOD).status_code == 404


def test_the_hash_is_checked_through_the_endpoint(gate):
    gate.state["snaps"][("org-A", VID)] = snap()
    h = connect.text_hash(TEXT)
    assert (
        gate.get(f"/v1/gate/versions/{VID}?text_sha256={h}", headers=GOOD).json()["decision"]
        == "go"
    )
    r = gate.get(f"/v1/gate/versions/{VID}?text_sha256={'0' * 64}", headers=GOOD)
    assert r.json()["decision"] == "not_yet"


def test_content_resolves_to_its_latest_version_in_the_keys_org(gate):
    gate.state["latest"][("org-A", CID)] = VID
    gate.state["snaps"][("org-A", VID)] = snap()
    r = gate.get(f"/v1/gate/contents/{CID}", headers=GOOD)
    assert r.json()["decision"] == "go" and r.json()["version_id"] == VID
    assert (
        gate.get(f"/v1/gate/contents/{'3' * 8}-3333-3333-3333-{'3' * 12}", headers=GOOD).status_code
        == 404
    )


def test_the_gate_is_off_without_the_narrow_role(monkeypatch):
    monkeypatch.setattr(
        api,
        "settings",
        Settings(_env_file=None, supabase_url="https://t.supabase.co", supabase_anon_key="a"),
    )
    r = TestClient(api.app).get(f"/v1/gate/versions/{VID}", headers=GOOD)
    assert r.status_code == 503 and r.json()["code"] == "not_enabled"


# ---- managing connections: brand owner only ---------------------------------------------------------


@pytest.fixture
def owner_client(monkeypatch, gate):
    from tests.test_api import token

    state = {"role": "brand_owner"}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-A", "role": state["role"]}
    )
    monkeypatch.setattr(
        auth,
        "_jwks",
        lambda _u: type(
            "J",
            (),
            {
                "get_signing_key_from_jwt": lambda self, t: type(
                    "K",
                    (),
                    {"key": __import__("tests.test_api", fromlist=["KEY"]).KEY.public_key()},
                )()
            },
        )(),
    )
    made = []
    monkeypatch.setattr(
        connect,
        "make_code",
        lambda s, org, uid: made.append(org) or ("ABCD-2345", "2026-10-28T10:15:00+00:00"),
    )
    monkeypatch.setattr(connect, "key_create", lambda s, org, uid, label: ("kid-1", "plk_new"))
    gate.state["role"] = state
    gate.state["made"] = made
    gate.bearer = {"Authorization": f"Bearer {token()}"}
    return gate


def test_only_the_brand_owner_can_make_codes_and_keys(owner_client):
    c = owner_client
    r = c.post("/v1/connect/link-codes", headers=c.bearer)
    assert r.status_code == 200 and r.json()["code"] == "ABCD-2345" and c.state["made"] == ["org-A"]
    assert (
        c.post("/v1/connect/gate-keys", headers=c.bearer, json={"label": "Buffer"}).json()["key"]
        == "plk_new"
    )
    c.state["role"]["role"] = "reviewer"
    assert c.post("/v1/connect/link-codes", headers=c.bearer).status_code == 403
    assert c.post("/v1/connect/gate-keys", headers=c.bearer, json={"label": "x"}).status_code == 403
    assert c.get("/v1/connect/overview", headers=c.bearer).status_code == 403
    assert c.post("/v1/connect/link-codes").status_code == 401
