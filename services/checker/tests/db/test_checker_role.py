"""The checker's narrow database role (Task 14): it can read one org's confidential facts through
one function, and nothing else; signed-in users can't call that function at all."""

import psycopg
import pytest

from .conftest import as_user, make_org, make_user

pytestmark = pytest.mark.db


def secret_fact(db, org):
    db.execute(
        "insert into facts (org_id, id, statement, market, owner, valid_from, confidentiality, embargo_until,"
        " verified) values (%s, 'FACT-031', 'Mumbai flagship', 'IN', 'brand', '2026-01-01', 'embargoed',"
        " '2026-12-01', true), (%s, 'FACT-001', 'Not tested on animals', 'IN', 'brand', '2026-01-01', 'public',"
        " null, true)",
        (org, org),
    )


def test_checker_role_reads_only_confidential_facts_of_one_org(db):
    org, other = make_org(db, "A"), make_org(db, "B")
    secret_fact(db, org)
    secret_fact(db, other)
    db.execute("set local role plumbline_checker")
    rows = db.execute("select org_id, id from public.confidential_facts(%s)", (org,)).fetchall()
    assert rows == [(org, "FACT-031")]


def test_checker_role_has_no_table_access(db):
    db.execute("set local role plumbline_checker")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("select * from facts limit 1")


def test_signed_in_users_cannot_call_the_function(db):
    org = make_org(db)
    agency = make_user(db, org, "external_creator")
    as_user(db, agency)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("select * from public.confidential_facts(%s)", (org,))
