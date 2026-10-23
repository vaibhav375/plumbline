"""Guideline health (Improvement 3 v1): do reviewers agree with each rule's flags? Wilson lower
bounds keep a handful of decisions from looking like a verdict."""

from math import sqrt

from plumbline.models import Rule

Z = 1.96  # 95% confidence
MIN_DECISIONS = 10
READY = 0.80  # graduate when we're 95% sure reviewers agree at least 80% of the time
UNCLEAR = 0.25  # flag when we're 95% sure they disagree at least a quarter of the time


def wilson_lower(successes: int, n: int, z: float = Z) -> float:
    """Same formula as the database's `wilson_lower` (migration 0003), but 0 for n = 0."""
    if n == 0:
        return 0.0
    p = successes / n
    return (p + z * z / (2 * n) - z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def graduation_ready(upheld: int, n: int) -> bool:
    return wilson_lower(upheld, n) >= READY


def assess(rows: list[dict], rules: dict[str, Rule]) -> list[dict]:
    """One row per rule from the `rule_health` view, with a status; unclear rules first."""
    out = []
    for r in rows:
        upheld, disagreed = r["upheld"], r["overruled"] + r["dismissed"]
        n = upheld + disagreed
        rule = rules.get(r["rule_id"])
        if n < MIN_DECISIONS:
            status = "too_few"
        elif rule and rule.blocks:
            status = "blocks"
        elif graduation_ready(upheld, n):
            status = "ready"
        else:
            status = "advisory"
        out.append(
            {
                **{k: r[k] for k in ("rule_id", "flags", "upheld", "overruled", "dismissed")},
                "title": rule.title if rule else None,
                "tier": rule.tier if rule else None,
                "maturity": rule.maturity if rule else None,
                "decisions": n,
                "agreement": upheld / n if n else None,
                "wilson_lower": wilson_lower(upheld, n) if n else None,
                "status": status,
                "unclear": n >= MIN_DECISIONS and wilson_lower(disagreed, n) >= UNCLEAR,
            }
        )
    return sorted(out, key=lambda x: (not x["unclear"], -x["decisions"], x["rule_id"]))
