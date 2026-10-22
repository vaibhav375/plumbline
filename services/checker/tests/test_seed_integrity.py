import csv
import json
import re
from pathlib import Path

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed" / "aurelle"
CHECK_TYPES = {"pattern", "word_list", "count", "required", "contrast", "alt_text", "ai_rule"}


def rows(name):
    with (SEED / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def by_id(name):
    return {r["id"]: r for r in rows(name)}


def test_every_wording_references_existing_fact():
    facts = by_id("facts.csv")
    assert [w["id"] for w in rows("wordings.csv") if w["fact_id"] not in facts] == []


def test_every_rule_has_valid_check_type():
    assert [
        (r["id"], r["check_type"]) for r in rows("rules.csv") if r["check_type"] not in CHECK_TYPES
    ] == []


def test_worked_example_present():
    first = json.loads((SEED / "contents.json").read_text(encoding="utf-8"))[0]
    assert first["key"] == "worked-example"
    assert first["text"].startswith("Meet the NEW Aurelle Vitamin-C serum!!!")
    assert (SEED / first["banner"]).is_file()


def test_ids_later_tasks_rely_on():
    rules, facts, wordings, terms = (
        by_id(n) for n in ("rules.csv", "facts.csv", "wordings.csv", "terms.csv")
    )
    for rid in (
        "TN-01",
        "TN-02",
        "CTA-02",
        "CL-03",
        "CL-05",
        "DL-REQ",
        "A11Y-CONTRAST",
        "A11Y-ALT",
        "GM08",
    ):
        assert rid in rules, rid
    assert rules["GM08"]["cls"] == "C" and "sparingly" in rules["GM08"]["title"]
    assert rules["TN-01"]["check_type"] == "ai_rule" and rules["TN-01"]["examples_bad"]
    assert (
        facts["FACT-031"]["confidentiality"] == "embargoed"
        and facts["FACT-031"]["embargo_until"] == "2026-12-01"
    )
    assert facts["FACT-014"]["valid_until"] == "2027-03-31"
    assert wordings["AW-014b"]["text"] == "shown to visibly reduce dark spots by 32% in 8 weeks*"
    assert wordings["AW-014b"]["disclaimer"] == "*In-house study, 48 participants, 2026."
    assert {"Vitamin-C serum", "vit C serum"} <= set(terms["TM-007"]["variants"].split("|"))


def test_no_term_variant_matches_its_own_preferred_name():
    for t in rows("terms.csv"):
        for v in t["variants"].split("|"):
            assert v.lower() not in t["preferred"].lower(), (t["id"], v)


def test_rule_params_parse_and_regexes_compile():
    for r in rows("rules.csv"):
        params = json.loads(r["params"] or "{}")
        for key in ("regex", "when_regex", "must_regex"):
            if key in params:
                re.compile(params[key])


def test_pattern_rules_agree_with_their_own_examples():
    for r in rows("rules.csv"):
        if r["check_type"] != "pattern" or r["cls"] != "A":
            continue
        rx = re.compile(json.loads(r["params"])["regex"])
        for bad in filter(None, r["examples_bad"].split("|")):
            assert rx.search(bad), (r["id"], "misses its bad example", bad)
        for good in filter(None, r["examples_good"].split("|")):
            assert not rx.search(good), (r["id"], "fires on its good example", good)


def test_history_only_references_real_rules_and_is_labelled_synthetic():
    history = json.loads((SEED / "history.json").read_text(encoding="utf-8"))
    rules = by_id("rules.csv")
    assert history["synthetic"] is True
    assert set(history["rules"]) <= set(rules)
    for spec in history["rules"].values():
        assert spec["quote"] in spec["sample"]
