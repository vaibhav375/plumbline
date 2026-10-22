"""Privacy gate before any model call (§6.2 stage 2).

redact: people's names, phones, emails, Aadhaar and PAN become placeholders (⟦PERSON_1⟧ ...).
Dates, places and numbers stay, because claims depend on them. Brand and product names in
`allow` are never touched.

mask_confidential: sentences that mention a confidential or still-embargoed fact become
⟦RESTRICTED⟧, so that text never reaches a provider. Matching is code only.
"""

import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz

from plumbline.models import Fact, Span
from plumbline.normalize import sentences

ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "IN_AADHAAR", "IN_PAN", "IN_PHONE", "EMAIL"]
LABEL = {"PHONE_NUMBER": "PHONE", "IN_PHONE": "PHONE", "EMAIL_ADDRESS": "EMAIL"}
PATTERNS = {
    # Aadhaar never starts with 0 or 1; written with spaces or hyphens or not at all.
    "IN_AADHAAR": r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b",
    "IN_PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "IN_PHONE": r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b",
    # Presidio's own email check rejects unknown TLDs (e.g. .example); a plain pattern doesn't.
    "EMAIL": r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b",
}
FUZZY_MIN_LEN = 8
# Presidio compiles patterns case-insensitively by default, which turns "[A-Z][a-z]+" into "any
# word" and lets lowercase text pass as a PAN. Names and IDs here depend on case.
CASE_SENSITIVE = re.DOTALL | re.MULTILINE
FUZZY_CUTOFF = 85


@lru_cache(maxsize=1)
def _names() -> tuple[frozenset[str], frozenset[str]]:
    given, surname, section = [], [], None
    for line in (
        (Path(__file__).parent / "data" / "indian_names.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        line = line.split("#", 1)[0].strip()
        if line in ("[given]", "[surname]"):
            section = line
        elif line:
            (given if section == "[given]" else surname).extend(line.split())
    return frozenset(given), frozenset(surname)


def _gazetteer_patterns() -> list[str]:
    given, surname = _names()
    g, s = "|".join(sorted(given)), "|".join(sorted(surname))
    cap = r"[A-Z][a-z]+"
    return [
        rf"\b(?:{g})(?:\s+{cap}){{0,2}}\b",  # Priya, Priya Sharma, Shreya Ghoshal Pandey
        rf"\b{cap}\s+(?:{s})\b",
    ]  # Gurpreet Sandhu, even when the given name is unknown


@lru_cache(maxsize=1)
def _analyzer():
    """Loaded once per process (spaCy model + recognisers, ~160 MB)."""
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    ).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])
    for name, rx in PATTERNS.items():
        engine.registry.add_recognizer(
            PatternRecognizer(
                supported_entity=name,
                patterns=[Pattern(name, rx, 0.6)],
                global_regex_flags=CASE_SENSITIVE,
            )
        )
    engine.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="PERSON",
            name="IndianNameGazetteer",
            global_regex_flags=CASE_SENSITIVE,
            patterns=[
                Pattern(f"in_names_{i}", rx, 0.6) for i, rx in enumerate(_gazetteer_patterns())
            ],
        )
    )
    return engine


def _occurrences(text: str, phrases: set[str]) -> list[tuple[int, int]]:
    spans = []
    for p in phrases:
        if p:
            spans += [
                (m.start(), m.end())
                for m in re.finditer(rf"(?<!\w){re.escape(p)}(?!\w)", text, re.IGNORECASE)
            ]
    return spans


def redact(text: str, allow: set[str]) -> tuple[str, dict[str, str]]:
    allowed = _occurrences(text, allow)
    found = []
    for r in _analyzer().analyze(text=text, language="en", entities=ENTITIES):
        if any(a < r.end and r.start < b for a, b in allowed):
            continue
        word = text[r.start : r.end]
        if (
            r.recognition_metadata.get("recognizer_name") == "SpacyRecognizer"
            and " " not in word
            and word not in _names()[0]
            and re.search(r"(?:^|[.!?]\s+)$", text[: r.start])
        ):
            continue  # spaCy reads sentence-initial imperatives ("Ignore ...") as names
        found.append((r.start, r.end, LABEL.get(r.entity_type, r.entity_type)))
    # Keep the longest of overlapping detections ("Priya Sharma" over "Priya").
    found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    spans: list[tuple[int, int, str]] = []
    for s, e, label in found:
        if spans and s < spans[-1][1]:
            continue
        spans.append((s, e, label))
    placeholders: dict[tuple[str, str], str] = {}
    counts: dict[str, int] = {}
    for s, e, label in spans:  # number in reading order, reuse for repeats
        key = (label, text[s:e])
        if key not in placeholders:
            counts[label] = counts.get(label, 0) + 1
            placeholders[key] = f"⟦{label}_{counts[label]}⟧"
    out = text
    for s, e, label in reversed(spans):
        out = out[:s] + placeholders[(label, text[s:e])] + out[e:]
    return out, {ph: original for (_, original), ph in placeholders.items()}


def _active(f: Fact, today: date) -> bool:
    if f.confidentiality == "confidential":
        return True
    return f.confidentiality == "embargoed" and (f.embargo_until is None or today < f.embargo_until)


def _mentions(alias: str, sentence: str) -> bool:
    a, s = alias.lower(), sentence.lower()
    if re.search(rf"(?<!\w){re.escape(a)}(?!\w)", s):
        return True
    # Fuzzy only for longer, digit-free aliases: "10% off" must never match "20% off".
    return (
        len(a) >= FUZZY_MIN_LEN
        and not any(c.isdigit() for c in a)
        and fuzz.partial_ratio(a, s) >= FUZZY_CUTOFF
    )


def mask_confidential(
    text: str, facts: list[Fact], today: date | None = None
) -> tuple[str, list[tuple[Span, str]]]:
    today = today or date.today()
    active = [f for f in facts if _active(f, today)]
    hits: list[tuple[Span, str]] = []
    for sentence in sentences(text):
        chunk = text[sentence.start : sentence.end]
        for f in active:
            if any(_mentions(a, chunk) for a in f.aliases):
                hits.append((sentence, f.id))
                break
    masked = text
    for span, _ in reversed(hits):
        masked = masked[: span.start] + "⟦RESTRICTED⟧" + masked[span.end :]
    return masked, hits
