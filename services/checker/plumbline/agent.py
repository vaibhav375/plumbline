"""Plumbline as an Agentverse chat agent, so ASI:One users can check a post from chat.

A message is checked exactly as the app checks it, as the demo agency writer: confidential facts
are matched but their findings withheld, and nothing is saved. The reply is plain text with the
same evidence the app shows (rule or fact ID, the quoted words, the approved wording).
"""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import UUID

import httpx
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
)
from uagents_core.identity import Identity
from uagents_core.utils.messages import send_message_to_agent

from plumbline import connect
from plumbline.config import Settings
from plumbline.models import CheckReport, Finding

log = logging.getLogger("plumbline.agent")

MAX_CHARS = 5000
SHOWN = 8  # findings listed in a reply; the rest are counted
RATE = (5, 600.0)  # checks per sender per 10 minutes: each one spends free model quota
HELP = (
    "Send me the text of a marketing post and I'll check it against a brand's rulebook and fact "
    "ledger. I quote the exact words that break a rule or aren't backed by evidence, and give the "
    "approved wording where one exists. By default I check against the demo brand, Aurelle Skin (a "
    "fictional brand). To check against your own brand, a brand owner creates a link code in Plumbline "
    '(Connect page); send me: link ABCD-2345. Send "unlink" to go back to the demo brand.'
)
BUSY = "You've sent several checks in a short time. Try again in a few minutes."
FAILED = "The checker couldn't finish this check. Try again in a minute."
BAD_CODE = (
    "That code isn't valid, or it has expired or was already used. A brand owner can create a new "
    "one in Plumbline (Connect page); codes last 15 minutes."
)
TOO_MANY_TRIES = "Too many link attempts. Try again in a few minutes."
NOT_LINKED = "You're not linked to a brand, so I check against the demo brand."
DEMO_NOTE = (
    "Checked against the demo brand (Aurelle Skin). To use your own brand, send: link <code> "
    "(a brand owner creates one in Plumbline > Connect)."
)

_sent: dict[str, deque[float]] = defaultdict(deque)
_wrong: dict[str, deque[float]] = defaultdict(deque)
_token: tuple[str, float] | None = None


def identity(seed: str) -> Identity:
    return Identity.from_seed(seed, 0)


def allowed(
    sender: str,
    now: float | None = None,
    store: dict[str, deque[float]] | None = None,
    limit: int | None = None,
) -> bool:
    """A sliding window per sender. ponytail: in-memory, so it resets on restart and isn't shared
    across instances; move it to the database if the checker ever runs more than one."""
    now = time.monotonic() if now is None else now
    window = RATE[1]
    limit = RATE[0] if limit is None else limit
    q = (_sent if store is None else store)[sender]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def demo_token(s: Settings) -> str:
    """An access token for the demo agency account, reused until a minute before it expires."""
    global _token
    if _token and _token[1] > time.time() + 60:
        return _token[0]
    r = httpx.post(
        f"{s.supabase_url.rstrip('/')}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": s.supabase_anon_key},
        json={"email": s.agent_demo_email, "password": s.demo_user_password},
        timeout=10,
    )
    r.raise_for_status()
    body = r.json()
    _token = (body["access_token"], time.time() + float(body.get("expires_in", 3600)))
    return _token[0]


def _blocking(f: Finding) -> bool:
    return f.severity == "blocking" and not f.advisory


def reply_text(report: CheckReport, app_url: str) -> str:
    """The report in words. Like the app, it never says a post passed: only what blocks, what
    was found, and what wasn't checked."""
    findings = sorted(report.findings, key=lambda f: (not _blocking(f), f.advisory))
    blocking = sum(_blocking(f) for f in findings)
    if blocking:
        head = f"**{blocking} {'issue blocks' if blocking == 1 else 'issues block'} publishing.**"
    else:
        head = "**Nothing blocks publishing in the checks that ran.**"
    lines = [head, ""]
    for n, f in enumerate(findings[:SHOWN], 1):
        label = "Blocking" if _blocking(f) else "Advisory" if f.advisory else f.severity.title()
        ids = " · ".join(i for i in (f.rule_id, f.fact_id) if i)
        lines.append(f"{n}. **{label} · {ids}**: “{f.quote}”")
        lines.append(f"   {f.explanation}")
        fix = f.fix
        if fix and fix.kind == "approved_wording" and fix.text:
            lines.append(f"   Approved wording ({fix.ref_id}): {fix.text}")
            if fix.footnote:
                lines.append(f"   It must carry: {fix.footnote}")
        elif fix and fix.kind in ("replace_term", "rewrite") and fix.text:
            lines.append(f"   Suggested: “{f.quote}” → “{fix.text}”")
        elif fix and fix.kind == "remove":
            lines.append("   Fix: remove this sentence.")
    if len(findings) > SHOWN:
        lines.append(f"…and {len(findings) - SHOWN} more in the app.")
    if report.needs_human:
        lines.append(f"\n{len(report.needs_human)} more need a person to decide.")
    if report.coverage.ai_note:
        lines.append(f"\n{report.coverage.ai_note}")
    lines.append("\n**Not checked:** " + " ".join(report.coverage.not_checked))
    lines.append(f"\nFix, re-check and send it for review in Plumbline: {app_url}")
    return "\n".join(lines)


def _send(to: str, msg, me: Identity, session: UUID) -> None:
    send_message_to_agent(to, msg, me, session_id=session, track_interaction=False)


def handle(
    text: str,
    sender: str,
    s: Settings,
    check: Callable[..., CheckReport],
    app_url: str,
) -> str:
    """What to say back to one message. A linked address is checked against its own brand (the org comes
    only from the link row, never from the message); anyone else against the demo brand."""
    text = text.strip()
    first, _, rest = text.partition(" ")
    word = first.lower()
    words = len(text.split())
    try:
        if word == "link" and words <= 3 and (words == 1 or connect.normalise_code(rest)):
            if not allowed(sender, store=_wrong, limit=5):
                return TOO_MANY_TRIES
            got = connect.redeem_code(s, rest, sender)
            if not got:
                return BAD_CODE
            _wrong.pop(sender, None)
            return (
                f"Linked to {got['org_name']}. I'll check your posts against its rulebook and facts "
                "(as an agency writer: confidential checks run when a post is submitted in Plumbline). "
                'Send me a post to try it, or "unlink".'
            )
        if word == "unlink" and words == 1:
            return (
                "Unlinked. I'll check against the demo brand again."
                if connect.unlink(s, sender)
                else NOT_LINKED
            )
        link = connect.link_for(s, sender)
    except connect.NotEnabled:
        link = None  # connections are off here: everyone gets the demo brand
    if words < 4:  # a greeting or a question about the agent, not a post
        return HELP
    if not allowed(sender):
        return BUSY
    report = check(text[:MAX_CHARS], link["org_id"] if link else None)
    body = reply_text(report, app_url)
    if link:
        return f"Checked against {link['org_name']}'s rulebook and facts.\n\n{body}"
    return f"{body}\n\n{DEMO_NOTE}"


def answer(
    sender: str,
    session: UUID,
    msg: ChatMessage,
    me: Identity,
    check: Callable[..., CheckReport],
    s: Settings,
    app_url: str,
) -> None:
    """Acknowledge, reply. Runs after the HTTP request has returned."""
    _send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id), me, session)
    try:
        reply = handle(msg.text(), sender, s, check, app_url)
    except Exception:
        log.exception("agent check failed")  # no content is logged
        reply = FAILED
    _send(sender, ChatMessage([TextContent(reply), EndSessionContent()]), me, session)
