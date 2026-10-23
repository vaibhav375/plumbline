import copy
import csv
import io
import json
from pathlib import Path

from plumbline import audit

# The first three events of Aurelle's live chain, read with `payload::text` so the text is exactly
# what the database hashed. Verifying them proves Python recomputes hashes the way the trigger does.
CHAIN = json.loads((Path(__file__).parent / "fixtures" / "audit_chain.json").read_text())


def test_verify_valid_chain():
    assert audit.verify_chain(CHAIN) == {"valid": True, "length": 3, "broken_at": None}


def test_verify_detects_tamper():
    rows = copy.deepcopy(CHAIN)
    rows[1]["payload"] = rows[1]["payload"].replace('"n": 1', '"n": 2')
    assert rows[1]["payload"] != CHAIN[1]["payload"]
    assert audit.verify_chain(rows) == {"valid": False, "length": 3, "broken_at": 2}


def test_verify_detects_a_removed_event():
    assert audit.verify_chain([CHAIN[0], CHAIN[2]])["broken_at"] == 2


def test_verify_empty_chain_is_valid():
    assert audit.verify_chain([]) == {"valid": True, "length": 0, "broken_at": None}


def test_export_csv_header():
    rows = list(csv.reader(io.StringIO(audit.to_csv(CHAIN))))
    assert rows[0] == [
        "at",
        "actor",
        "kind",
        "entity",
        "entity_id",
        "prev_hash",
        "hash",
        "payload",
    ]
    assert len(rows) == 4
    assert rows[1][7] == CHAIN[0]["payload"]  # exact text, so the export can be re-verified offline


def test_describe_events():
    assert audit.describe("decisions.insert", {"action": "uphold"}) == "upheld a finding"
    assert (
        audit.describe("approvals.insert", {"stage": "compliance", "outcome": "approve"})
        == "approved the compliance stage"
    )
    assert (
        audit.describe("versions.update", {"from_status": "submitted", "status": "in_review"})
        == "moved a version from submitted to in review"
    )
    assert (
        audit.describe("versions.insert", {"n": 2, "private": True}) == "saved version 2 (private)"
    )
