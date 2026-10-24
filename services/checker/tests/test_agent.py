"""The Agentverse chat agent: signed envelopes in, the app's check out, never a pass verdict."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
from uagents_core.identity import Identity
from uagents_core.models import Model
from uagents_core.utils.messages import generate_message_envelope

from plumbline import agent, api
from plumbline.config import Settings
from plumbline.models import Fix
from tests.test_api import _claim_report

SEED = "plumbline test agent seed"


@pytest.fixture
def client(monkeypatch):
    settings = Settings(
        _env_file=None,
        supabase_url="https://test.supabase.co",
        supabase_anon_key="anon",
        agent_seed_phrase=SEED,
    )
    monkeypatch.setattr(api, "settings", settings)
    calls = []
    monkeypatch.setattr(agent, "answer", lambda *a: calls.append(a))
    c = TestClient(api.app)
    c.calls = calls
    return c


def envelope(text: str, *, to: str | None = None, sender: Identity | None = None) -> dict:
    sender = sender or Identity.generate()
    msg = ChatMessage([TextContent(text)])
    env = generate_message_envelope(
        destination=to or agent.identity(SEED).address,
        message_schema_digest=Model.build_schema_digest(msg),
        message_body=json.loads(msg.model_dump_json()),
        sender=sender,
    )
    return json.loads(env.model_dump_json())


def test_status_answers_for_agentverse(client):
    assert client.get("/status").json() == {"status": "OK - Agent is running"}


def test_a_signed_chat_message_is_answered_in_the_background(client):
    r = client.post("/chat", json=envelope("Clinically proven to fade dark spots in 2 weeks."))
    assert r.status_code == 200
    ((sender, _session, msg, me, check, url),) = client.calls
    assert msg.text().startswith("Clinically proven") and me.address == agent.identity(SEED).address
    assert check is api._agent_check and url.startswith("https://")


def test_messages_for_another_agent_or_with_a_bad_signature_are_refused(client):
    assert (
        client.post("/chat", json=envelope("hi there", to=Identity.generate().address)).status_code
        == 400
    )
    forged = envelope("hello world again")
    forged["signature"] = envelope("something else entirely")["signature"]
    assert client.post("/chat", json=forged).status_code == 400
    assert client.calls == []


def test_the_agent_is_off_without_a_seed_phrase(client, monkeypatch):
    monkeypatch.setattr(api, "settings", api.settings.model_copy(update={"agent_seed_phrase": ""}))
    assert client.post("/chat", json=envelope("anything at all here")).status_code == 404


def test_reply_quotes_the_evidence_and_never_says_it_passed():
    report = _claim_report()
    report.findings[0].fix = Fix(
        kind="approved_wording", text="Shown to visibly reduce", ref_id="AW-014a"
    )
    text = agent.reply_text(report, "https://app")
    assert text.startswith("**1 issue blocks publishing.**")
    assert "CL-01 · FACT-014" in text and "“60% in 2 weeks”" in text
    assert "Approved wording (AW-014a): Shown to visibly reduce" in text
    assert "**Not checked:** x" in text and "https://app" in text
    clean = agent.reply_text(report.model_copy(update={"findings": []}), "https://app")
    assert clean.startswith("**Nothing blocks publishing in the checks that ran.**")
    for word in ("passed", "compliant", "all clear"):
        assert word not in (text + clean).lower()


def test_rate_limit_is_per_sender_and_slides():
    a, b = str(uuid4()), str(uuid4())
    assert all(agent.allowed(a, now=t) for t in range(5))
    assert not agent.allowed(a, now=5)
    assert agent.allowed(b, now=5)
    assert agent.allowed(a, now=601)


def test_short_messages_get_the_help_text_without_a_check(monkeypatch):
    sent = []
    monkeypatch.setattr(agent, "_send", lambda to, msg, me, session: sent.append(msg))
    agent.answer(
        "s", uuid4(), ChatMessage([TextContent("hi")]), agent.identity(SEED), lambda t: 1 / 0, "u"
    )
    assert sent[-1].text() == agent.HELP
