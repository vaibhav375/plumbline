"""Rule linter: catches rules that can't run as written (§4.3: class C rules never run)."""

import re

from plumbline.models import Rule

# Words that make a rule a judgement call unless params pin them down.
VAGUE = (
    "sparingly",
    "infrequently",
    "when appropriate",
    "appropriately",
    "common sense",
    "as needed",
    "too many",
    "excessive",
    "overuse",
    "where possible",
    "generally",
)

REQUIRED_PARAMS = {
    "pattern": ("regex",),
    "count": ("regex", "max"),
    "required": ("when_regex", "must_regex"),
}


def lint_rule(rule: Rule) -> list[str]:
    warnings: list[str] = []
    title = rule.title.lower()
    if not rule.params:
        for word in VAGUE:
            if re.search(rf"\b{re.escape(word)}\b", title):
                warnings.append(
                    f"Vague quantifier '{word}' with no params; classified C, will not run"
                )
    if rule.cls == "C":
        if not warnings:
            warnings.append("Class C (judgement only): kept in the rulebook, never run")
        return warnings

    if rule.check_type == "ai_rule" and rule.cls == "A":
        warnings.append("Class A rules are checked by code; ai_rule needs class B")
    if rule.cls == "B" and rule.check_type != "ai_rule":
        warnings.append("Class B rules are AI judgements; use check_type ai_rule")
    if rule.cls == "B" and not (rule.examples_good and rule.examples_bad):
        warnings.append("AI rules need at least one good and one bad example")

    for key in REQUIRED_PARAMS.get(rule.check_type, ()):
        if key not in rule.params:
            warnings.append(f"{rule.check_type} rules need params.{key}")
    if rule.check_type == "count" and not isinstance(rule.params.get("max", 0), int):
        warnings.append("params.max must be a whole number")
    if rule.check_type == "word_list" and not (
        rule.params.get("words") or rule.params.get("source")
    ):
        warnings.append("word_list rules need params.words (or source: terms)")
    for key in ("regex", "when_regex", "must_regex"):
        if key in rule.params:
            try:
                re.compile(rule.params[key])
            except re.error as e:
                warnings.append(f"params.{key} is not a valid regex: {e}")
    return warnings
