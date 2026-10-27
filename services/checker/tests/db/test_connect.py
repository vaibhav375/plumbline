"""Round 3, improvement 2 (migration 0013): link codes, chat links, gate keys and the gate snapshot.
Everything is reached as the narrow checker role; users get nothing."""

import json

import psycopg
import pytest

from .conftest import as_user, make_org, make_user, make_version

pytestmark = pytest.mark.db


def checker(db):
    db.execute("set local role plumbline_checker")


def fact(db, org, fid, confidentiality="public"):
    db.execute(
        "insert into facts (org_id, id, statement, market, owner, valid_from, confidentiality, verified)"
        " values (%s, %s, %s, 'IN', 'brand', '2026-01-01', %s, true)",
        (org, fid, f"statement {fid} of {org}", confidentiality),
    )


def rule(db, org, rid, active=True):
    db.execute(
        "insert into rules (org_id, id, title, category, cls, check_type, params, severity, tier, maturity,"
        " source_ref, owner_function, active) values (%s, %s, 'T', 'tone', 'A', 'pattern', '{}', 'minor',"
        " 'brand', 'advisory', 'x', 'brand', %s)",
        (org, rid, active),
    )


def test_a_code_works_once_and_links_the_address(db):
    org = make_org(db, "Acme")
    owner = make_user(db, org, "brand_owner")
    checker(db)
    db.execute("select public.agent_make_code(%s, %s, 'h1', 15)", (org, owner))
    got = db.execute("select public.agent_redeem_code('h1', 'agent1abc')").fetchone()[0]
    assert got["org_id"] == str(org) and got["org_name"] == "Acme"
    assert db.execute("select public.agent_redeem_code('h1', 'agent1other')").fetchone()[0] is None
    link = db.execute("select public.agent_link_for('agent1abc')").fetchone()[0]
    assert link["org_id"] == str(org)
    assert db.execute("select public.agent_link_for('agent1other')").fetchone()[0] is None


def test_an_expired_or_unknown_code_links_nothing(db):
    org = make_org(db)
    owner = make_user(db, org, "brand_owner")
    checker(db)
    db.execute("select public.agent_make_code(%s, %s, 'old', -1)", (org, owner))
    assert db.execute("select public.agent_redeem_code('old', 'agent1x')").fetchone()[0] is None
    assert db.execute("select public.agent_redeem_code('nope', 'agent1x')").fetchone()[0] is None
    assert db.execute("select public.agent_link_for('agent1x')").fetchone()[0] is None


