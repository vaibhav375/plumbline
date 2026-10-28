"""API tests. Tokens are real ES256 JWTs signed by a test key (the same algorithm Supabase uses);
only the JWKS lookup and the database reads are replaced."""

import json
import time
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from plumbline import api, auth
from plumbline.config import Settings

KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())
ISS = "https://test.supabase.co/auth/v1"
USER_ID = "11111111-1111-1111-1111-111111111111"


def token(key=KEY, **claims) -> str:
    now = int(time.time())
    body = {
        "sub": USER_ID,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": ISS,
        "iat": now,
        "exp": now + 600,
    } | claims
    return jwt.encode(body, key, algorithm="ES256", headers={"kid": "test"})


class FakeJwks:
    def get_signing_key_from_jwt(self, _token):
        return type("K", (), {"key": KEY.public_key()})()


@pytest.fixture
def client(monkeypatch, aurelle):
    settings = Settings(
        _env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="anon"
    )
    monkeypatch.setattr(api, "settings", settings)
    monkeypatch.setattr(auth, "_jwks", lambda _url: FakeJwks())
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-1", "role": "creator"}
    )
    api.app.dependency_overrides[api.org_context] = lambda: aurelle
    saved: list[dict] = []

    class MemoryCache(dict):
        key = None

        def __init__(self, *_):
            super().__init__()

        def __setitem__(self, k, v):
            self.key = k

    def save_check(s, token, **kw):
        saved.append(kw)
        n = len(kw["report"]["findings"]) + len(kw["report"]["needs_human"])
        return (
            kw["content_id"] or "content-1",
            f"version-{len(saved)}",
            [f"rec-{len(saved)}-{i}" for i in range(n)],
        )

    monkeypatch.setattr(api.db, "ReportCache", MemoryCache)
    monkeypatch.setattr(api.db, "save_check", save_check)
    monkeypatch.setattr(api.db, "load_confidential_facts", lambda s, org: [])
    c = TestClient(api.app)
    c.saved = saved
    yield c
    api.app.dependency_overrides.clear()


def bearer(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(api, "db_ok", lambda s: True)
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["db"] is True
    assert set(body["providers"]) == {"groq", "gemini", "asi1"} and isinstance(body["version"], str)


def test_checks_requires_auth(client):
    r = client.post("/v1/checks", data={"text": "hi", "channel": "instagram", "region": "IN"})
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"


@pytest.mark.parametrize(
    "bad",
    [
        token(key=OTHER_KEY),  # wrong signature
        token(exp=int(time.time()) - 10),  # expired
        token(aud="anon"),  # wrong audience
        token(iss="https://evil.example/auth/v1"),
        "not-a-jwt",
    ],
)
def test_bad_tokens_rejected(client, bad):
    r = client.post(
        "/v1/checks", headers=bearer(bad), data={"text": "hi", "channel": "x", "region": "IN"}
    )
    assert r.status_code == 401


def test_hs256_token_rejected_even_with_known_secret(client):
    """Algorithm confusion: an HS256 token must never be accepted."""
    forged = jwt.encode(
        {"sub": USER_ID, "aud": "authenticated", "iss": ISS, "exp": int(time.time()) + 60},
        "anything",
        algorithm="HS256",
    )
    r = client.post(
        "/v1/checks", headers=bearer(forged), data={"text": "hi", "channel": "x", "region": "IN"}
    )
    assert r.status_code == 401


def test_checks_returns_findings_for_text(client, samples):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": samples["worked-example"]["text"], "channel": "instagram", "region": "IN"},
    )
    assert r.status_code == 200, r.text
    report = r.json()
    ids = {f["rule_id"] for f in report["findings"]}
    assert len(report["findings"]) >= 3 and "TN-02" in ids
    assert report["coverage"]["not_checked"]
    assert report["ms_code"] >= 0


def test_checks_accepts_file_upload(client):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"channel": "instagram", "region": "IN"},
        files={"file": ("post.txt", b"Click here to shop!!!", "text/plain")},
    )
    assert r.status_code == 200
    assert {"CTA-02", "TN-02"} <= {f["rule_id"] for f in r.json()["findings"]}


def test_empty_file_422_message(client):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"channel": "instagram", "region": "IN"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "empty"
    assert r.json()["message"].startswith("The file is empty.")


def test_user_without_profile_is_forbidden(client, monkeypatch):
    monkeypatch.setattr(auth, "fetch_profile", lambda s, t, uid: None)
    r = client.post(
        "/v1/checks", headers=bearer(token()), data={"text": "hi", "channel": "x", "region": "IN"}
    )
    assert r.status_code == 403


