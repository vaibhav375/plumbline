"""Run the dev set through Plumbline and through the baseline, and write the results.

`make eval` runs both modes with the live model chain, writes apps/web/public/eval/latest.json (the
"How I know it works" page imports it) and records the run in `eval_runs`."""

import json
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from plumbline.evalkit.baseline import baseline_predict
from plumbline.evalkit.metrics import citation_valid, resolve_labels, score, wilson_interval
from plumbline.llm import LLM, LLMUnavailable
from plumbline.models import Intent, OrgContext
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check

ROOT = Path(__file__).resolve().parents[4]
DEV_SET = ROOT / "data" / "golden" / "dev.jsonl"
LATEST = ROOT / "apps" / "web" / "public" / "eval" / "latest.json"
TODAY = date(2026, 10, 23)  # fixed, so expiry and embargo dates give the same answer every run


COOLDOWN_S = 90


class EvalItem(BaseModel):
    id: str
    kind: Literal["labelled", "clean", "injection"]
    text: str
    channel: str = "instagram"
    labels: list[dict] = []
    base: str | None = None  # injection variants: the labelled item they were made from


class EvalResult(BaseModel):
    mode: str
    recall: float
    precision: float
    false_alarms_per_clean: float
    citation_valid_rate: float
    injection_recall_delta: float
    n_items: int
    n_labels: int
    ms_p95: int
    intervals: dict[str, tuple[float, float]]
    counts: dict[str, tuple[int, int]]  # metric -> (k, n), shown as "k / n"
    duplicates: int
    unavailable: int  # items whose AI calls all failed (baseline) or ran code-only (Plumbline)
    per_item: dict[
        str, dict
    ] = {}  # id -> tp/fp/fn/dup and the IDs it predicted, for reading misses


def load_items(path: Path = DEV_SET) -> list[EvalItem]:
    return [EvalItem.model_validate_json(line) for line in path.read_text().splitlines() if line]


def _predict(item: EvalItem, mode: str, ctx: OrgContext, llm: LLM, today: date):
    doc = parse_upload("paste.txt", item.text.encode(), 10)  # same normalisation as the API
    if mode == "baseline":
        try:
            return doc.text, baseline_predict(doc.text, ctx, llm), False
        except LLMUnavailable:
            return doc.text, [], True
    report = run_check(
        doc, ctx, Intent(channel=item.channel), "creator", False, llm, today, cache=None
    )
    return doc.text, report.findings, report.coverage.ai_status == "unavailable"


def run_eval(
    items: list[EvalItem], mode: str, ctx: OrgContext, llm: LLM, today: date = TODAY
) -> EvalResult:
    known = {r.id for r in ctx.rules} | {t.id for t in ctx.terms} | {f.id for f in ctx.facts}
    totals: dict[str, Counter] = {k: Counter() for k in ("labelled", "clean", "injection", "base")}
    injected_bases = {i.base for i in items if i.kind == "injection"}
    valid = cited = clean_alarm_items = clean_alarms = unavailable = 0
    ms: list[int] = []
    per_item: dict[str, dict] = {}
    for item in items:
        t0 = time.perf_counter()
        text, preds, failed = _predict(item, mode, ctx, llm, today)
        ms.append(round((time.perf_counter() - t0) * 1000))
        unavailable += failed
        s = score(preds, resolve_labels(text, item.labels))
        per_item[item.id] = s | {
            "predicted": [f"{f.rule_id or ''}/{f.fact_id or ''}:{f.quote[:40]}" for f in preds],
            "unavailable": failed,
        }
        totals[item.kind].update(s)
        if item.id in injected_bases:
            totals["base"].update(s)
        if item.kind == "clean":
            clean_alarms += len(preds)
            clean_alarm_items += bool(preds)
        cited += len(preds)
        valid += sum(citation_valid(f, text, known) for f in preds)

    lab = totals["labelled"]
    found, labels = lab["tp"], lab["tp"] + lab["fn"]
    shown = lab["tp"] + lab["fp"]
    n_clean = sum(i.kind == "clean" for i in items)

    def rate(t: Counter) -> float:
        return t["tp"] / max(1, t["tp"] + t["fn"])

    counts = {
        "recall": (found, labels),
        "precision": (lab["tp"], shown),
        "clean_with_alarm": (clean_alarm_items, n_clean),
        "citation_valid": (valid, cited),
    }
    return EvalResult(
        mode=mode,
        recall=found / max(1, labels),
        precision=lab["tp"] / max(1, shown),
        false_alarms_per_clean=clean_alarms / max(1, n_clean),
        citation_valid_rate=valid / max(1, cited),
        # Recall on the injected copies minus recall on their originals: negative means the
        # injected instructions cost recall.
        injection_recall_delta=rate(totals["injection"]) - rate(totals["base"]),
        n_items=len(items),
        n_labels=sum(len(i.labels) for i in items),
        ms_p95=round(statistics.quantiles(ms, n=20)[-1]) if len(ms) >= 2 else (ms or [0])[0],
        intervals={k: wilson_interval(*v) for k, v in counts.items()},
        counts=counts,
        duplicates=sum(t["dup"] for t in totals.values()) - totals["base"]["dup"],
        unavailable=unavailable,
        per_item=per_item,
    )


def _egress_summary(events) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for e in events:
        g = groups.setdefault(
            (e.provider, e.model, e.region),
            {
                "provider": e.provider,
                "model": e.model,
                "region": e.region,
                "calls": 0,
                "chars_sent": 0,
                "tasks": Counter(),
                "statuses": Counter(),
            },
        )
        g["calls"] += 1
        g["chars_sent"] += e.chars_sent
        g["tasks"][e.task] += 1
        g["statuses"][e.status] += 1
    return [
        g | {"tasks": dict(g["tasks"]), "statuses": dict(g["statuses"])} for g in groups.values()
    ]


def main() -> None:  # pragma: no cover - spends real model calls
    import os

    import psycopg

    from plumbline.config import Settings
    from plumbline.llm import default_chain
    from plumbline.rules.load import load_seed_dir

    ctx, errors = load_seed_dir(ROOT / "supabase" / "seed" / "aurelle")
    assert not errors, errors
    items = load_items()
    results, egress = {}, {}
    for n, mode in enumerate(sys.argv[1:] or ["plumbline", "baseline"]):
        if n:
            time.sleep(COOLDOWN_S)  # per-minute rate limits: don't let one mode starve the next
        events: list = []
        llm = LLM(default_chain(Settings()), events.append)
        t0 = time.perf_counter()
        results[mode] = run_eval(items, mode, ctx, llm)
        egress[mode] = _egress_summary(events)
        print(f"{mode}: {time.perf_counter() - t0:.0f} s", results[mode].model_dump_json(indent=1))
    latest = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "today": TODAY.isoformat(),
        "dataset": {
            "name": "dev (builder-written)",
            "n_items": len(items),
            "n_labels": sum(len(i.labels) for i in items),
            "kinds": dict(Counter(i.kind for i in items)),
        },
        "rulebook_version": ctx.rulebook_version,
        "results": {m: r.model_dump(mode="json") for m, r in results.items()},
        "egress": egress,
    }
    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(latest, indent=1) + "\n")
    from scripts.seed import ORG_ID

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            "insert into eval_runs (org_id, name, metrics_json) values (%s, %s, %s)",
            (ORG_ID, "dev", json.dumps(latest)),
        )
    print("wrote", LATEST)


if __name__ == "__main__":
    main()
