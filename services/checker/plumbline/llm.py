"""The only way Plumbline talks to a model: an OpenAI-compatible provider chain in JSON mode.

Each call tries providers in order; one retry per provider on rate limits, server errors,
timeouts or unreadable JSON; then the next provider. Every attempt emits an EgressEvent (no
content, only counts), and when everything fails the caller gets LLMUnavailable with a reason
in plain words for the coverage statement.
"""

import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

from plumbline.config import Settings

Task = Literal["extract", "judge", "support", "rewrite"]
TIMEOUT_S = 20.0
MAX_BACKOFF_S = 3.0

# Measured 22 Oct: lower reasoning effort halves tokens on gpt-oss and Gemini with the same
# JSON output, which matters under Groq's free limit of 8,000 tokens per minute per model.
GROQ_MODELS = {
    "extract": "openai/gpt-oss-20b",
    "support": "openai/gpt-oss-20b",
    "judge": "qwen/qwen3.8-27b",
    "rewrite": "qwen/qwen3.8-27b",
}
GROQ_PARAMS = {
    "openai/gpt-oss-20b": {"reasoning_effort": "low"},
    "qwen/qwen3.8-27b": {"reasoning_effort": "none"},
}
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_PARAMS = {GEMINI_MODEL: {"reasoning_effort": "none"}}

PLAIN = {
    "rate_limited": "rate-limited",
    "timeout": "timed out",
    "invalid_json": "returned unreadable output",
    "server_error": "had a server error",
    "rejected": "rejected the request",
    "network": "was unreachable",
    "not_configured": "not configured",
}


class ProviderCfg(BaseModel):
    name: Literal["groq", "gemini", "ollama"]
    base_url: str
    api_key: str | None
    region: str
    models: dict[str, str]  # task -> model id
    params: dict[str, dict] = {}  # model id -> extra request fields


class EgressEvent(BaseModel):
    """One outbound model call. Deliberately has no field for the text that was sent."""

    provider: str
    model: str
    region: str
    task: str
    chars_sent: int
    status: str  # "ok", "http_429", "timeout", "invalid_json", ...
    ms: int
    at: datetime


class LLMUnavailable(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def _kind(status: str) -> str:
    if status == "http_429":
        return "rate_limited"
    if status.startswith("http_5"):
        return "server_error"
    if status.startswith("http_"):
        return "rejected"
    return status


class LLM:
    def __init__(
        self,
        chain: list[ProviderCfg],
        egress_sink: Callable[[EgressEvent], None] = lambda e: None,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.chain = chain
        self.sink = egress_sink
        self.client = client or httpx.Client(timeout=TIMEOUT_S)
        self.sleep = sleep

    def _attempt(
        self, p: ProviderCfg, model: str, task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel | None, str, float]:
        """One call: (parsed or None, status, seconds to wait before a retry)."""
        body = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            **p.params.get(model, {}),
        }
        started = time.perf_counter()
        parsed, wait = None, 0.5
        try:
            r = self.client.post(
                f"{p.base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {p.api_key}"},
            )
            if r.status_code != 200:
                status = f"http_{r.status_code}"
                try:
                    wait = float(r.headers.get("retry-after", wait))
                except ValueError:
                    pass
            else:
                content = r.json()["choices"][0]["message"]["content"] or ""
                content = _FENCE.sub("", _THINK.sub("", content).strip())
                parsed, status = schema.model_validate_json(content), "ok"
        except httpx.TimeoutException:
            status = "timeout"
        except httpx.HTTPError:
            status = "network"
        except (ValidationError, ValueError, KeyError, IndexError, TypeError):
            status = "invalid_json"
        self.sink(
            EgressEvent(
                provider=p.name,
                model=model,
                region=p.region,
                task=task,
                chars_sent=len(system) + len(user),
                status=status,
                ms=round((time.perf_counter() - started) * 1000),
                at=datetime.now(UTC),
            )
        )
        return parsed, status, min(wait, MAX_BACKOFF_S)

    def model_for(self, task: str) -> str | None:
        """The model the first configured provider would use for a task."""
        for p in self.chain:
            if p.api_key and p.models.get(task):
                return p.models[task]
        return None

    def json[T: BaseModel](
        self, task: Task, system: str, user: str, schema: type[T]
    ) -> tuple[T, str]:
        failures: list[str] = []
        for p in self.chain:
            model = p.models.get(task)
            if not model or not p.api_key:
                failures.append(f"{p.name} {PLAIN['not_configured']}")
                continue
            for attempt in (1, 2):
                parsed, status, wait = self._attempt(p, model, task, system, user, schema)
                if parsed is not None:
                    return parsed, f"{p.name}/{model}"
                kind = _kind(status)
                if kind == "rejected" or attempt == 2:  # auth/bad request won't fix itself on retry
                    failures.append(f"{p.name} {PLAIN.get(kind, kind)}")
                    break
                self.sleep(wait)
        raise LLMUnavailable(", ".join(failures) or "no providers configured")


class FakeLLM(LLM):
    """Tests: responses keyed by (task, substring of the user message): a JSON string, or an
    exception to raise. Unscripted calls raise LLMUnavailable so gaps in a test are loud."""

    def __init__(
        self,
        responses: dict[tuple[str, str], str | Exception],
        egress_sink: Callable[[EgressEvent], None] = lambda e: None,
    ):
        super().__init__([], egress_sink)
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def json[T: BaseModel](
        self, task: Task, system: str, user: str, schema: type[T]
    ) -> tuple[T, str]:
        self.calls.append((task, user))
        for (t, needle), reply in self.responses.items():
            if t == task and needle in user:
                if isinstance(reply, Exception):
                    raise reply
                return schema.model_validate_json(reply), "fake/fake"
        raise LLMUnavailable(f"FakeLLM has no scripted reply for {task!r}")


def default_chain(s: Settings) -> list[ProviderCfg]:
    providers = {
        "groq": ProviderCfg(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=s.groq_api_key or None,
            region="us",
            models=GROQ_MODELS,
            params=GROQ_PARAMS,
        ),
        "gemini": ProviderCfg(
            name="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=s.gemini_api_key or None,
            region="global",
            models=dict.fromkeys(GROQ_MODELS, GEMINI_MODEL),
            params=GEMINI_PARAMS,
        ),
        "ollama": ProviderCfg(
            name="ollama",
            base_url=s.ollama_base_url,
            api_key="ollama",
            region="local",
            models=dict.fromkeys(GROQ_MODELS, "qwen3:8b"),
        ),
    }
    return [providers[name] for name in s.llm_chain if name in providers]
