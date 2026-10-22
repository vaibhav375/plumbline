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
