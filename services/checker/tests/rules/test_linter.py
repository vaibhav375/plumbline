from plumbline.models import Rule
from plumbline.rules.linter import lint_rule


def rule(**kw) -> Rule:
    base = dict(
        id="R1",
        title="t",
        category="style",
        cls="A",
        check_type="pattern",
        params={"regex": "x"},
        severity="minor",
        tier="brand",
        source_ref="s",
        owner_function="brand",
    )
    return Rule(**(base | kw))


def test_linter_flags_sparingly(aurelle):
    gm08 = next(r for r in aurelle.rules if r.id == "GM08")
    assert any("sparingly" in w for w in lint_rule(gm08))


def test_linter_flags_vague_class_a_rule():
    warnings = lint_rule(rule(title="Use hashtags sparingly", params={}))
    assert any("sparingly" in w and "classified C" in w for w in warnings)


def test_linter_quiet_on_good_rules(aurelle):
    for r in aurelle.rules:
        if r.cls != "C":
            assert lint_rule(r) == [], (r.id, lint_rule(r))


def test_linter_bad_regex_and_missing_params():
    assert any("regex" in w.lower() for w in lint_rule(rule(params={"regex": "(unclosed"})))
    assert any("max" in w for w in lint_rule(rule(check_type="count", params={"regex": "!"})))
    assert any("ai_rule" in w for w in lint_rule(rule(cls="A", check_type="ai_rule", params={})))
