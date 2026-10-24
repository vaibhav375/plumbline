import json

import httpx
import pytest
import respx
from pydantic import BaseModel

from plumbline.llm import LLM, EgressEvent, FakeLLM, LLMUnavailable, ProviderCfg

GROQ = "https://groq.test/v1"
GEMINI = "https://gemini.test/v1"


class Claims(BaseModel):
    claims: list[str]


def chain() -> list[ProviderCfg]:
    return [
        ProviderCfg(
            name="groq",
            base_url=GROQ,
            api_key="g",
            region="us",
            models={"extract": "gpt-oss-20b", "judge": "qwen"},
            params={"gpt-oss-20b": {"reasoning_effort": "low"}},
        ),
        ProviderCfg(
            name="gemini",
            base_url=GEMINI,
            api_key="m",
            region="global",
            models={"extract": "flash", "judge": "flash"},
        ),
    ]


def ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.fixture
def llm():
    events: list[EgressEvent] = []
    sleeps: list[float] = []
    adapter = LLM(chain(), events.append, sleep=sleeps.append)
    adapter.events, adapter.sleeps = events, sleeps  # for assertions
    return adapter


@respx.mock
def test_strips_think_and_parses(llm):
    respx.post(f"{GROQ}/chat/completions").mock(
        return_value=ok('<think>hmm, claims...</think>\n{"claims": ["clinically proven"]}')
    )
    parsed, used = llm.json("extract", "sys", "user text", Claims)
    assert parsed.claims == ["clinically proven"] and used == "groq/gpt-oss-20b"


@respx.mock
def test_invalid_json_then_valid_retries_same_provider(llm):
    route = respx.post(f"{GROQ}/chat/completions")
    route.side_effect = [ok("not json at all"), ok('{"claims": ["x"]}')]
    parsed, used = llm.json("extract", "sys", "user", Claims)
    assert used == "groq/gpt-oss-20b" and route.call_count == 2


@respx.mock
def test_schema_mismatch_counts_as_invalid(llm):
    respx.post(f"{GROQ}/chat/completions").side_effect = [ok('{"wrong": 1}'), ok('{"claims": []}')]
    parsed, _ = llm.json("extract", "sys", "user", Claims)
    assert parsed.claims == [] and [e.status for e in llm.events] == ["invalid_json", "ok"]


@respx.mock
def test_429_moves_straight_to_the_next_provider(llm):
    # Each provider/model has its own rate limit, so waiting on a limited one only adds delay.
    groq = respx.post(f"{GROQ}/chat/completions").mock(
        return_value=httpx.Response(429, headers={"retry-after": "10"})
    )
    respx.post(f"{GEMINI}/chat/completions").mock(return_value=ok('{"claims": ["y"]}'))
    parsed, used = llm.json("extract", "sys", "user", Claims)
    assert used == "gemini/flash"
    assert groq.call_count == 1 and llm.sleeps == []


