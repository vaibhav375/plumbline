"""Improvement 3: draft a clearer wording of a rule from reviewers' recorded decisions, and measure it.

A *case* is one recorded decision on a flagged sentence: reviewers upheld it (the rule should flag it) or did
not (it should not). A wording is scored by how often an AI judge, given only that wording and the sentence,
gives the answer the reviewers gave. The draft is written from half the cases and scored on the other half,
so it isn't graded on its own homework.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from plumbline.llm import LLM
from plumbline.models import Rule
from plumbline.privacy import redact

PROMPTS = Path(__file__).parent / "prompts"
UPHELD = {"accept", "edit", "uphold"}
DISAGREED = {"overrule", "dismiss"}
BATCH = 10
MIN_CASES = 10  # fewer decisions than this can't both write and test a wording


class Case(BaseModel):
    quote: str
    should_flag: bool
    reason: str | None = None


class Wording(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    instruction: str = Field(min_length=10, max_length=700)
    examples_good: list[str] = Field(default_factory=list, max_length=3)
    examples_bad: list[str] = Field(default_factory=list, max_length=3)


class _Answer(BaseModel):
    n: int
    breaks: bool


class _Answers(BaseModel):
    answers: list[_Answer]


def wording_of(rule: Rule) -> Wording:
    return Wording(
        title=rule.title,
        instruction=rule.params.get("instruction") or rule.title,
        examples_good=rule.examples_good[:3],
        examples_bad=rule.examples_bad[:3],
    )


def cases_from(rows: list[dict]) -> list[Case]:
    """Rows of `rule_cases` (quote, action, reason). Decisions other than upheld/disagreed (escalations) are skipped."""
    return [
        Case(quote=r["quote"], should_flag=r["action"] in UPHELD, reason=(r.get("reason") or None))
        for r in rows
        if r["action"] in UPHELD | DISAGREED
    ]


def split(cases: list[Case]) -> tuple[list[Case], list[Case]]:
    """Alternate cases: even positions write the draft, odd positions test it. Fixed, so a run is repeatable."""
    return cases[::2], cases[1::2]


def _safe(text: str) -> str:
    return redact(text, set())[0]


def _wording_text(w: Wording) -> str:
    out = [f"{w.title}\nHow to judge: {w.instruction}"]
    out += [f"Follows the rule: {x}" for x in w.examples_good]
    out += [f"Breaks the rule: {x}" for x in w.examples_bad]
    return "\n".join(out)


def draft(old: Wording, train: list[Case], llm: LLM) -> Wording:
    lines = []
    for c in train:
        verdict = "Upheld" if c.should_flag else "Not upheld"
        why = f" (reviewer: {_safe(c.reason)})" if c.reason and not c.should_flag else ""
        lines.append(f"- {verdict}: “{_safe(c.quote)}”{why}")
    system = (
        (PROMPTS / "clarify.txt")
        .read_text(encoding="utf-8")
        .replace("@@WORDING@@", _wording_text(old))
        .replace("@@CASES@@", "\n".join(lines))
    )
    w, _ = llm.json("rewrite", system, "Write the clearer wording.", Wording)
    return w


def replay(w: Wording, cases: list[Case], llm: LLM) -> dict:
    """How often the wording leads the judge to the reviewers' decision. A case the model skips counts as a miss."""
    template = (PROMPTS / "replay.txt").read_text(encoding="utf-8")
    examples = "\n".join(
        [f"Follows the rule: {x}" for x in w.examples_good]
        + [f"Breaks the rule: {x}" for x in w.examples_bad]
    )
    agree = 0
    for i in range(0, len(cases), BATCH):
        chunk = cases[i : i + BATCH]
        system = (
            template.replace("@@TITLE@@", w.title)
            .replace("@@INSTRUCTION@@", w.instruction)
            .replace("@@EXAMPLES@@", examples)
            .replace(
                "@@SENTENCES@@",
                "\n".join(f"{n}. “{_safe(c.quote)}”" for n, c in enumerate(chunk, 1)),
            )
        )
        got, _ = llm.json("judge", system, "Answer for each sentence.", _Answers)
        said = {a.n: a.breaks for a in got.answers}
        agree += sum(said.get(n) is c.should_flag for n, c in enumerate(chunk, 1))
    n = len(cases)
    return {"n": n, "agree": agree, "rate": agree / n if n else None}


def evaluate(old: Wording, cases: list[Case], llm: LLM) -> dict:
    """Draft from the writing half; score old and new wording on the held-out half."""
    train, held = split(cases)
    new = draft(old, train, llm)
    before, after = replay(old, held, llm), replay(new, held, llm)
    return {
        "new": new.model_dump(),
        "held_out": {"old": before, "new": after},
        "trained_on": len(train),
        "helps": after["agree"] > before["agree"],
    }
