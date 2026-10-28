"""Round 3, improvement 1: the claim watch.

After a post is approved the facts under its claims can change. `compute_tasks` compares what each live
post relied on (the report's `claims_used`, with the fact's digest at check time) with the facts now and
says which posts need an update-or-withdraw task. `check_page` re-reads a registered live URL, safely, and
says which approved sentences are gone or altered. Both are pure or injectable, so tests need no network.
Database access is through the narrow checker role (migration 0014), as for the gate.
"""

import html
import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from rapidfuzz import fuzz

from plumbline.config import Settings
from plumbline.connect import _json, _one
from plumbline.models import ApprovedWording, Fact

# ---- which posts need a task ------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskDraft:
    version_id: str
    content_id: str
    fact_id: str | None
    reason: str
    detail: str
    replacement: str | None
    owner: str | None


def _why(fact: Fact | None, used_digest: str, today: date) -> tuple[str, str] | None:
    """(reason, plain words) if the fact no longer carries the claim, in order of seriousness."""
    if fact is None:
        return "removed", "has been withdrawn from the fact ledger"
    if fact.valid_until and fact.valid_until < today:
        return "expired", f"expired on {fact.valid_until}"
    if not fact.verified:
        return "unverified", "is no longer verified"
    if fact.digest != used_digest:
        return "changed", "has changed since this post was approved"
    return None


def _replacement(
    fact: Fact, wordings: list[ApprovedWording], region: str, channel: str
) -> str | None:
    for w in wordings:
        if w.fact_id == fact.id and w.market == region and w.channel in (channel, "any"):
            return w.text
    return None


def compute_tasks(
    live: list[dict], facts: list[Fact], wordings: list[ApprovedWording], today: date
) -> list[TaskDraft]:
    """One draft per (post, fact), for the most serious reason. A fact that is restricted (confidential or
    embargoed) is never named: the task says only that a restricted fact changed, so no one learns its
    text from the task list."""
    by_id = {f.id: f for f in facts}
    out: list[TaskDraft] = []
    for post in live:
        seen: set[str] = set()
        for use in post.get("claims_used") or []:
            fid = use["fact_id"]
            if fid in seen:
                continue
            seen.add(fid)
            fact = by_id.get(fid)
            found = _why(fact, use["digest"], today)
            if not found:
                continue
            reason, words = found
            restricted = fact is not None and fact.code_only
            subject = "a restricted fact" if restricted else fid
            out.append(
                TaskDraft(
                    version_id=post["version_id"],
                    content_id=post["content_id"],
                    fact_id=fid,
                    reason=reason,
                    detail=f"The claim “{use['quote']}” relies on {subject}, which {words}.",
                    replacement=(
                        _replacement(fact, wordings, post["region"], post["channel"])
                        if fact and reason == "changed" and not restricted
                        else None
                    ),
                    owner=post.get("owner"),
                )
            )
    return out


# ---- re-reading a live page -------------------------------------------------------------------------

MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
TIMEOUT_S = 8.0
MATCH = 90  # fuzzy score at which an approved sentence counts as still on the page


class UnsafeUrl(Exception):
    pass


def check_url_is_public(url: str, resolve=socket.getaddrinfo) -> None:
    """Refuse anything that isn't a plain http(s) address of a public host, so the check can't be pointed
    at the checker's own network. ponytail: resolves, then httpx resolves again, so a host that changes its
    answer between the two (DNS rebinding) isn't covered; pin the IP if this ever takes untrusted input at
    scale. Today only a signed-in owner can register a URL."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeUrl("Use a full http or https address.")
    if p.username or p.password:
        raise UnsafeUrl("Addresses with a username or password aren't allowed.")
    try:
        infos = resolve(
            p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except OSError:
        raise UnsafeUrl("That host couldn't be found.") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsafeUrl("That address isn't a public website.")


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "head", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        elif tag in ("p", "br", "li", "div", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data)


def visible_text(markup: str) -> str:
    p = _Text()
    p.feed(markup)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape("".join(p.parts))).strip()


def fetch_page(url: str, client: httpx.Client | None = None, resolve=socket.getaddrinfo) -> str:
    """The page's visible text. Every hop is checked before it is requested; the body is capped."""
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=False)
    try:
        for _ in range(MAX_REDIRECTS + 1):
            check_url_is_public(url, resolve)
            with client.stream("GET", url, headers={"User-Agent": "PlumblineWatch/1.0"}) as r:
                if r.is_redirect and r.headers.get("location"):
                    url = urljoin(url, r.headers["location"])
                    continue
                r.raise_for_status()
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                return visible_text(
                    body[:MAX_BYTES].decode(r.encoding or "utf-8", errors="replace")
                )
        raise UnsafeUrl("Too many redirects.")
    finally:
        if own:
            client.close()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 20]


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _present(sentence: str, low_page: str) -> bool:
    """The sentence is on the page: a close fuzzy match whose numbers are exactly the same. A claim that
    quietly went from 32% in 8 weeks to 60% in 2 weeks is one character-ish away in fuzzy terms, so
    numbers are compared on their own."""
    s = sentence.lower()
    al = fuzz.partial_ratio_alignment(s, low_page)
    if al is None or al.score < MATCH:
        return False
    window = low_page[al.dest_start : al.dest_end]
    return sorted(_NUM.findall(s)) == sorted(_NUM.findall(window))