@respx.mock
def test_timeout_moves_straight_to_the_next_provider(llm):
    groq = respx.post(f"{GROQ}/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))
    respx.post(f"{GEMINI}/chat/completions").mock(return_value=ok('{"claims": []}'))
    _, used = llm.json("extract", "s", "u", Claims)
    assert used == "gemini/flash" and groq.call_count == 1 and llm.sleeps == []


@respx.mock
def test_all_fail_raises_unavailable(llm):
    respx.post(f"{GROQ}/chat/completions").mock(return_value=httpx.Response(429))
    respx.post(f"{GEMINI}/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(LLMUnavailable) as e:
        llm.json("extract", "sys", "user", Claims)
    assert "groq" in e.value.reason and "rate-limited" in e.value.reason
    assert "gemini" in e.value.reason and "timed out" in e.value.reason


@respx.mock
def test_egress_event_per_attempt(llm):
    respx.post(f"{GROQ}/chat/completions").mock(return_value=httpx.Response(503))
    respx.post(f"{GEMINI}/chat/completions").mock(return_value=ok('{"claims": []}'))
    llm.json("extract", "system prompt", "user text", Claims)
    assert len(llm.events) == 3
    assert [(e.provider, e.status) for e in llm.events] == [
        ("groq", "http_503"),
        ("groq", "http_503"),
        ("gemini", "ok"),
    ]
    assert all(
        e.task == "extract" and e.chars_sent == len("system prompt") + len("user text")
        for e in llm.events
    )
    assert not {"content", "text", "user", "system"} & set(EgressEvent.model_fields)  # no content


@respx.mock
def test_auth_error_skips_retry_and_moves_on(llm):
    groq = respx.post(f"{GROQ}/chat/completions").mock(return_value=httpx.Response(401))
    respx.post(f"{GEMINI}/chat/completions").mock(return_value=ok('{"claims": []}'))
    _, used = llm.json("extract", "s", "u", Claims)
    assert used == "gemini/flash" and groq.call_count == 1 and llm.sleeps == []


@respx.mock
def test_request_uses_json_mode_model_params_and_routing(llm):
    route = respx.post(f"{GROQ}/chat/completions").mock(return_value=ok('{"claims": []}'))
    llm.json("extract", "sys", "user", Claims)
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "gpt-oss-20b" and body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "low" and body["temperature"] == 0
    assert route.calls[0].request.headers["authorization"] == "Bearer g"
    llm.json("judge", "sys", "user", Claims)
    assert json.loads(route.calls[1].request.content)["model"] == "qwen"


def test_unconfigured_provider_is_skipped_with_reason():
    cfg = [
        ProviderCfg(name="groq", base_url=GROQ, api_key=None, region="us", models={"extract": "m"})
    ]
    with pytest.raises(LLMUnavailable) as e:
        LLM(cfg).json("extract", "s", "u", Claims)
    assert "not configured" in e.value.reason


def test_fake_llm_scripted_by_task_and_substring():
    fake = FakeLLM(
        {
            ("extract", "dark spots"): '{"claims": ["fade dark spots"]}',
            ("judge", "hype"): LLMUnavailable("groq rate-limited"),
        }
    )
    parsed, used = fake.json("extract", "sys", "text about dark spots", Claims)
    assert parsed.claims == ["fade dark spots"] and used == "fake/fake"
    with pytest.raises(LLMUnavailable):
        fake.json("judge", "sys", "so much hype", Claims)
    with pytest.raises(LLMUnavailable):
        fake.json("extract", "sys", "unscripted", Claims)


def test_default_chain_spills_over_to_a_second_groq_model_before_gemini():
    from plumbline.config import Settings
    from plumbline.llm import GEMINI_MODEL, GROQ_SPILLOVER_MODEL, default_chain

    s = Settings(
        _env_file=None,
        supabase_url="x",
        supabase_anon_key="y",
        groq_api_key="g",
        gemini_api_key="m",
    )
    chain = default_chain(s)
    assert [(p.name, p.models["judge"]) for p in chain] == [
        ("groq", "qwen/qwen3.8-27b"),
        ("groq", GROQ_SPILLOVER_MODEL),
        ("gemini", GEMINI_MODEL),
    ]


def test_asi1_joins_the_chain_only_where_llm_chain_puts_it():
    from plumbline.config import Settings
    from plumbline.llm import default_chain

    s = Settings(
        _env_file=None,
        supabase_url="x",
        supabase_anon_key="y",
        groq_api_key="g",
        gemini_api_key="m",
        asi1_api_key="a",
        llm_chain=["groq", "gemini", "asi1"],
    )
    last = default_chain(s)[-1]
    assert (last.name, last.base_url, last.models["judge"]) == (
        "asi1",
        "https://api.asi1.ai/v1",
        "asi1-mini",
    )
    assert "asi1" not in [
        p.name for p in default_chain(s.model_copy(update={"llm_chain": ["groq", "gemini"]}))
    ]
