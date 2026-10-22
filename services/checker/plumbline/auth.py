"""Supabase JWT verification. This project signs access tokens with ES256 and publishes the public
key as JWKS, so tokens are checked against that key; symmetric algorithms are never accepted."""

import time
from functools import lru_cache

import httpx
import jwt
from fastapi import Request
from pydantic import BaseModel

from plumbline.config import Settings
from plumbline.db import fetch_profile

ALGORITHMS = ["ES256", "RS256"]


class User(BaseModel):
    id: str
    org_id: str
    role: str
    token: str


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


class Jwks:
    """Public signing keys, fetched with httpx (its own CA bundle; PyJWKClient's urllib fetch
    fails where the system has no certificate store). Refreshed hourly for key rotation, and on
    an unknown kid at most once a minute so garbage tokens can't hammer Supabase."""

    def __init__(self, url: str):
        self.url = f"{url}/auth/v1/.well-known/jwks.json"
        self.keys: dict[str, jwt.PyJWK] = {}
        # None, not 0.0: monotonic time counts from boot, so right after a boot "0.0" looks recent.
        self.fetched: float | None = None

    def _refresh(self) -> None:
        r = httpx.get(self.url, timeout=5)
        r.raise_for_status()
        self.keys = {k.key_id: k for k in jwt.PyJWKSet.from_dict(r.json()).keys}
        self.fetched = time.monotonic()

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        kid = jwt.get_unverified_header(token).get("kid")
        age = None if self.fetched is None else time.monotonic() - self.fetched
        if age is None or age > 3600 or (kid not in self.keys and age > 60):
            self._refresh()
        if kid not in self.keys:
            raise jwt.InvalidKeyError("Unknown signing key")
        return self.keys[kid]


@lru_cache
def _jwks(supabase_url: str) -> Jwks:
    return Jwks(supabase_url)


def verify_token(token: str, s: Settings) -> dict:
    url = s.supabase_url.rstrip("/")
    key = _jwks(url).get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        key,
        algorithms=ALGORITHMS,
        audience="authenticated",
        issuer=f"{url}/auth/v1",
        options={"require": ["exp", "sub", "aud", "iss"]},
    )


def current_user(request: Request, s: Settings) -> User:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Sign in to run a check.")
    token = header[7:].strip()
    try:
        claims = verify_token(token, s)
    except jwt.PyJWTError:
        raise ApiError(401, "unauthorized", "Your session has expired. Sign in again.") from None
    except httpx.HTTPError:
        raise ApiError(
            503, "auth_unavailable", "Sign-in can't be checked right now. Try again shortly."
        ) from None
    try:
        profile = fetch_profile(s, token, claims["sub"])
    except httpx.HTTPError:
        raise ApiError(
            503, "db_unavailable", "The database is not reachable. Try again shortly."
        ) from None
    if not profile:
        raise ApiError(403, "no_profile", "This account isn't set up for any organisation yet.")
    return User(id=claims["sub"], org_id=profile["org_id"], role=profile["role"], token=token)
