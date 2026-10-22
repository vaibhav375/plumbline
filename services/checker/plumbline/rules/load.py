"""CSV import for the rulebook, fact ledger, approved wordings and terms. Bad rows are reported
by row number (header = row 1) and skipped; good rows still load."""

import csv
import io
import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from plumbline.models import ApprovedWording, Fact, OrgContext, Rule, Term

LIST_FIELDS = {"examples_good", "examples_bad", "variants", "aliases"}


def _clean(row: dict[str, str]) -> dict:
    out: dict = {}
    for key, value in row.items():
        value = (value or "").strip()
        if key in LIST_FIELDS:
            out[key] = [v for v in value.split("|") if v]
        elif key == "params":
            out[key] = json.loads(value or "{}")
        else:
            out[key] = value or None
    return out


def _load[T: BaseModel](data: str, model: type[T]) -> tuple[list[T], list[str]]:
    reader = csv.DictReader(io.StringIO(data))
    required = {n for n, f in model.model_fields.items() if f.is_required()}
    missing = required - set(reader.fieldnames or [])
    if missing:
        return [], [f"Missing column(s): {', '.join(sorted(missing))}"]
    items: list[T] = []
    errors: list[str] = []
    seen: set[str] = set()
    for n, row in enumerate(reader, start=2):
        rid = (row.get("id") or "").strip() or "?"
        try:
            item = model.model_validate(_clean(row))
        except json.JSONDecodeError as e:
            errors.append(f"Row {n} ({rid}): params is not valid JSON ({e.msg})")
            continue
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            errors.append(f"Row {n} ({rid}): {problems}")
            continue
        if item.id in seen:
            errors.append(f"Row {n} ({rid}): duplicate id")
            continue
        seen.add(item.id)
        items.append(item)
    return items, errors


def load_rules_csv(data: str) -> tuple[list[Rule], list[str]]:
    return _load(data, Rule)


def load_facts_csv(data: str) -> tuple[list[Fact], list[str]]:
    return _load(data, Fact)


def load_wordings_csv(data: str) -> tuple[list[ApprovedWording], list[str]]:
    return _load(data, ApprovedWording)


def load_terms_csv(data: str) -> tuple[list[Term], list[str]]:
    return _load(data, Term)


def load_seed_dir(
    path: Path, org_id: str = "aurelle", version: str = "v1.3"
) -> tuple[OrgContext, list[str]]:
    """Read a seed folder (rules.csv, facts.csv, wordings.csv, terms.csv) into an OrgContext."""

    def read(name: str) -> str:
        return (path / name).read_text(encoding="utf-8")

    rules, e1 = load_rules_csv(read("rules.csv"))
    facts, e2 = load_facts_csv(read("facts.csv"))
    wordings, e3 = load_wordings_csv(read("wordings.csv"))
    terms, e4 = load_terms_csv(read("terms.csv"))
    ctx = OrgContext(
        org_id=org_id,
        rulebook_version=version,
        rules=rules,
        facts=facts,
        wordings=wordings,
        terms=terms,
    )
    return ctx, [
        *(f"rules.csv {e}" for e in e1),
        *(f"facts.csv {e}" for e in e2),
        *(f"wordings.csv {e}" for e in e3),
        *(f"terms.csv {e}" for e in e4),
    ]
