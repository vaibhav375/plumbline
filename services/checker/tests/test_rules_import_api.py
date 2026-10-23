from datetime import date, timedelta

import pytest

from plumbline import api, auth

from .conftest import SEED
from .test_api import bearer, client, token  # noqa: F401  (client is a fixture)

LINES = (SEED / "rules.csv").read_text(encoding="utf-8").splitlines()
HEADER = LINES[0]
ROW = {line.split(",", 1)[0]: line for line in LINES[1:]}


@pytest.fixture
def rules_db(client, monkeypatch):  # noqa: F811
    state = {"role": "brand_owner", "written": []}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-1", "role": state["role"]}
    )
    monkeypatch.setattr(api.db, "upsert_rules", lambda s, t, rows: state["written"].extend(rows))
    return state


def _import(client, csv_text: str, dry_run: bool = False):  # noqa: F811
    return client.post(
        f"/v1/rules/import?dry_run={str(dry_run).lower()}",
        headers=bearer(token()),
        files={"file": ("rules.csv", csv_text.encode(), "text/csv")},
    )


def test_import_returns_lint_counts(client, rules_db):  # noqa: F811
    r = _import(client, "\n".join([HEADER, ROW["CL-01"], ROW["GM08"]]))
    assert r.status_code == 200
    body = r.json()
    assert (body["imported"], body["need_clarification"], body["rejected"]) == (2, 1, [])
    assert any("sparingly" in w for w in body["warnings"]["GM08"])
    assert [w["id"] for w in rules_db["written"]] == ["CL-01", "GM08"]


def test_import_forbidden_for_creator(client, rules_db):  # noqa: F811
    rules_db["role"] = "creator"
    assert _import(client, "\n".join([HEADER, ROW["CL-01"]])).status_code == 403
    assert rules_db["written"] == []


def test_dry_run_previews_without_writing(client, rules_db):  # noqa: F811
    r = _import(client, "\n".join([HEADER, ROW["CL-01"], ROW["GM08"]]), dry_run=True)
    assert (r.json()["imported"], r.json()["dry_run"]) == (2, True)
    assert rules_db["written"] == []


def test_bad_rows_are_reported_and_skipped(client, rules_db):  # noqa: F811
    bad = ROW["CL-02"].replace(",blocking,", ",fatal,")
    body = _import(client, "\n".join([HEADER, ROW["CL-01"], bad])).json()
    assert body["imported"] == 1
    assert body["rejected"][0].startswith("Row 3 (CL-02)")
    assert [w["id"] for w in rules_db["written"]] == ["CL-01"]


def test_import_rejects_a_non_csv(client, rules_db):  # noqa: F811
    assert _import(client, "just some text").json()["imported"] == 0


def test_rules_list_shows_lint_warnings(client, rules_db):  # noqa: F811
    rules_db["role"] = "creator"
    r = client.get("/v1/rules", headers=bearer(token()))
    assert r.status_code == 200
    rules = {x["id"]: x for x in r.json()["rules"]}
    assert any("sparingly" in w for w in rules["GM08"]["warnings"])
    assert rules["CL-01"]["warnings"] == []
    assert r.json()["can_import"] is False


def test_fact_ledger_nests_wordings_and_marks_expired(client, rules_db, monkeypatch):  # noqa: F811
    today = api._today()
    fact = {
        "id": "FACT-1",
        "statement": "s",
        "market": "IN",
        "owner": "Compliance",
        "valid_from": "2025-01-01",
        "confidentiality": "public",
        "verified": False,
    }
    monkeypatch.setattr(
        api.db,
        "list_facts",
        lambda s, t: (
            [
                fact | {"valid_until": str(today - timedelta(days=1))},
                fact | {"id": "FACT-2", "valid_until": str(today)},
            ],
            [{"id": "AW-1", "fact_id": "FACT-1", "text": "w"}],
        ),
    )
    rules_db["role"] = "external_creator"
    body = client.get("/v1/facts", headers=bearer(token())).json()
    facts = {f["id"]: f for f in body["facts"]}
    assert facts["FACT-1"]["expired"] is True and facts["FACT-2"]["expired"] is False
    assert [w["id"] for w in facts["FACT-1"]["wordings"]] == ["AW-1"]
    assert body["restricted"] is True
    rules_db["role"] = "compliance"
    assert client.get("/v1/facts", headers=bearer(token())).json()["restricted"] is False
    assert date.fromisoformat(body["today"]) == today
