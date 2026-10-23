import pytest

pytestmark = pytest.mark.db


def test_wilson_lower_known_values(db):
    row = db.execute(
        "select wilson_lower(8, 10), wilson_lower(95, 100), wilson_lower(0, 0)"
    ).fetchone()
    assert row[0] == pytest.approx(0.490, abs=5e-4)
    assert row[1] == pytest.approx(0.888, abs=5e-4)
    assert row[2] is None


def test_rule_health_is_own_work_for_creators_and_org_wide_for_reviewers(db):
    from .conftest import as_admin, as_user, make_finding, make_org, make_user, make_version

    org = make_org(db)
    asha, ravi = make_user(db, org, "creator"), make_user(db, org, "creator")
    reviewer = make_user(db, org, "reviewer")
    make_finding(db, org, make_version(db, org, asha))
    make_finding(db, org, make_version(db, org, ravi))
    make_finding(db, org, make_version(db, org, ravi, private=True))  # pre-checks never count
    sql = "select coalesce(sum(flags), 0) from rule_health"
    as_user(db, asha)
    assert db.execute(sql).fetchone()[0] == 1
    assert db.execute("select count(*) from insights_by_origin").fetchone()[0] == 0
    as_admin(db)
    as_user(db, reviewer)
    assert db.execute(sql).fetchone()[0] == 2