def drift(approved: str, page: str) -> dict:
    """Approved sentences that are missing or altered on the page. Extra text on the page is ignored."""
    low = page.lower()
    sentences = _sentences(approved)
    return {"checked": len(sentences), "missing": [s for s in sentences if not _present(s, low)]}


def page_result(approved: str, page_text: str) -> dict:
    d = drift(approved, page_text)
    return {"status": "drift" if d["missing"] else "ok", **d}


def drift_detail(result: dict) -> str:
    shown = "; ".join(f"“{s[:90]}”" for s in result["missing"][:3])
    n = len(result["missing"])
    return (
        f"{n} approved {'sentence is' if n == 1 else 'sentences are'} missing or changed on the live page: "
        f"{shown}."
    )


# ---- database (narrow role) -------------------------------------------------------------------------


def live(s: Settings, org: str) -> list[dict]:
    return _json(_one(s, "select public.watch_live(%s)", org))


def facts_and_wordings(s: Settings, org: str) -> tuple[list[Fact], list[ApprovedWording]]:
    raw = _json(_one(s, "select public.watch_facts(%s)", org))
    return (
        [Fact.model_validate(f) for f in raw["facts"]],
        [ApprovedWording.model_validate(w) for w in raw["wordings"]],
    )


def add_task(s: Settings, org: str, t: TaskDraft) -> bool:
    return _one(
        s,
        "select public.watch_task_add(%s, %s, %s, %s, %s, %s, %s, %s)",
        org,
        t.version_id,
        t.content_id,
        t.fact_id,
        t.reason,
        t.detail,
        t.replacement,
        t.owner,
    )


def scan(s: Settings, org: str, today: date) -> dict:
    """Open a task for every live post whose facts have moved. Safe to repeat: already-open tasks are
    skipped. Returns how many posts were looked at and how many tasks are new."""
    posts = live(s, org)
    facts, wordings = facts_and_wordings(s, org)
    drafts = compute_tasks(posts, facts, wordings, today)
    new = sum(1 for d in drafts if add_task(s, org, d))
    return {"posts": len(posts), "needing_attention": len(drafts), "new_tasks": new}


def tasks(s: Settings, org: str, status: str = "open", owner: str | None = None) -> list[dict]:
    return _json(_one(s, "select public.watch_tasks_list(%s, %s, %s)", org, status, owner))


def resolve_task(
    s: Settings, org: str, task_id: str, by: str, status: str, note: str | None
) -> int:
    return _one(
        s, "select public.watch_task_resolve(%s, %s, %s, %s, %s)", org, task_id, by, status, note
    )


def set_url(s: Settings, org: str, version_id: str, url: str, by: str) -> int:
    return _one(s, "select public.watch_url_set(%s, %s, %s, %s)", org, version_id, url, by)


def urls(s: Settings, org: str) -> list[dict]:
    return _json(_one(s, "select public.watch_urls_list(%s)", org))


def check_registered_url(s: Settings, org: str, version_id: str, fetch=fetch_page) -> dict:
    """Re-read the registered page for a version; record the result; open a drift task if needed."""
    target = _json(_one(s, "select public.watch_url_target(%s, %s)", org, version_id))
    if not target:
        raise LookupError(version_id)
    try:
        result = page_result(target["text"], fetch(target["url"]))
    except UnsafeUrl as e:
        result = {"status": "unreachable", "error": str(e)}
    except (httpx.HTTPError, ValueError) as e:
        result = {"status": "unreachable", "error": f"Couldn't read the page ({type(e).__name__})."}
    _one(
        s, "select public.watch_url_result(%s, %s, %s::jsonb)", org, version_id, json.dumps(result)
    )
    if result["status"] == "drift":
        add_task(
            s,
            org,
            TaskDraft(
                version_id,
                target["content_id"],
                None,
                "drift",
                drift_detail(result),
                None,
                target["owner"],
            ),
        )
    return result
