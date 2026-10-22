"""DB tests run against the plumbline-test Supabase project inside one transaction that is
always rolled back, so they leave nothing behind. RLS is exercised by switching to the
`authenticated` role with forged JWT claims, exactly as PostgREST does."""

import json
import os
import uuid

import psycopg
import pytest


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    with psycopg.connect(url) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


def as_admin(conn):
    conn.execute("reset role")


def as_user(conn, user_id):
    conn.execute("set local role authenticated")
    claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
    conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))


def make_org(conn, name="Org"):
    return conn.execute(
        "insert into organizations (name) values (%s) returning id", (name,)
    ).fetchone()[0]


def make_user(conn, org_id, role):
    uid = uuid.uuid4()
    conn.execute(
        "insert into auth.users (id, email, aud, role)"
        " values (%s, %s, 'authenticated', 'authenticated')",
        (uid, f"{uid}@test.local"),
    )
    conn.execute(
        "insert into profiles (user_id, org_id, display_name, role) values (%s, %s, %s, %s)",
        (uid, org_id, role, role),
    )
    return uid


def make_version(conn, org_id, created_by, private=False, status="submitted"):
    content_id = conn.execute(
        "insert into contents (org_id, title, channel, region, origin, created_by)"
        " values (%s, 'Post', 'instagram', 'IN', 'agency', %s) returning id",
        (org_id, created_by),
    ).fetchone()[0]
    return conn.execute(
        "insert into versions (org_id, content_id, n, text, private, status, created_by)"
        " values (%s, %s, 1, 'Hello', %s, %s, %s) returning id",
        (org_id, content_id, private, status, created_by),
    ).fetchone()[0]


def make_finding(conn, org_id, version_id):
    run_id = conn.execute(
        "insert into check_runs (org_id, version_id, report_json, rulebook_version)"
        " values (%s, %s, '{}', 'v1') returning id",
        (org_id, version_id),
    ).fetchone()[0]
    return conn.execute(
        "insert into findings (org_id, run_id, rule_id, category, severity, advisory, quote)"
        " values (%s, %s, 'TN-02', 'tone', 'minor', true, '!!!') returning id",
        (org_id, run_id),
    ).fetchone()[0]
