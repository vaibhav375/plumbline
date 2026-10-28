import pytest

from plumbline import api, auth, health

from .test_api import bearer, client, token  # noqa: F401  (client is a fixture)


def test_wilson_20_of_20_ready():
    assert health.wilson_lower(20, 20) == pytest.approx(0.839, abs=5e-4)
    assert health.graduation_ready(20, 20)


def test_wilson_19_of_20_not_ready():
    assert health.wilson_lower(19, 20) < 0.80
    assert not health.graduation_ready(19, 20)


def test_wilson_38_of_40_ready():
    assert health.graduation_ready(38, 40)


def test_wilson_n0_returns_0():
    assert health.wilson_lower(0, 0) == 0.0


def test_wilson_matches_the_database_function():
    # Same values as tests/db/test_views.py::test_wilson_lower_known_values (SQL wilson_lower).
    assert health.wilson_lower(8, 10) == pytest.approx(0.490, abs=5e-4)
    assert health.wilson_lower(95, 100) == pytest.approx(0.888, abs=5e-4)


def row(rule_id, upheld, overruled, dismissed=0, flags=50):
    return {
        "rule_id": rule_id,
        "flags": flags,
        "upheld": upheld,
        "overruled": overruled,
        "dismissed": dismissed,
    }


def test_status_and_unclear(aurelle):
    rules = {r.id: r for r in aurelle.rules}
    a = {
        r["rule_id"]: r
        for r in health.assess(
            [
                row("TN-02", 34, 1),  # brand, advisory: 0.855 ≥ 0.80
                row("GM10", 12, 0),  # 0.757: high agreement, not enough decisions yet
                row("GM07", 4, 1),  # n = 5
                row("CL-03", 22, 0, 1),  # mandatory: blocks regardless
                row("TN-03", 6, 9, 5),  # 15 of 20 disagree
                row("TN-01", 9, 6, 3),  # 9 of 18 disagree
                row("CTA-02", 18, 2, 1),  # 3 of 21 disagree: not unclear
                row("GONE-1", 30, 0),  # rule since removed from the rulebook
            ],
            rules,
        )
    }
    assert {k: v["status"] for k, v in a.items()} == {
        "TN-02": "ready",
        "GM10": "advisory",
        "GM07": "too_few",
        "CL-03": "blocks",
        "TN-03": "advisory",
        "TN-01": "advisory",
        "CTA-02": "advisory",
        "GONE-1": "ready",
    }
    assert sorted(k for k, v in a.items() if v["unclear"]) == ["TN-01", "TN-03"]
    assert a["TN-02"]["decisions"] == 35 and a["TN-02"]["agreement"] == pytest.approx(34 / 35)
    assert a["TN-02"]["title"] == rules["TN-02"].title and a["GONE-1"]["title"] is None


def test_unclear_rules_come_first(aurelle):
    out = health.assess([row("TN-02", 34, 1), row("TN-03", 6, 9, 5)], {})
    assert [r["rule_id"] for r in out] == ["TN-03", "TN-02"]


@pytest.fixture
def health_db(client, monkeypatch):  # noqa: F811
    state = {"role": "brand_owner"}
    monkeypatch.setattr(
        auth, "fetch_profile", lambda s, t, uid: {"org_id": "org-1", "role": state["role"]}
    )
    monkeypatch.setattr(
        api.db,
        "health",
        lambda s, t: (
            [row("TN-03", 6, 9, 5), row("TN-02", 34, 1)],
            [{"origin": "employee", "authors": 3, "versions": 9, "findings": 20, "blocking": 4}],
            True,
        ),
    )
    monkeypatch.setattr(api.db, "pinned_rules", lambda s, t: ["TN-03"])
    return state


def test_health_api_for_reviewers(client, health_db):  # noqa: F811
    body = client.get("/v1/health", headers=bearer(token())).json()
    assert (body["scope"], body["unclear"], body["synthetic"]) == ("org", 1, True)
    assert body["by_origin"][0]["origin"] == "employee"
    assert [r["rule_id"] for r in body["rules"]] == ["TN-03", "TN-02"]
    assert [r["pinned"] for r in body["rules"]] == [True, False]


def test_creators_get_their_own_work_without_group_breakdown(client, health_db):  # noqa: F811
    health_db["role"] = "external_creator"
    body = client.get("/v1/health", headers=bearer(token())).json()
    assert body["scope"] == "mine"
    assert body["by_origin"] is None
    assert body["synthetic"] is False  # their own work never includes the seeded history
