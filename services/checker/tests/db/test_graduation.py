"""Self-learning guidelines (migration 0015): graduation by decisions, undo, pinning, and rewording."""

import psycopg
import pytest

from .conftest import as_admin, as_user, make_org, make_user, make_version

pytestmark = pytest.mark.db


def rule(db, org, tier="brand", owner="brand", maturity="advisory"):
    db.execute(
        "insert into rules (org_id, id, title, category, cls, check_type, params, severity, tier, maturity,"
        " source_ref, owner_function) values (%s, 'TN-90', 'Be warm', 'tone', 'B', 'ai_rule',"
        " '{\"instruction\": \"old\"}', 'minor', %s, %s, 'x', %s)",
        (org, tier, maturity, owner),
    )


def decide(db, org, user, upheld, disagreed, rule_id="TN-90"):
    """One public version per decision, so counts match what the health page would show."""
    for action in ["uphold"] * upheld + ["overrule"] * disagreed:
        v = make_version(db, org, user)
        run = db.execute(
            "insert into check_runs (org_id, version_id, report_json, rulebook_version)"
            " values (%s, %s, '{}', 'v1') returning id",
            (org, v),
        ).fetchone()[0]
        f = db.execute(
            "insert into findings (org_id, run_id, rule_id, category, severity, advisory, quote)"
            " values (%s, %s, %s, 'tone', 'minor', true, 'q') returning id",
            (org, run, rule_id),
        ).fetchone()[0]
        db.execute(
            "insert into decisions (org_id, finding_id, actor, action, reason) values (%s, %s, %s, %s, 'r')",
            (org, f, user, action),
        )


def state(db, org):
    return db.execute(
        "select maturity, pinned, graduated_auto from rules where org_id = %s and id = 'TN-90'",
        (org,),
    ).fetchone()


def setup(db):
    org = make_org(db)
    return org, make_user(db, org, "reviewer")


def test_a_rule_graduates_at_the_threshold_and_the_move_is_audited(db):
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 12, 0)  # lower bound of 12/12 is 0.757: not enough
    assert state(db, org)[0] == "advisory"
    decide(
        db, org, rev, 8, 0
    )  # it crossed at 16/16 (0.806): the trigger stops at the first crossing
    assert state(db, org) == ("blocking", False, True)
    assert db.execute(
        "select kind, n, upheld from rule_changes where org_id = %s", (org,)
    ).fetchall() == [("graduate", 16, 16)]
    assert (
        db.execute(
            "select count(*) from audit_events where org_id = %s and kind = 'rule_changes.insert'",
            (org,),
        ).fetchone()[0]
        == 1
    )


def test_no_graduation_below_ten_decisions_or_below_the_bound_or_for_mandatory_rules(db):
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 9, 0)
    assert state(db, org)[0] == "advisory"
    decide(db, org, rev, 15, 15)  # 24/39 agreement is ~0.6
    assert state(db, org)[0] == "advisory"
    m = make_org(db, "M")
    mu = make_user(db, m, "reviewer")
    rule(db, m, tier="mandatory", owner="compliance")
    decide(db, m, mu, 30, 0)
    assert (
        db.execute("select count(*) from rule_changes where org_id = %s", (m,)).fetchone()[0] == 0
    )


def test_agreement_that_falls_demotes_an_automatic_graduation_with_a_gap(db):
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 25, 0)
    assert state(db, org)[0] == "blocking"
    decide(db, org, rev, 0, 3)  # 25/28 -> still above 0.70
    assert state(db, org)[0] == "blocking"
    decide(db, org, rev, 0, 12)  # 25/40 -> below
    assert state(db, org) == ("advisory", False, False)
    assert [
        k
        for (k,) in db.execute(
            "select kind from rule_changes where org_id = %s order by at", (org,)
        )
    ] == ["graduate", "demote"]


