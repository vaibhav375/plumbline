"""API tests. Tokens are real ES256 JWTs signed by a test key (the same algorithm Supabase uses);
only the JWKS lookup and the database reads are replaced."""

import json
import time

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
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def bearer(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(api, "db_ok", lambda s: True)
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["db"] is True
    assert set(body["providers"]) == {"groq", "gemini"} and isinstance(body["version"], str)


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