def test_jwks_fetch_uses_httpx_and_rejects_unknown_kid(monkeypatch):
    """The live run showed PyJWKClient's urllib fetch failing on certificates; keys now come via
    httpx. An unknown kid is refused after one refresh."""
    from jwt.algorithms import ECAlgorithm

    jwk = json.loads(ECAlgorithm.to_jwk(KEY.public_key())) | {"kid": "test", "alg": "ES256"}
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return httpx.Response(200, json={"keys": [jwk]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    jwks = auth.Jwks("https://test.supabase.co")
    assert jwks.get_signing_key_from_jwt(token()).key_id == "test"
    assert calls == ["https://test.supabase.co/auth/v1/.well-known/jwks.json"]
    bad = jwt.encode({"sub": "x"}, OTHER_KEY, algorithm="ES256", headers={"kid": "other"})
    with pytest.raises(jwt.InvalidKeyError):
        jwks.get_signing_key_from_jwt(bad)
    assert len(calls) == 1  # no refetch within a minute


def test_jwks_fetches_on_first_use_right_after_boot(monkeypatch):
    """CI caught this: monotonic time starts near 0 on a freshly booted machine, so a 'last
    fetched at 0.0' default looked recent and keys were never fetched."""
    from jwt.algorithms import ECAlgorithm

    jwk = json.loads(ECAlgorithm.to_jwk(KEY.public_key())) | {"kid": "test", "alg": "ES256"}
    monkeypatch.setattr(auth.time, "monotonic", lambda: 5.0)  # 5 s after boot
    monkeypatch.setattr(
        auth.httpx,
        "get",
        lambda url, timeout: httpx.Response(
            200, json={"keys": [jwk]}, request=httpx.Request("GET", url)
        ),
    )
    assert auth.Jwks("https://test.supabase.co").get_signing_key_from_jwt(token()).key_id == "test"


def test_check_is_saved_as_a_private_precheck(client):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Click here!!!", "channel": "instagram", "region": "IN"},
    )
    assert r.status_code == 200 and r.json()["version_id"] == "version-1"
    saved = client.saved[0]
    assert saved["private"] is True and saved["status"] == "precheck" and saved["cache_key"]
    assert saved["user_id"] == USER_ID and saved["org_id"] == "org-1"


def test_no_ai_keys_means_the_report_says_ai_did_not_run(client):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Click here to shop!", "channel": "instagram", "region": "IN"},
    )
    cov = r.json()["coverage"]
    assert cov["ai_status"] == "unavailable" and cov["ai_note"].startswith("AI checks did not run:")
    assert {f["rule_id"] for f in r.json()["findings"]} >= {"CTA-02"}  # code checks still ran


def test_content_you_cannot_see_is_404(client, monkeypatch):
    monkeypatch.setattr(api.db, "get_content", lambda s, t, cid: None)
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Hi", "channel": "x", "region": "IN", "content_id": "someone-elses"},
    )
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert (
        client.post("/v1/contents/someone-elses/submit", headers=bearer(token())).status_code == 404
    )


def test_submit_reruns_as_a_non_private_submission(client, monkeypatch):
    monkeypatch.setattr(
        api.db,
        "get_content",
        lambda s, t, cid: {"id": cid, "title": "Post", "channel": "instagram"},
    )
    monkeypatch.setattr(
        api.db,
        "latest_version",
        lambda s, t, cid: {
            "text": "Click here to shop!",
            "doc_json": None,
            "intent_json": {"channel": "instagram"},
        },
    )
    r = client.post("/v1/contents/c-9/submit", headers=bearer(token()))
    assert r.status_code == 200
    saved = client.saved[-1]
    assert (
        saved["private"] is False
        and saved["status"] == "submitted"
        and saved["content_id"] == "c-9"
    )


def test_missing_confidential_role_is_reported_not_hidden(client):
    """Without CHECKER_DATABASE_URL a creator's check can't see embargoed facts: say so."""
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Hello there.", "channel": "x", "region": "IN"},
    )
    assert api.CONFIDENTIAL_UNAVAILABLE in r.json()["coverage"]["not_checked"]