def test_relinking_moves_the_address_and_unlink_is_scoped_to_its_org(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua, ub = make_user(db, a, "brand_owner"), make_user(db, b, "brand_owner")
    checker(db)
    for org, user, h in ((a, ua, "ha"), (b, ub, "hb")):
        db.execute("select public.agent_make_code(%s, %s, %s, 15)", (org, user, h))
    db.execute("select public.agent_redeem_code('ha', 'agent1z')")
    db.execute("select public.agent_redeem_code('hb', 'agent1z')")
    assert db.execute("select public.agent_link_for('agent1z')").fetchone()[0]["org_id"] == str(b)
    assert (
        db.execute("select public.agent_unlink('agent1z', %s)", (a,)).fetchone()[0] == 0
    )  # not A's
    assert db.execute("select public.agent_unlink('agent1z', %s)", (b,)).fetchone()[0] == 1
    assert db.execute("select public.agent_links_list(%s)", (b,)).fetchone()[0] == []


def test_org_context_has_only_that_orgs_non_confidential_rows(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    for org in (a, b):
        fact(db, org, "FACT-001")
        fact(db, org, "FACT-002", "internal")
        fact(db, org, "FACT-031", "embargoed")
        fact(db, org, "FACT-040", "confidential")
        rule(db, org, "TN-02")
        rule(db, org, "TN-99", active=False)
        db.execute(
            "insert into approved_wordings (org_id, id, fact_id, market, channel, text) values"
            " (%s, 'AW-1', 'FACT-001', 'IN', 'any', 'ok'), (%s, 'AW-31', 'FACT-031', 'IN', 'any', 'secret')",
            (org, org),
        )
    checker(db)
    ctx = db.execute("select public.agent_org_context(%s)", (a,)).fetchone()[0]
    assert {f["org_id"] for f in ctx["facts"]} == {str(a)}
    assert {f["id"] for f in ctx["facts"]} == {"FACT-001", "FACT-002"}
    assert [r["id"] for r in ctx["rules"]] == ["TN-02"]
    assert {w["id"] for w in ctx["wordings"]} == {"AW-1"}
    assert str(b) not in json.dumps(ctx)


def test_org_context_matches_what_an_agency_writer_can_read(db):
    org = make_org(db)
    agency = make_user(db, org, "external_creator")
    for fid, c in (("FACT-001", "public"), ("FACT-002", "internal"), ("FACT-031", "embargoed")):
        fact(db, org, fid, c)
    rule(db, org, "TN-02")
    rule(db, org, "TN-99", active=False)
    as_user(db, agency)
    seen = {r[0] for r in db.execute("select id from facts")}
    seen_rules = {r[0] for r in db.execute("select id from rules where active")}
    db.execute("reset role")
    checker(db)
    ctx = db.execute("select public.agent_org_context(%s)", (org,)).fetchone()[0]
    assert {f["id"] for f in ctx["facts"]} == seen
    assert {r["id"] for r in ctx["rules"]} == seen_rules


def test_gate_keys_belong_to_their_org_and_can_be_revoked(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua = make_user(db, a, "brand_owner")
    checker(db)
    kid = db.execute("select public.gate_key_create(%s, %s, 'kh', 'Buffer')", (a, ua)).fetchone()[0]
    assert db.execute("select public.gate_key_org('kh')").fetchone()[0] == a
    assert db.execute("select public.gate_key_org('other')").fetchone()[0] is None
    assert db.execute("select public.gate_key_revoke(%s, %s)", (b, kid)).fetchone()[0] == 0
    assert db.execute("select public.gate_key_revoke(%s, %s)", (a, kid)).fetchone()[0] == 1
    assert db.execute("select public.gate_key_org('kh')").fetchone()[0] is None
    listed = db.execute("select public.gate_keys_list(%s)", (a,)).fetchone()[0]
    assert listed[0]["label"] == "Buffer" and listed[0]["revoked_at"]


def test_gate_snapshot_is_only_for_the_versions_own_org_and_never_private(db):
    a, b = make_org(db, "A"), make_org(db, "B")
    ua = make_user(db, a, "creator")
    shown = make_version(db, a, ua, status="approved")
    private = make_version(db, a, ua, private=True, status="precheck")
    content = db.execute("select content_id from versions where id = %s", (shown,)).fetchone()[0]
    checker(db)
    snap = db.execute("select public.gate_snapshot(%s, %s)", (a, shown)).fetchone()[0]
    assert snap["version"]["status"] == "approved" and snap["version"]["text"] == "Hello"
    assert db.execute("select public.gate_snapshot(%s, %s)", (b, shown)).fetchone()[0] is None
    assert db.execute("select public.gate_snapshot(%s, %s)", (a, private)).fetchone()[0] is None
    assert (
        db.execute("select public.gate_latest_version(%s, %s)", (a, content)).fetchone()[0] == shown
    )
    assert (
        db.execute("select public.gate_latest_version(%s, %s)", (b, content)).fetchone()[0] is None
    )


def test_users_and_the_api_roles_cannot_touch_any_of_it(db):
    org = make_org(db)
    user = make_user(db, org, "brand_owner")
    as_user(db, user)
    for stmt in (
        "select * from public.agent_links",
        "select * from public.gate_keys",
        "select * from public.agent_link_codes",
        "select * from public.gate_calls",
        "select public.agent_link_for('x')",
        "select public.gate_key_org('x')",
        f"select public.agent_org_context('{org}')",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(stmt)


def test_the_checker_role_still_has_no_table_access(db):
    checker(db)
    for t in ("agent_links", "gate_keys", "agent_link_codes", "gate_calls"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(f"select * from public.{t} limit 1")
