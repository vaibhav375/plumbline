"""The claim watch tables (migration 0014): reached only through the narrow checker role, scoped to one org."""

import json

import psycopg
import pytest

from .conftest import as_user, make_org, make_user, make_version

pytestmark = pytest.mark.db


def checker(db):
    db.execute("set local role plumbline_checker")


def report(db, version_id, claims):
    db.execute(
        "insert into check_runs (org_id, version_id, report_json, rulebook_version)"
        " select org_id, id, %s::jsonb, 'v1' from versions where id = %s",
        (json.dumps({"findings": [], "claims_used": claims}), version_id),
    )


def test_live_lists_only_this_orgs_approved_posts_with_their_claims(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua, ub = make_user(db, a, "creator"), make_user(db, b, "creator")
    live = make_version(db, a, ua, status="approved")
    make_version(db, a, ua, status="submitted")
    make_version(db, a, ua, private=True, status="precheck")
    other = make_version(db, b, ub, status="approved")
    report(db, live, [{"fact_id": "FACT-014", "quote": "q", "digest": "d"}])
    report(db, other, [])
    checker(db)
    rows = db.execute("select public.watch_live(%s)", (a,)).fetchone()[0]
    assert [r["version_id"] for r in rows] == [str(live)]
    assert rows[0]["claims_used"][0]["fact_id"] == "FACT-014" and rows[0]["owner"] == str(ua)


def test_a_post_with_no_saved_claims_still_lists_with_an_empty_set(db):
    a = make_org(db)
    u = make_user(db, a, "creator")
    make_version(db, a, u, status="approved")
    checker(db)
    assert db.execute("select public.watch_live(%s)", (a,)).fetchone()[0][0]["claims_used"] == []


def add(db, org, version, content, reason="expired", fact="FACT-014", owner=None):
    return db.execute(
        "select public.watch_task_add(%s, %s, %s, %s, %s, 'detail', null, %s)",
        (org, version, content, fact, reason, owner),
    ).fetchone()[0]


def content_of(db, version):
    return db.execute("select content_id from versions where id = %s", (version,)).fetchone()[0]


def test_an_open_task_is_never_duplicated_but_a_resolved_one_can_reopen(db):
    a = make_org(db)
    u = make_user(db, a, "creator")
    v = make_version(db, a, u, status="approved")
    c = content_of(db, v)
    checker(db)
    assert add(db, a, v, c) is True
    assert add(db, a, v, c) is False  # same post, fact and reason, still open
    assert add(db, a, v, c, reason="changed") is True  # a different reason is a different task
    assert add(db, a, v, c, fact=None, reason="drift") is True
    assert add(db, a, v, c, fact=None, reason="drift") is False
    task = db.execute("select public.watch_tasks_list(%s)", (a,)).fetchone()[0][0]
    assert (
        db.execute(
            "select public.watch_task_resolve(%s, %s, %s, 'done', 'updated')", (a, task["id"], u)
        ).fetchone()[0]
        == 1
    )
    assert (
        db.execute(
            "select public.watch_task_resolve(%s, %s, %s, 'done', 'again')", (a, task["id"], u)
        ).fetchone()[0]
        == 0
    )
    assert len(db.execute("select public.watch_tasks_list(%s)", (a,)).fetchone()[0]) == 2
    assert len(db.execute("select public.watch_tasks_list(%s, 'all')", (a,)).fetchone()[0]) == 3
    # Resolved, so the same problem can open a fresh task later.
    assert add(db, a, v, c, reason=task["reason"], fact=task["fact_id"]) is True


def test_tasks_are_scoped_to_their_org_and_filterable_by_owner(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua, ub = make_user(db, a, "creator"), make_user(db, b, "creator")
    other = make_user(db, a, "creator")
    va, vb = make_version(db, a, ua, status="approved"), make_version(db, b, ub, status="approved")
    ca, cb = content_of(db, va), content_of(db, vb)
    checker(db)
    add(db, a, va, ca, owner=ua)
    add(db, b, vb, cb, owner=ub)
    assert [
        t["version_id"]
        for t in db.execute("select public.watch_tasks_list(%s)", (a,)).fetchone()[0]
    ] == [str(va)]
    assert (
        db.execute("select public.watch_tasks_list(%s, 'open', %s)", (a, other)).fetchone()[0] == []
    )
    t = db.execute("select public.watch_tasks_list(%s)", (b,)).fetchone()[0][0]
    # Org A can't resolve org B's task.
    assert (
        db.execute(
            "select public.watch_task_resolve(%s, %s, %s, 'dismissed', 'x')", (a, t["id"], ua)
        ).fetchone()[0]
        == 0
    )
    # Only done or dismissed are valid outcomes.
    assert (
        db.execute(
            "select public.watch_task_resolve(%s, %s, %s, 'open', 'x')", (b, t["id"], ub)
        ).fetchone()[0]
        == 0
    )


def test_a_url_can_only_be_registered_for_an_approved_post_of_the_same_org(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua = make_user(db, a, "creator")
    ok = make_version(db, a, ua, status="approved")
    draft = make_version(db, a, ua, status="submitted")
    checker(db)
    assert (
        db.execute(
            "select public.watch_url_set(%s, %s, 'https://x.example/p', %s)", (a, ok, ua)
        ).fetchone()[0]
        == 1
    )
    assert (
        db.execute(
            "select public.watch_url_set(%s, %s, 'https://x.example/p', %s)", (a, draft, ua)
        ).fetchone()[0]
        == 0
    )
    assert (
        db.execute(
            "select public.watch_url_set(%s, %s, 'https://x.example/p', %s)", (b, ok, ua)
        ).fetchone()[0]
        == 0
    )
    target = db.execute("select public.watch_url_target(%s, %s)", (a, ok)).fetchone()[0]
    assert target["url"] == "https://x.example/p" and target["text"] == "Hello"
    assert db.execute("select public.watch_url_target(%s, %s)", (b, ok)).fetchone()[0] is None
    db.execute('select public.watch_url_result(%s, %s, \'{"status": "ok"}\'::jsonb)', (a, ok))
    listed = db.execute("select public.watch_urls_list(%s)", (a,)).fetchone()[0]
    assert listed[0]["last_result"] == {"status": "ok"} and listed[0]["last_checked_at"]
    # Registering again replaces the address and clears the old result.
    db.execute("select public.watch_url_set(%s, %s, 'https://y.example/p', %s)", (a, ok, ua))
    assert (
        db.execute("select public.watch_urls_list(%s)", (a,)).fetchone()[0][0]["last_result"]
        is None
    )


def test_users_and_the_checker_role_have_no_table_access_to_the_watch(db):
    org = make_org(db)
    user = make_user(db, org, "brand_owner")
    as_user(db, user)
    for stmt in (
        "select * from public.watch_tasks",
        "select * from public.published_urls",
        f"select public.watch_live('{org}')",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(stmt)
    db.execute("reset role")
    checker(db)
    for t in ("watch_tasks", "published_urls"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(f"select * from public.{t} limit 1")


def test_facts_and_wordings_include_restricted_facts_only_for_the_scan(db):
    org = make_org(db)
    db.execute(
        "insert into facts (org_id, id, statement, market, owner, valid_from, confidentiality, verified) values"
        " (%s, 'FACT-001', 's', 'IN', 'b', '2026-01-01', 'public', true),"
        " (%s, 'FACT-031', 'secret', 'IN', 'b', '2026-01-01', 'embargoed', true)",
        (org, org),
    )
    checker(db)
    raw = db.execute("select public.watch_facts(%s)", (org,)).fetchone()[0]
    assert {f["id"] for f in raw["facts"]} == {"FACT-001", "FACT-031"}