def test_apply_accepted_fixes_records_decisions_and_rechecks(client, monkeypatch, aurelle):
    from plumbline.models import Document

    text = "Meet the NEW Aurelle Vitamin-C serum!!! Click here to shop!"
    first = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": text, "channel": "instagram", "region": "IN"},
    ).json()
    report = first | {
        "findings": [f | {"record_id": f"rec-{i}"} for i, f in enumerate(first["findings"])]
    }
    term = next(f for f in report["findings"] if f["rule_id"] == "TM-007")
    decisions = []
    monkeypatch.setattr(
        api.db,
        "load_version",
        lambda s, t, vid: {
            "id": vid,
            "content_id": "content-1",
            "doc": Document(format="text", text=text, blocks=[], images=[]),
            "intent": {"channel": "instagram"},
            "report": report,
        },
    )
    monkeypatch.setattr(api.db, "record_decisions", lambda s, t, **kw: decisions.append(kw))
    r = client.post(
        f"/v1/versions/{first['version_id']}/apply",
        headers=bearer(token()),
        json={"accepted": [term["record_id"]], "edits": {}},
    )
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["previous_text"] == text
    assert client.saved[-1]["doc"]["text"].startswith(
        "Meet the NEW Aurelle Vitamin C Brightening Serum"
    )
    assert decisions[0]["accepted"] == [term["record_id"]]
    assert not any(f["rule_id"] == "TM-007" for f in new["findings"])
    assert new["content_id"] == "content-1"


def test_apply_on_someone_elses_version_is_404(client, monkeypatch):
    monkeypatch.setattr(api.db, "load_version", lambda s, t, vid: None)
    r = client.post(
        "/v1/versions/v-x/apply", headers=bearer(token()), json={"accepted": [], "edits": {}}
    )
    assert r.status_code == 404


def test_blocking_findings_cannot_be_dismissed(client, monkeypatch):
    monkeypatch.setattr(
        api.db, "get_finding", lambda s, t, rid: {"id": rid, "severity": "blocking"}
    )
    r = client.post(
        "/v1/findings/f-1/decisions",
        headers=bearer(token()),
        json={"action": "dismiss", "reason": "fine"},
    )
    assert r.status_code == 409 and "blocking" in r.json()["message"].lower()


def test_dismiss_needs_a_reason_and_is_recorded(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api.db, "get_finding", lambda s, t, rid: {"id": rid, "severity": "minor"})
    monkeypatch.setattr(api.db, "insert_decision", lambda s, t, **kw: calls.append(kw))
    assert (
        client.post(
            "/v1/findings/f-1/decisions",
            headers=bearer(token()),
            json={"action": "dismiss", "reason": "  "},
        ).status_code
        == 422
    )
    r = client.post(
        "/v1/findings/f-1/decisions",
        headers=bearer(token()),
        json={"action": "dismiss", "reason": "Intentional brand style."},
    )
    assert (
        r.status_code == 200 and calls[0]["action"] == "dismiss" and calls[0]["finding_id"] == "f-1"
    )


def test_report_returns_the_exact_text_it_checked(client):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"text": "Shop\r\nnow\u00a0please.", "channel": "x", "region": "IN"},
    )
    assert r.json()["checked_text"] == "Shop\nnow please."


# ---- review workflow (Task 16) ---------------------------------------------------------------


def _claim_report():
    from plumbline.models import CheckReport, Coverage, Finding

    claim = Finding(
        id="FACT-014@10",
        category="claim",
        severity="blocking",
        advisory=False,
        rule_id="CL-01",
        fact_id="FACT-014",
        quote="60% in 2 weeks",
        span=None,
        image_id=None,
        explanation="x",
        basis_excerpt="b",
        method="code",
        claim_status="contradicted",
        record_id="r1",
    )
    cov = Coverage(
        rules_run=[],
        rules_advisory=[],
        rules_not_run={},
        not_checked=["x"],
        ai_status="ok",
        ai_note=None,
    )
    return CheckReport(
        run_id="run", version_id="v1", findings=[claim], coverage=cov, ms_code=1, ms_total=1
    )


