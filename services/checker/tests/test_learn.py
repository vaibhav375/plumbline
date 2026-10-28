import json

from plumbline.learn import Case, Wording, cases_from, draft, evaluate, replay, split
from plumbline.llm import FakeLLM

OLD = Wording(title="Be warm", instruction="Copy should sound warm and human.")


def cases(n=12):
    return [
        Case(quote=f"sentence {i}", should_flag=i % 3 != 0, reason=None if i % 3 else "fine here")
        for i in range(n)
    ]


def test_cases_skip_escalations_and_map_actions():
    got = cases_from(
        [
            {"quote": "a", "action": "uphold", "reason": None},
            {"quote": "b", "action": "dismiss", "reason": "ok"},
            {"quote": "c", "action": "escalate", "reason": "?"},
            {"quote": "d", "action": "accept", "reason": None},
        ]
    )
    assert [(c.quote, c.should_flag) for c in got] == [("a", True), ("b", False), ("d", True)]


def test_the_draft_is_written_from_one_half_and_scored_on_the_other():
    train, held = split(cases())
    assert not {c.quote for c in train} & {c.quote for c in held} and len(train) == len(held) == 6


def test_replay_scores_agreement_and_counts_skipped_cases_as_misses():
    cs = [
        Case(quote="x", should_flag=True),
        Case(quote="y", should_flag=False),
        Case(quote="z", should_flag=True),
    ]
    llm = FakeLLM(
        {
            ("judge", ""): json.dumps(
                {"answers": [{"n": 1, "breaks": True}, {"n": 2, "breaks": True}]}
            )
        }
    )
    assert replay(OLD, cs, llm) == {"n": 3, "agree": 1, "rate": 1 / 3}


def test_the_draft_prompt_carries_the_train_cases_not_the_held_out_ones():
    new = {
        "title": "Sound warm",
        "instruction": "Warm means talking to one person, not at a crowd.",
        "examples_good": [],
        "examples_bad": [],
    }
    llm = FakeLLM({("rewrite", ""): json.dumps(new), ("judge", ""): json.dumps({"answers": []})})
    out = evaluate(OLD, cases(), llm)
    sys_prompt = llm.systems[0]
    assert "sentence 0" in sys_prompt and "sentence 1”" not in sys_prompt
    assert (
        out["new"]["title"] == "Sound warm"
        and out["helps"] is False
        and out["held_out"]["old"]["n"] == 6
    )


def test_private_details_are_redacted_before_the_model_sees_them():
    llm = FakeLLM(
        {
            ("rewrite", ""): json.dumps(
                {
                    "title": "Sound warm",
                    "instruction": "Warm means one person.",
                    "examples_good": [],
                    "examples_bad": [],
                }
            )
        }
    )
    draft(OLD, [Case(quote="Email asha@example.com now", should_flag=False)], llm)
    assert "asha@example.com" not in llm.systems[0]
