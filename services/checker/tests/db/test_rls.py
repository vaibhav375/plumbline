import pytest

from .conftest import as_admin, as_user, make_org, make_user, make_version

pytestmark = pytest.mark.db


def count(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def test_external_creator_cannot_read_embargoed_fact(db):
    org = make_org(db)
    ext = make_user(db, org, "external_creator")
    reviewer = make_user(db, org, "reviewer")
    db.execute(
        "insert into facts (org_id, id, statement, market, owner, valid_from, confidentiality,"
        " embargo_until, verified) values (%s, 'FACT-031', 'Mumbai flagship', 'IN', 'brand',"
        " '2026-01-01', 'embargoed', '2026-12-01', true)",
        (org,),
    )
    sql = "select count(*) from facts where id = 'FACT-031'"
    as_user(db, ext)
    assert count(db, sql) == 0
    as_admin(db)
    as_user(db, reviewer)
    assert count(db, sql) == 1


def test_private_version_hidden_from_reviewer(db):
    org = make_org(db)
    creator = make_user(db, org, "creator")
    reviewer = make_user(db, org, "reviewer")
    vid = make_version(db, org, creator, private=True, status="precheck")
    sql = "select count(*) from versions where id = %s"
    as_user(db, reviewer)
    assert count(db, sql, vid) == 0
    as_admin(db)
    as_user(db, creator)
    assert count(db, sql, vid) == 1


def test_other_org_invisible(db):
    org_a, org_b = make_org(db, "A"), make_org(db, "B")
    user_a = make_user(db, org_a, "brand_owner")
    user_b = make_user(db, org_b, "brand_owner")
    db.execute(
        "insert into rules (org_id, id, title, category, cls, check_type, params, severity, tier,"
        " source_ref, owner_function) values (%s, 'TN-02', 'Max one !', 'tone', 'A', 'count',"
        " '{\"regex\": \"!\", \"max\": 1}', 'minor', 'brand', 'GL p.4', 'brand')",
        (org_a,),
    )
    sql = "select count(*) from rules where org_id = %s"
    as_user(db, user_b)
    assert count(db, sql, org_a) == 0
    as_admin(db)
    as_user(db, user_a)
    assert count(db, sql, org_a) == 1


def test_external_creator_sees_only_own_work(db):
    """§4.5: an agency sees its own work, not the brand's other content."""
    org = make_org(db)
    agency = make_user(db, org, "external_creator")
    creator = make_user(db, org, "creator")
    own = make_version(db, org, agency)
    other = make_version(db, org, creator)
    as_user(db, agency)
    assert count(db, "select count(*) from versions where id = %s", own) == 1
    assert count(db, "select count(*) from versions where id = %s", other) == 0
    assert count(db, "select count(*) from contents where created_by = %s", creator) == 0


def test_audit_log_own_work_only_for_creators(db):
    """§4.5: creators see the audit log for their own work; reviewer roles see all of it."""
    org = make_org(db)
    creator_a = make_user(db, org, "creator")
    creator_b = make_user(db, org, "creator")
    auditor = make_user(db, org, "auditor")
    make_version(db, org, creator_a)
    make_version(db, org, creator_b)
    sql = "select count(*) from audit_events where org_id = %s"
    as_user(db, creator_a)
    assert count(db, sql, org) == 1
    as_admin(db)
    as_user(db, auditor)
    assert count(db, sql, org) == 2


def test_users_can_create_their_own_versions_with_returning(db):
    """Task 14 live run: PostgREST inserts with RETURNING, which must also pass the read policy;
    a policy that looks the row up again by id can't see it inside the same statement."""
    org = make_org(db)
    creator = make_user(db, org, "creator")
    agency = make_user(db, org, "external_creator")
    for user, private in ((creator, True), (agency, True), (creator, False)):
        as_admin(db)
        content = db.execute(
            "insert into contents (org_id, title, channel, region, origin, created_by)"
            " values (%s, 'Post', 'instagram', 'IN', 'agency', %s) returning id",
            (org, user),
        ).fetchone()[0]
        as_user(db, user)
        row = db.execute(
            "insert into versions (org_id, content_id, n, text, private, status, created_by)"
            " values (%s, %s, 1, 'Hello', %s, 'precheck', %s) returning id, private",
            (org, content, private, user),
        ).fetchone()
        assert row[1] is private