@pytest.fixture
def review_db(client, monkeypatch):
    state = {"status": "submitted", "decisions": [], "approvals": [], "role": "reviewer"}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-1", "role": state["role"]}
    )
    monkeypatch.setattr(
        api.db,
        "load_review",
        lambda s, t, vid: {
            "version": {
                "id": vid,
                "content_id": "c1",
                "n": 1,
                "text": "60% in 2 weeks",
                "status": state["status"],
                "created_by": "creator-1",
                "created_at": "2026-10-23T10:00:00",
            },
            "content": {"id": "c1", "title": "Post"},
            "report": _claim_report().model_dump(mode="json"),
            "decisions": list(state["decisions"]),
            "approvals": list(state["approvals"]),
            "comments": [],
            "names": {"creator-1": "Creator Asha"},
        },
    )
    tick = iter(range(100))
    monkeypatch.setattr(
        api.db,
        "insert_decision",
        lambda s, t, **kw: state["decisions"].append(
            {
                "finding_id": kw["finding_id"],
                "actor": kw["user_id"],
                "action": kw["action"],
                "reason": kw["reason"],
                "at": f"2026-10-23T11:{next(tick):02d}",
            }
        ),
    )

    def add_approval(s, t, **kw):
        if kw["stage"] == "second" and any(
            a["stage"] == "first" and a["actor"] == kw["user_id"] for a in state["approvals"]
        ):
            raise api.db.SecondApproverError()
        state["approvals"].append(
            {
                "actor": kw["user_id"],
                "stage": kw["stage"],
                "outcome": kw["outcome"],
                "reason": kw["reason"],
                "at": f"2026-10-23T12:{next(tick):02d}",
            }
        )

    monkeypatch.setattr(api.db, "add_approval", add_approval)
    monkeypatch.setattr(api.db, "set_status", lambda s, t, vid, status: state.update(status=status))
    return state


def test_creators_cannot_open_the_queue(client, review_db):
    review_db["role"] = "creator"
    assert client.get("/v1/review/queue", headers=bearer(token())).status_code == 403


def test_claim_needs_compliance_and_decisions_before_approval(client, review_db):
    h = bearer(token())
    detail = client.get("/v1/review/v1", headers=h).json()
    assert detail["state"]["required"] == ["first", "compliance"] and detail["can_decide"] == []
    r = client.post(
        "/v1/review/v1/decisions",
        headers=h,
        json={"record_id": "r1", "action": "uphold", "reason": "x"},
    )
    assert (
        r.status_code == 403 and "Compliance" in r.json()["message"]
    )  # a reviewer can't decide a claim
    review_db["role"] = "compliance"
    r = client.post(
        "/v1/versions/v1/approve", headers=h, json={"stage": "first", "outcome": "approve"}
    )
    assert r.status_code == 409 and r.json()["code"] == "undecided"
    r = client.post(
        "/v1/review/v1/decisions",
        headers=h,
        json={"record_id": "r1", "action": "uphold", "reason": "Use AW-014b before publishing."},
    )
    assert r.status_code == 200 and review_db["status"] == "in_review"
    for stage in ("first", "compliance"):
        assert (
            client.post(
                "/v1/versions/v1/approve", headers=h, json={"stage": stage, "outcome": "approve"}
            ).status_code
            == 200
        )
    assert review_db["status"] == "approved"
    timeline = client.get("/v1/review/v1", headers=h).json()["timeline"]
    assert [e["what"] for e in timeline] == [
        "submitted for review",
        "upheld FACT-014",
        "approved the first stage",
        "approved the compliance stage",
    ]


def test_overruled_blocking_needs_a_different_second_approver(client, review_db):
    h = bearer(token())
    review_db["role"] = "compliance"
    client.post(
        "/v1/review/v1/decisions",
        headers=h,
        json={"record_id": "r1", "action": "overrule", "reason": "Study is new."},
    )
    assert client.get("/v1/review/v1", headers=h).json()["state"]["required"] == [
        "first",
        "compliance",
        "second",
    ]
    for stage in ("first", "compliance"):
        client.post(
            "/v1/versions/v1/approve", headers=h, json={"stage": stage, "outcome": "approve"}
        )
    assert (
        "second" not in client.get("/v1/review/v1", headers=h).json()["can_approve"]
    )  # same person
    r = client.post(
        "/v1/versions/v1/approve", headers=h, json={"stage": "second", "outcome": "approve"}
    )
    assert (
        r.status_code == 409
        and r.json()["message"] == "A second approval must come from a different person."
    )
    assert review_db["status"] != "approved"


def test_request_changes_needs_a_reason_and_sets_the_status(client, review_db):
    h = bearer(token())
    assert (
        client.post(
            "/v1/versions/v1/approve",
            headers=h,
            json={"stage": "first", "outcome": "request_changes"},
        ).status_code
        == 422
    )
    client.post(
        "/v1/versions/v1/approve",
        headers=h,
        json={
            "stage": "first",
            "outcome": "request_changes",
            "reason": "Use the approved wording.",
        },
    )
    assert review_db["status"] == "changes_requested"


