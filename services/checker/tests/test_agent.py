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
SETTINGS = Settings(
    _env_file=None, supabase_url="https://test.supabase.co", supabase_anon_key="anon"
)


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
    ((sender, _session, msg, me, check, _settings, url),) = client.calls
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
    monkeypatch.setattr(agent.connect, "link_for", lambda s, a: None)
    agent.answer(
        "s",
        uuid4(),
        ChatMessage([TextContent("hi")]),
        agent.identity(SEED),
        lambda t, o: 1 / 0,
        SETTINGS,
        "u",
    )
    assert sent[-1].text() == agent.HELP


# ---- Round 3: linking a chat address to a brand ----------------------------------------------------


class Brain:
    """Fakes for the database calls, remembering which org each check was run for."""

    def __init__(self, monkeypatch):
        self.links: dict[str, dict] = {}
        self.codes: dict[str, dict] = {"ABCD-2345": {"org_id": "org-A", "org_name": "Acme Foods"}}
        self.checked: list[tuple[str, str | None]] = []
        monkeypatch.setattr(agent, "_wrong", {})
        monkeypatch.setattr(agent, "_sent", {})
        for name, fn in {
            "link_for": lambda s, a: self.links.get(a),
            "unlink": lambda s, a, org=None: 1 if self.links.pop(a, None) else 0,
            "redeem_code": self.redeem,
        }.items():
            monkeypatch.setattr(agent.connect, name, fn)
        monkeypatch.setattr(
            agent, "_wrong", __import__("collections").defaultdict(__import__("collections").deque)
        )
        monkeypatch.setattr(
            agent, "_sent", __import__("collections").defaultdict(__import__("collections").deque)
        )

    def redeem(self, s, code, address):
        got = self.codes.pop(agent.connect.normalise_code(code), None)
        if got:
            self.links[address] = got
        return got

    def check(self, text, org_id):
        self.checked.append((text, org_id))
        return _claim_report()

    def say(self, sender, text):
        return agent.handle(text, sender, SETTINGS, self.check, "https://app")


@pytest.fixture
def brain(monkeypatch):
    return Brain(monkeypatch)


POST = "Clinically proven to fade dark spots by 60% in just 2 weeks, shop now."


def test_unlinked_senders_get_the_demo_brand_and_a_hint(brain):
    reply = brain.say("agent1a", POST)
    assert brain.checked == [(POST, None)]
    assert "Checked against the demo brand" in reply and "link <code>" in reply


def test_linking_then_checking_runs_against_that_org_only(brain):
    assert "Linked to Acme Foods" in brain.say("agent1a", "link abcd 2345")
    reply = brain.say("agent1a", POST)
    assert brain.checked == [(POST, "org-A")]
    assert reply.startswith("Checked against Acme Foods's rulebook")
    assert "demo brand" not in reply
    # Someone else's address is unaffected by that link.
    brain.say("agent1b", POST)
    assert brain.checked[-1] == (POST, None)


def test_the_org_comes_from_the_link_never_from_the_message(brain):
    brain.say("agent1a", "link ABCD-2345")
    brain.say("agent1a", "org_id org-B " + POST)  # a message naming another org changes nothing
    assert brain.checked[-1][1] == "org-A"


def test_a_code_works_once_and_a_bad_one_is_refused_politely(brain):
    assert "Linked" in brain.say("agent1a", "link ABCD-2345")
    assert brain.say("agent1b", "link ABCD-2345") == agent.BAD_CODE
    assert brain.say("agent1b", "link nonsense") == agent.BAD_CODE
    assert "agent1b" not in brain.links


def test_guessing_codes_is_rate_limited(brain):
    replies = [brain.say("agent1x", f"link AAAA-{i:04d}"[:14]) for i in range(7)]
    assert replies[:5] == [agent.BAD_CODE] * 5 and replies[5] == agent.TOO_MANY_TRIES


def test_unlink_goes_back_to_the_demo_brand(brain):
    brain.say("agent1a", "link ABCD-2345")
    assert brain.say("agent1a", "unlink").startswith("Unlinked")
    assert brain.say("agent1a", "unlink") == agent.NOT_LINKED
    brain.say("agent1a", POST)
    assert brain.checked[-1][1] is None


def test_a_post_that_starts_with_the_word_link_is_still_a_post(brain):
    brain.say("agent1a", "Link in bio for the new serum, shop now before it sells out")
    assert brain.checked and brain.checked[-1][1] is None


def test_with_connections_off_everyone_gets_the_demo_brand(brain, monkeypatch):
    def off(*a, **k):
        raise agent.connect.NotEnabled

    monkeypatch.setattr(agent.connect, "link_for", off)
    brain.say("agent1a", POST)
    assert brain.checked[-1][1] is None


def test_code_shapes():
    c = agent.connect.new_code()
    assert (
        len(c) == 9
        and c[4] == "-"
        and agent.connect.normalise_code(c.lower().replace("-", " ")) == c
    )
    assert agent.connect.normalise_code("short") == ""
    assert agent.connect.digest("a") != agent.connect.digest("b")


def test_a_leading_at_address_is_ignored_as_asi_one_adds_it(brain):
    at = "@agent1qdec79g6x8dfjkvklj2gr9gwr28ggrk5julydls9e00mrsxct6rxcym5p4p"
    assert "Linked to Acme Foods" in brain.say("agent1a", f"{at} link ABCD-2345")
    brain.say("agent1a", f"{at} {POST}")
    assert brain.checked[-1] == (POST, "org-A")
    assert "Unlinked" in brain.say("agent1a", f"{at} unlink")
