import psycopg
import pytest

from .conftest import as_admin, as_user, make_finding, make_org, make_user, make_version

pytestmark = pytest.mark.db


def test_chain_links(db):
    org = make_org(db)
    creator = make_user(db, org, "creator")
    reviewer = make_user(db, org, "reviewer")
    finding = make_finding(db, org, make_version(db, org, creator))
    as_user(db, reviewer)
    for action in ("uphold", "dismiss", "overrule"):
        db.execute(
            "insert into decisions (org_id, finding_id, actor, action, reason)"
            " values (%s, %s, %s, %s, 'r')",
            (org, finding, reviewer, action),
        )
    as_admin(db)
    rows = db.execute(
        "select kind, prev_hash, hash from audit_events where org_id = %s order by id", (org,)
    ).fetchall()
    decisions = [r for r in rows if r[0] == "decisions.insert"]
    assert len(decisions) == 3
    for prev, cur in zip(rows, rows[1:], strict=False):
        assert cur[1] == prev[2]
    assert rows[0][1] == "0" * 64


def test_update_denied(db):
    org = make_org(db)
    creator = make_user(db, org, "creator")
    make_version(db, org, creator)
    as_user(db, creator)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("update audit_events set kind = 'tampered' where org_id = %s", (org,))


def test_same_actor_second_approval_rejected(db):
    org = make_org(db)
    creator = make_user(db, org, "creator")
    reviewer = make_user(db, org, "reviewer")
    vid = make_version(db, org, creator)
    as_user(db, reviewer)
    db.execute(
        "insert into approvals (org_id, version_id, actor, stage, outcome, reason)"
        " values (%s, %s, %s, 'first', 'approve', 'ok')",
        (org, vid, reviewer),
    )
    with pytest.raises(psycopg.errors.RaiseException, match="different"):
        db.execute(
            "insert into approvals (org_id, version_id, actor, stage, outcome, reason)"
            " values (%s, %s, %s, 'second', 'approve', 'ok')",
            (org, vid, reviewer),
        )