def test_writer_escalates_blocking_but_cannot_dismiss_it(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        api.db, "get_finding", lambda s, t, rid: {"id": rid, "severity": "blocking"}
    )
    monkeypatch.setattr(api.db, "insert_decision", lambda s, t, **kw: calls.append(kw))
    h = bearer(token())
    assert (
        client.post(
            "/v1/findings/f/decisions", headers=h, json={"action": "dismiss", "reason": "x"}
        ).status_code
        == 409
    )
    r = client.post(
        "/v1/findings/f/decisions",
        headers=h,
        json={"action": "escalate", "reason": "No approved wording."},
    )
    assert r.status_code == 200 and calls[0]["action"] == "escalate"


def _audit_chain(monkeypatch, role):
    chain = json.loads((Path(__file__).parent / "fixtures" / "audit_chain.json").read_text())
    monkeypatch.setattr(auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-1", "role": role})
    monkeypatch.setattr(api.db, "audit_events", lambda s, t: (chain, {chain[0]["actor"]: "Asha"}))
    return chain


def test_auditor_verifies_the_chain_and_sees_newest_first(client, monkeypatch):
    chain = _audit_chain(monkeypatch, "auditor")
    r = client.get("/v1/audit/verify", headers=bearer(token()))
    assert r.status_code == 200
    body = r.json()
    assert (body["scope"], body["valid"], body["length"], body["broken_at"]) == (
        "org",
        True,
        3,
        None,
    )
    assert [e["id"] for e in body["recent"]] == [c["id"] for c in reversed(chain)]
    assert body["recent"][-1]["what"] == "saved version 1"


def test_audit_export_is_a_csv_download(client, monkeypatch):
    _audit_chain(monkeypatch, "compliance")
    r = client.get("/v1/audit/export.csv", headers=bearer(token()))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "at,actor,kind,entity,entity_id,prev_hash,hash,payload"


def test_creators_see_their_own_events_but_cannot_verify_or_export(client, monkeypatch):
    # Spec §4.5: creators view the audit log for their own work. RLS returns only those events,
    # and a chain with gaps can't be verified, so `valid` is null rather than a false alarm.
    _audit_chain(monkeypatch, "creator")
    body = client.get("/v1/audit/verify", headers=bearer(token())).json()
    assert (body["scope"], body["valid"], len(body["recent"])) == ("mine", None, 3)
    assert client.get("/v1/audit/export.csv", headers=bearer(token())).status_code == 403


BANNER = (Path(__file__).parent / "fixtures" / "banner_v1.png").read_bytes()


def _check_banner(client, **form):
    r = client.post(
        "/v1/checks",
        headers=bearer(token()),
        data={"channel": "instagram", "region": "IN", **form},
        files={"file": ("banner_v1.png", BANNER, "image/png")},
    )
    assert r.status_code == 200
    return {f["rule_id"]: f for f in r.json()["findings"]}


def test_image_upload_without_alt_text_asks_for_it(client):
    found = _check_banner(client)
    assert "can't see this image" in found["A11Y-ALT"]["explanation"]
    contrast = found["A11Y-CONTRAST"]
    assert "1.96:1" in contrast["explanation"]
    assert contrast["tier"] == "mandatory" and contrast["category"] == "accessibility"
    assert len(contrast["bbox"]) == 4


def test_image_upload_with_alt_text_or_decorative_has_no_alt_finding(client):
    assert "A11Y-ALT" not in _check_banner(client, alt_text="Glow in 2 weeks, Aurelle")
    assert "A11Y-ALT" not in _check_banner(client, decorative="true")


def test_cors_allows_the_app_domains_and_nothing_else(client):
    def allowed(origin: str) -> bool:
        r = client.options(
            "/v1/checks",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        return r.headers.get("access-control-allow-origin") == origin

    assert allowed("https://getplumbline.xyz") and allowed("https://www.getplumbline.xyz")
    assert allowed("https://plumbline-git-redesign-3-pes1ug23cs665s-projects.vercel.app")
    assert not allowed("https://getplumbline.xyz.evil.com")
    assert not allowed("https://notgetplumbline.xyz")


def test_cors_allows_delete_for_revoking_links_and_keys(client):
    r = client.options(
        "/v1/connect/gate-keys/x",
        headers={"Origin": "https://getplumbline.xyz", "Access-Control-Request-Method": "DELETE"},
    )
    assert r.status_code == 200 and "DELETE" in r.headers["access-control-allow-methods"]