def test_undo_returns_to_advisory_pins_the_rule_and_it_is_not_graduated_again(db):
    org, rev = setup(db)
    owner = make_user(db, org, "brand_owner")
    rule(db, org)
    decide(db, org, rev, 25, 0)
    as_user(db, owner)
    db.execute("select rule_undo('TN-90')")
    as_admin(db)
    assert state(db, org) == ("advisory", True, False)
    decide(db, org, rev, 10, 0)
    assert state(db, org)[0] == "advisory"
    as_user(db, owner)
    db.execute("select rule_unpin('TN-90')")
    as_admin(db)
    decide(db, org, rev, 1, 0)
    assert state(db, org)[0] == "blocking"


def test_only_the_function_that_owns_the_rule_can_undo_or_reword(db):
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 25, 0)
    other = make_user(db, org, "compliance")  # compliance does not own a brand rule
    as_user(db, other)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("select rule_undo('TN-90')")


def test_a_draft_changes_nothing_until_accepted_and_can_be_reverted(db):
    org, rev = setup(db)
    owner = make_user(db, org, "brand_owner")
    rule(db, org)
    as_user(db, owner)
    new = '{"title": "Sound warm", "instruction": "new", "examples_good": ["a"], "examples_bad": ["b"]}'
    cid = db.execute(
        "select clarification_save('TN-90', %s::jsonb, '{}', '{}')", (new,)
    ).fetchone()[0]
    assert db.execute(
        "select title, params->>'instruction' from rules where id = 'TN-90' and org_id = %s", (org,)
    ).fetchone() == ("Be warm", "old")
    db.execute("select clarification_accept(%s, %s::jsonb)", (cid, new))
    assert db.execute(
        "select title, params->>'instruction', examples_bad from rules where id = 'TN-90' and org_id = %s",
        (org,),
    ).fetchone() == ("Sound warm", "new", ["b"])
    db.execute("select clarification_revert(%s)", (cid,))
    assert db.execute(
        "select title, params->>'instruction' from rules where id = 'TN-90' and org_id = %s", (org,)
    ).fetchone() == ("Be warm", "old")
    as_admin(db)
    assert [
        k
        for (k,) in db.execute(
            "select kind from rule_changes where org_id = %s order by at", (org,)
        )
    ] == ["clarify", "revert"]


def test_cases_are_only_this_orgs_public_decisions(db):
    a, ua = setup(db)
    b, ub = setup(db)
    rule(db, a)
    rule(db, b)
    decide(db, a, ua, 2, 1)
    decide(db, b, ub, 5, 0)
    as_user(db, ua)
    assert len(db.execute("select * from rule_cases('TN-90')").fetchall()) == 3


def test_a_finding_counts_once_however_often_it_is_decided(db):
    """Migration 0016: re-clicking Uphold on one finding must not add agreement again."""
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 9, 0)  # nine findings, one decision each
    f = db.execute(
        "select f.id from findings f where f.org_id = %s order by f.id limit 1", (org,)
    ).fetchone()[0]
    for _ in range(20):  # the bug: the same finding upheld again and again
        db.execute(
            "insert into decisions (org_id, finding_id, actor, action, reason) values (%s, %s, %s, 'uphold', 'r')",
            (org, f, rev),
        )
    assert state(db, org)[0] == "advisory"  # still 9 decisions, not 29
    assert db.execute("select n, upheld from rule_counts(%s, 'TN-90')", (org,)).fetchone() == (9, 9)
    as_user(db, rev)
    assert db.execute("select upheld from rule_health where rule_id = 'TN-90'").fetchone()[0] == 9
    assert db.execute("select count(*) from rule_cases('TN-90')").fetchone()[0] == 9
    as_admin(db)


def test_the_latest_decision_wins_when_a_reviewer_changes_their_mind(db):
    org, rev = setup(db)
    rule(db, org)
    decide(db, org, rev, 1, 0)
    f = db.execute("select id from findings where org_id = %s", (org,)).fetchone()[0]
    db.execute(
        "insert into decisions (org_id, finding_id, actor, action, reason, at)"
        " values (%s, %s, %s, 'overrule', 'changed my mind', now() + interval '1 minute')",
        (org, f, rev),
    )
    assert db.execute("select upheld, n from rule_counts(%s, 'TN-90')", (org,)).fetchone() == (0, 1)
