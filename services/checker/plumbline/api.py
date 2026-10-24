"""FastAPI app: health, checks (full pipeline, persisted as the caller), and submission."""

import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import BackgroundTasks, Body, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage
from uagents_core.envelope import Envelope
from uagents_core.utils.messages import parse_envelope

from plumbline import agent, audit, auth, db, ops, review
from plumbline import health as guideline
from plumbline.auth import ApiError, User
from plumbline.config import Settings
from plumbline.fixes import apply_fixes
from plumbline.llm import LLM, EgressEvent, default_chain
from plumbline.models import CheckReport, Document, Fix, Intent, OrgContext, ParseError
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check
from plumbline.routing import can_approve, can_decide
from plumbline.rules.linter import lint_rule
from plumbline.rules.load import load_rules_csv

VERSION = os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]
log = logging.getLogger("plumbline")
settings: Settings | None = None


def cfg() -> Settings:
    global settings
    if settings is None:
        settings = Settings()
    return settings


def warm_up() -> None:
    """Load the name gazetteer and the privacy NLP model (2.5 s locally, far longer on Render's
    shared CPU) before the first check needs them, instead of during it."""
    from plumbline import privacy

    privacy._names()
    privacy._analyzer()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # In the background: the port binds at once, so Render's wake-up and /health aren't delayed.
    threading.Thread(target=lambda: warm_up(), daemon=True, name="warm-up").start()
    yield


app = FastAPI(title="Plumbline checker", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX", r"https://plumbline[\w-]*\.vercel\.app"),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Server-Timing"],
)

FORM_OVERHEAD = 64 * 1024  # multipart boundaries and the small form fields around a file


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"code": code, "message": message, "request_id": ops.REQUEST_ID.get()}, status_code=status
    )


@app.middleware("http")
async def _ops(request: Request, call_next) -> Response:
    """Request id, a body-size cap before anything is read, timings, and one log line."""
    rid, phases = ops.new_request(request.headers.get("x-request-id"))
    t0 = time.perf_counter()
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > cfg().max_upload_mb * 1024 * 1024 + FORM_OVERHEAD:
        response: Response = _error(
            413, "too_large", f"That's over the {cfg().max_upload_mb} MB limit. Try a smaller file."
        )
    else:
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error, request %s", rid)
            response = _error(
                500,
                "internal",
                f"Something went wrong on the checker. Try again; if it keeps happening, quote reference {rid}.",
            )
    total = (time.perf_counter() - t0) * 1000
    response.headers["X-Request-ID"] = rid
    response.headers["Server-Timing"] = ops.server_timing(phases, total)
    ops.log_request(rid, request.method, request.url.path, response.status_code, total, phases)
    return response


@app.exception_handler(ApiError)
def _api_error(_request: Request, e: ApiError) -> JSONResponse:
    return _error(e.status, e.code, e.message)


@app.exception_handler(ParseError)
def _parse_error(_request: Request, e: ParseError) -> JSONResponse:
    return _error(422, e.code, str(e))


@app.exception_handler(httpx.TransportError)
def _db_unreachable(_request: Request, _e: httpx.TransportError) -> JSONResponse:
    return _error(503, "db_unavailable", "The database is not reachable. Try again shortly.")


def db_ok(s: Settings) -> bool:
    try:
        r = httpx.get(
            f"{s.supabase_url.rstrip('/')}/auth/v1/health",
            headers={"apikey": s.supabase_anon_key},
            timeout=3,
        )
        return r.status_code == 200
    except httpx.HTTPError:
        return False


@app.get("/health")
def health() -> dict:
    s = cfg()
    return {
        "status": "ok",
        "version": VERSION,
        "providers": {"groq": bool(s.groq_api_key), "gemini": bool(s.gemini_api_key)},
        "db": db_ok(s),
    }


def user(request: Request) -> User:
    with ops.phase("auth"):
        return auth.current_user(request, cfg())


CurrentUser = Annotated[User, Depends(user)]


def org_context(u: CurrentUser) -> OrgContext:
    try:
        # What a role can see of the rulebook depends only on its org and role (RLS), so that's
        # the key. A rule import clears it; other edits show within a minute.
        with ops.phase("rulebook"):
            return ops.cached(
                ("rulebook", u.org_id, u.role),
                lambda: db.load_org_context(cfg(), u.token, u.org_id),
            )
    except httpx.HTTPError:
        raise ApiError(
            503, "db_unavailable", "The database is not reachable. Try again shortly."
        ) from None


ORIGIN = {"external_creator": "agency"}  # everyone else writes as an employee
SEES_CONFIDENTIAL = {"reviewer", "compliance", "brand_owner", "auditor"}  # via RLS (migration 0002)
CONFIDENTIAL_UNAVAILABLE = (
    "Confidential facts couldn't be loaded, so they weren't checked this time."
)
NOT_FOUND = ApiError(404, "not_found", "That content doesn't exist, or it isn't yours to check.")


def _today():
    """Embargo and expiry dates are Indian business dates, whatever the server's time zone."""
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _report(
    u: User, ctx: OrgContext, doc: Document, intent: Intent, *, submit: bool
) -> tuple[CheckReport, list[EgressEvent], db.ReportCache]:
    """Run the full check as this user: their rulebook (RLS) plus confidential facts, which are
    matched in code and withheld from roles that may not see them."""
    s = cfg()
    secret: list | None = None
    if s.checker_database_url:
        try:
            with ops.phase("confidential"):
                secret = ops.cached(
                    ("confidential", u.org_id), lambda: db.load_confidential_facts(s, u.org_id)
                )
        except Exception:  # the narrow role is unreachable: still check, but say so below
            secret = None
    known = {f.id for f in ctx.facts}
    full = ctx.model_copy(
        update={"facts": ctx.facts + [f for f in secret or [] if f.id not in known]}
    )
    events: list[EgressEvent] = []
    llm = LLM(default_chain(s), events.append)
    cache = db.ReportCache(s, u.token)
    try:
        with ops.phase("check"):
            report = run_check(doc, full, intent, u.role, not submit, llm, _today(), cache=cache)
    except httpx.HTTPError:
        raise ApiError(
            503, "db_unavailable", "The database is not reachable. Try again shortly."
        ) from None
    if secret is None and u.role not in SEES_CONFIDENTIAL:
        report.coverage.not_checked.append(CONFIDENTIAL_UNAVAILABLE)
    return report, events, cache


def _check_and_save(
    u: User,
    ctx: OrgContext,
    doc: Document,
    intent: Intent,
    *,
    submit: bool,
    content_id: str | None,
    title: str,
) -> CheckReport:
    s = cfg()
    report, events, cache = _report(u, ctx, doc, intent, submit=submit)
    try:
        with ops.phase("save"):
            content_id, version_id, record_ids = db.save_check(
                s,
                u.token,
                user_id=u.id,
                org_id=u.org_id,
                content_id=content_id,
                title=title,
                channel=intent.channel,
                region=intent.region,
                origin=ORIGIN.get(u.role, "employee"),
                doc=doc.model_dump(mode="json"),
                intent=intent.model_dump(mode="json"),
                private=not submit,
                status="submitted" if submit else "precheck",
                report=report.model_dump(mode="json"),
                rulebook_version=ctx.rulebook_version,
                cache_key=cache.key,
                egress=[e.model_dump(mode="json") for e in events],
            )
    except httpx.HTTPError as e:
        reason = e.response.text[:500] if isinstance(e, httpx.HTTPStatusError) else repr(e)
        log.error(
            "saving check %s failed: %s", report.run_id, reason
        )  # the DB's reason, no content
        raise ApiError(
            503, "db_unavailable", "The check ran but couldn't be saved. Try again shortly."
        ) from None
    ids = iter(record_ids)
    findings = [f.model_copy(update={"record_id": next(ids, None)}) for f in report.findings]
    needs_human = [f.model_copy(update={"record_id": next(ids, None)}) for f in report.needs_human]
    return report.model_copy(
        update={
            "version_id": version_id,
            "checked_text": doc.text,
            "content_id": content_id,
            "findings": findings,
            "needs_human": needs_human,
        }
    )


@app.post("/v1/checks", response_model=CheckReport)
def create_check(
    u: CurrentUser,
    ctx: Annotated[OrgContext, Depends(org_context)],
    channel: Annotated[str, Form()],
    region: Annotated[str, Form()],
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    intent_json: Annotated[str | None, Form()] = None,
    content_id: Annotated[str | None, Form()] = None,
    submit: Annotated[bool, Form()] = False,
    # For an image uploaded on its own: the writer's alt text, or a decorative flag (WCAG 1.1.1).
    alt_text: Annotated[str | None, Form(max_length=1000)] = None,
    decorative: Annotated[bool, Form()] = False,
) -> CheckReport:
    s = cfg()
    limit = s.max_upload_mb * 1024 * 1024
    if text:
        name, data = "paste.txt", text.encode()
    elif file is not None:
        name, data = (
            file.filename or "upload",
            file.file.read(limit + 1),
        )  # never read more than the cap
    else:
        raise ParseError("empty")
    try:
        intent = Intent.model_validate(
            {**json.loads(intent_json or "{}"), "channel": channel, "region": region}
        )
    except (json.JSONDecodeError, ValueError):
        raise ApiError(
            422, "invalid_intent", "The intent couldn't be read. Try setting it again."
        ) from None
    if content_id and db.get_content(s, u.token, content_id) is None:
        raise NOT_FOUND
    with ops.phase("parse"):
        doc = parse_upload(name, data, s.max_upload_mb, alt_text=alt_text, decorative=decorative)
    title = next((line.strip() for line in doc.text.splitlines() if line.strip()), name)
    return _check_and_save(u, ctx, doc, intent, submit=submit, content_id=content_id, title=title)


@app.post("/v1/contents/{content_id}/submit", response_model=CheckReport)
def submit_content(
    u: CurrentUser, ctx: Annotated[OrgContext, Depends(org_context)], content_id: str
) -> CheckReport:
    """Submit the latest version: re-run as a non-private submission (confidential checks included)."""
    s = cfg()
    content = db.get_content(s, u.token, content_id)
    latest = db.latest_version(s, u.token, content_id) if content else None
    if not latest:
        raise NOT_FOUND
    doc = (
        Document.model_validate(latest["doc_json"])
        if latest.get("doc_json")
        else Document(format="text", text=latest["text"], blocks=[], images=[])
    )
    intent = Intent.model_validate(latest.get("intent_json") or {"channel": content["channel"]})
    # The writer's "ask a reviewer" notes were made on the pre-check; carry them to the same findings
    # (same rule, same place) in the submitted version, so the reviewer sees why.
    before = db.load_version(s, u.token, latest["id"]) if latest.get("id") else None
    old = CheckReport.model_validate(before["report"]) if before and before["report"] else None
    by_record = {f.record_id: f.id for f in (old.findings if old else []) if f.record_id}
    asked = {
        by_record[e["finding_id"]]: e["reason"]
        for e in db.escalations(s, u.token, list(by_record))
        if e["finding_id"] in by_record
    }
    new = _check_and_save(
        u, ctx, doc, intent, submit=True, content_id=content_id, title=content["title"]
    )
    for f in new.findings:
        if f.id in asked and f.record_id:
            db.insert_decision(
                s,
                u.token,
                org_id=u.org_id,
                user_id=u.id,
                finding_id=f.record_id,
                action="escalate",
                reason=asked[f.id],
            )
    return new


@app.post("/v1/versions/{version_id}/apply", response_model=CheckReport)
def apply_accepted(
    u: CurrentUser,
    ctx: Annotated[OrgContext, Depends(org_context)],
    version_id: str,
    accepted: Annotated[list[str], Body()] = (),
    edits: Annotated[dict[str, str], Body()] = None,
) -> CheckReport:
    """Apply the writer's accepted fixes and edits (record ids), record those decisions, and re-check
    the result as the next version. Offsets are applied here, in the same units the checker used."""
    s = cfg()
    edits = edits or {}
    v = db.load_version(s, u.token, version_id)
    if not v or not v["report"]:
        raise NOT_FOUND
    report = CheckReport.model_validate(v["report"])
    by_record = {f.record_id: f for f in report.findings + report.needs_human if f.record_id}
    chosen = [
        by_record[r]
        for r in accepted
        if r in by_record and by_record[r].fix and by_record[r].fix.kind != "none"
    ]
    chosen += [
        by_record[r].model_copy(update={"fix": Fix(kind="rewrite", text=t)})
        for r, t in edits.items()
        if r in by_record
    ]
    if not chosen:
        raise ApiError(
            422, "nothing_to_apply", "Choose at least one fix to accept, or edit a finding."
        )
    text = apply_fixes(v["doc"].text, chosen, {f.id for f in chosen})
    db.record_decisions(
        s,
        u.token,
        org_id=u.org_id,
        user_id=u.id,
        accepted=[r for r in accepted if r in by_record],
        edits={r: t for r, t in edits.items() if r in by_record},
    )
    doc = parse_upload("paste.txt", text.encode(), s.max_upload_mb)
    intent = Intent.model_validate(v["intent"] or {})
    new = _check_and_save(
        u,
        ctx,
        doc,
        intent,
        submit=False,
        content_id=v["content_id"],
        title=next((ln.strip() for ln in text.splitlines() if ln.strip()), "Post"),
    )
    return new.model_copy(update={"previous_text": v["doc"].text})


@app.post("/v1/findings/{record_id}/decisions")
def decide(
    u: CurrentUser,
    record_id: str,
    action: Annotated[str, Body()],
    reason: Annotated[str | None, Body()] = None,
) -> dict:
    """A writer's own decisions: dismiss a non-blocking finding, or pass a blocking one to a reviewer
    ("escalate"). Both need a reason. Blocking findings can never be dismissed by the writer."""
    s = cfg()
    if action not in ("dismiss", "escalate"):
        raise ApiError(422, "unsupported_action", "Use Accept or Edit to change the text.")
    if not (reason or "").strip():
        raise ApiError(422, "reason_required", "Say why, so the reviewer knows.")
    finding = db.get_finding(s, u.token, record_id)
    if not finding:
        raise NOT_FOUND
    blocking = finding["severity"] == "blocking"
    if action == "dismiss" and blocking:
        raise ApiError(
            409,
            "blocking",
            "Blocking findings can't be dismissed. Fix or edit the text, or ask a reviewer.",
        )
    if action == "escalate" and not blocking:
        raise ApiError(
            422,
            "not_blocking",
            "Only blocking findings go to a reviewer; dismiss this one with a reason instead.",
        )
    db.insert_decision(
        s,
        u.token,
        org_id=u.org_id,
        user_id=u.id,
        finding_id=record_id,
        action=action,
        reason=reason.strip(),
    )
    return {"ok": True}


REVIEW_ROLES = {"reviewer", "compliance", "brand_owner", "accessibility", "auditor"}


def _reviewer(u: User) -> None:
    if u.role not in REVIEW_ROLES:
        raise ApiError(403, "forbidden", "Only reviewers can open the review queue.")


@app.get("/v1/health")
def guideline_health(u: CurrentUser, ctx: Annotated[OrgContext, Depends(org_context)]) -> dict:
    """Reviewer agreement per rule. Org-wide for reviewer roles; creators get their own work and
    no group breakdown (the views enforce both)."""
    rows, origins, synthetic = db.health(cfg(), u.token)
    assessed = guideline.assess(rows, {r.id: r for r in ctx.rules})
    org = u.role in REVIEW_ROLES
    return {
        "scope": "org" if org else "mine",
        "synthetic": synthetic and org,  # seeded history belongs to synthetic authors, never to you
        "unclear": sum(r["unclear"] for r in assessed),
        "min_decisions": guideline.MIN_DECISIONS,
        "rules": assessed,
        "by_origin": origins if org else None,
    }


AUDIT_RECENT = 200


def _audit_rows(u: User) -> tuple[list[dict], dict[str, str]]:
    if u.role not in REVIEW_ROLES:
        raise ApiError(403, "forbidden", "Only reviewers and auditors can export the audit log.")
    return db.audit_events(cfg(), u.token)


@app.get("/v1/audit/verify")
def audit_verify(u: CurrentUser) -> dict:
    """Recomputes every hash in the org's chain, plus the newest events for the audit page.
    Creators see only events about their own work (RLS, migration 0004); a chain with gaps can't
    be verified, so for them `valid` is null."""
    org = u.role in REVIEW_ROLES
    rows, names = db.audit_events(cfg(), u.token)
    recent = [
        {
            "id": r["id"],
            "at": r["at"],
            "who": names.get(r["actor"], "Someone"),
            "what": audit.describe(r["kind"], json.loads(r["payload"])),
            "reason": json.loads(r["payload"]).get("reason"),
            "kind": r["kind"],
            "entity_id": r["entity_id"],
            "hash": r["hash"],
        }
        for r in reversed(rows[-AUDIT_RECENT:])
    ]
    if not org:
        return {"scope": "mine", "valid": None, "length": len(rows), "broken_at": None} | {
            "recent": recent
        }
    return {"scope": "org"} | audit.verify_chain(rows) | {"recent": recent}


@app.get("/v1/audit/export.csv")
def audit_export(u: CurrentUser) -> Response:
    rows, _ = _audit_rows(u)
    return Response(
        audit.to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="plumbline-audit.csv"'},
    )


# Spec §4.5: each function edits only its own rules (enforced in the database by migration 0012).
RULE_OWNERS = {"brand_owner": "brand", "compliance": "compliance", "accessibility": "accessibility"}
RULES_CSV_LIMIT = 1024 * 1024


@app.get("/v1/rules")
def list_rules(u: CurrentUser, ctx: Annotated[OrgContext, Depends(org_context)]) -> dict:
    """The rulebook the checker runs, each rule with the linter's warnings."""
    return {
        "rulebook_version": ctx.rulebook_version,
        "can_import": u.role in RULE_OWNERS,
        "rules": [r.model_dump() | {"warnings": lint_rule(r)} for r in ctx.rules],
    }


@app.post("/v1/rules/import")
def import_rules(
    u: CurrentUser, file: Annotated[UploadFile, File()], dry_run: bool = False
) -> dict:
    """Upserts valid rows (never deletes). Rows that fail validation are skipped and listed; rules
    the linter flags still load (class C is kept, never run) and count as needing clarification."""
    if u.role not in RULE_OWNERS:
        raise ApiError(403, "forbidden", "Only rule owners can import rules.")
    data = file.file.read(RULES_CSV_LIMIT + 1)
    if len(data) > RULES_CSV_LIMIT:
        raise ApiError(413, "too_large", "The rules file is over 1 MB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(422, "not_csv", "That file isn't a UTF-8 CSV.") from None
    rules, rejected = load_rules_csv(text)
    mine = RULE_OWNERS[u.role]
    rejected += [
        f"{r.id}: owned by {r.owner_function}; only that function can edit it"
        for r in rules
        if r.owner_function != mine
    ]
    rules = [r for r in rules if r.owner_function == mine]
    warnings = {r.id: w for r in rules if (w := lint_rule(r))}
    if rules and not dry_run:
        db.upsert_rules(cfg(), u.token, [r.model_dump(mode="json") for r in rules])
        ops.clear_cache()  # the next check runs against the imported rules
    return {
        "dry_run": dry_run,
        "imported": len(rules),
        "need_clarification": len(warnings),
        "warnings": warnings,
        "rejected": rejected,
    }


@app.get("/v1/facts")
def list_facts(u: CurrentUser) -> dict:
    """The fact ledger as RLS lets this role see it, with approved wordings under each fact."""
    facts, wordings = db.list_facts(cfg(), u.token)
    today = _today()
    by_fact: dict[str, list[dict]] = {}
    for w in wordings:
        by_fact.setdefault(w["fact_id"], []).append(w)
    return {
        "today": today.isoformat(),
        "restricted": u.role not in SEES_CONFIDENTIAL,
        "facts": [
            f
            | {
                "expired": bool(f.get("valid_until"))
                and datetime.fromisoformat(f["valid_until"]).date() < today,
                "wordings": by_fact.get(f["id"], []),
            }
            for f in facts
        ],
    }


def _review(u: User, version_id: str) -> tuple[dict, CheckReport, dict]:
    data = db.load_review(cfg(), u.token, version_id)
    if not data or not data["report"]:
        raise NOT_FOUND
    report = CheckReport.model_validate(data["report"])
    return data, report, review.stage_state(report, data["decisions"], data["approvals"])


def _detail(u: User, version_id: str) -> dict:
    data, report, state = _review(u, version_id)
    names = data["names"]
    approved_by_me = {
        a["stage"] for a in data["approvals"] if a["actor"] == u.id and a["outcome"] == "approve"
    }
    return {
        "version": {
            k: data["version"][k] for k in ("id", "content_id", "n", "text", "status", "created_at")
        },
        "content": data["content"],
        "report": report.model_dump(mode="json"),
        "state": state,
        "decisions": [d | {"who": names.get(d["actor"], "Someone")} for d in data["decisions"]],
        "comments": [c | {"who": names.get(c["author"], "Someone")} for c in data["comments"]],
        "timeline": review.timeline(
            data["version"], report, data["decisions"], data["approvals"], names
        ),
        "can_decide": [
            f.record_id
            for f in report.findings + report.needs_human
            if f.record_id and can_decide(u.role, f)
        ],
        "can_approve": [
            st
            for st in state["pending"]
            if can_approve(u.role, st) and not (st == "second" and "first" in approved_by_me)
        ],
    }


@app.get("/v1/review/queue")
def review_queue(u: CurrentUser) -> list[dict]:
    """Submitted versions, riskiest first. Pre-checks are private, so they never appear."""
    _reviewer(u)
    d = db.review_queue(cfg(), u.token)
    rows = []
    for v in d["versions"]:
        if v["id"] not in d["reports"]:
            continue
        report = CheckReport.model_validate(d["reports"][v["id"]])
        ids = {f.record_id for f in report.findings + report.needs_human}
        rows.append(
            review.queue_row(
                v,
                d["contents"].get(v["content_id"], {}),
                report,
                [x for x in d["decisions"] if x["finding_id"] in ids],
                [a for a in d["approvals"] if a["version_id"] == v["id"]],
                d["names"],
            )
        )
    return review.risk_order(rows)


@app.get("/v1/review/{version_id}")
def review_detail(u: CurrentUser, version_id: str) -> dict:
    _reviewer(u)
    return _detail(u, version_id)


@app.post("/v1/review/{version_id}/decisions")
def review_decide(
    u: CurrentUser,
    version_id: str,
    record_id: Annotated[str, Body()],
    action: Annotated[str, Body()],
    reason: Annotated[str | None, Body()] = None,
) -> dict:
    _reviewer(u)
    if action not in ("uphold", "overrule"):
        raise ApiError(422, "unsupported_action", "Reviewers uphold or overrule a finding.")
    if not (reason or "").strip():
        raise ApiError(422, "reason_required", "Give a reason; it goes in the audit log.")
    data, report, _ = _review(u, version_id)
    finding = next(
        (f for f in report.findings + report.needs_human if f.record_id == record_id), None
    )
    if finding is None:
        raise NOT_FOUND
    if not can_decide(u.role, finding):
        raise ApiError(
            403,
            "not_your_decision",
            "This finding is decided by "
            + (
                "Compliance."
                if finding.category in ("claim", "confidential")
                else "the accessibility approver."
                if finding.category == "accessibility"
                else "a reviewer."
            ),
        )
    s = cfg()
    db.insert_decision(
        s,
        u.token,
        org_id=u.org_id,
        user_id=u.id,
        finding_id=record_id,
        action=action,
        reason=reason.strip(),
    )
    if data["version"]["status"] == "submitted":
        db.set_status(s, u.token, version_id, "in_review")
    return _detail(u, version_id)


@app.post("/v1/versions/{version_id}/approve")
def approve(
    u: CurrentUser,
    version_id: str,
    stage: Annotated[str, Body()],
    outcome: Annotated[str, Body()],
    reason: Annotated[str | None, Body()] = None,
) -> dict:
    _reviewer(u)
    if outcome not in ("approve", "request_changes"):
        raise ApiError(422, "unsupported_outcome", "Approve, or request changes.")
    data, report, state = _review(u, version_id)
    if stage not in state["required"]:
        raise ApiError(422, "stage_not_needed", f"This version doesn't need a {stage} approval.")
    if not can_approve(u.role, stage):
        raise ApiError(403, "not_your_stage", f"Your role can't approve the {stage} stage.")
    if outcome == "approve" and state["undecided_blocking"]:
        raise ApiError(
            409,
            "undecided",
            "Decide every blocking finding first: uphold or overrule it, with a reason.",
        )
    if outcome == "approve" and stage == "second" and "first" not in state["approved"]:
        raise ApiError(409, "first_missing", "The first approval comes before the second.")
    if outcome == "request_changes" and not (reason or "").strip():
        raise ApiError(422, "reason_required", "Say what needs to change.")
    s = cfg()
    try:
        db.add_approval(
            s,
            u.token,
            org_id=u.org_id,
            user_id=u.id,
            version_id=version_id,
            stage=stage,
            outcome=outcome,
            reason=(reason or "").strip() or None,
        )
    except db.SecondApproverError:
        raise ApiError(
            409, "same_approver", "A second approval must come from a different person."
        ) from None
    approvals = data["approvals"] + [
        {"actor": u.id, "stage": stage, "outcome": outcome, "at": "9999"}
    ]
    after = review.stage_state(report, data["decisions"], approvals)
    status = (
        "changes_requested"
        if outcome == "request_changes"
        else ("approved" if not after["pending"] else "in_review")
    )
    if status != data["version"]["status"]:
        db.set_status(s, u.token, version_id, status)
    return _detail(u, version_id)


@app.post("/v1/review/{version_id}/comments")
def comment(u: CurrentUser, version_id: str, body: Annotated[str, Body(embed=True)]) -> dict:
    if not body.strip():
        raise ApiError(422, "empty_comment", "Write something first.")
    _review(u, version_id)  # 404 if you can't see it
    db.add_comment(
        cfg(), u.token, org_id=u.org_id, user_id=u.id, version_id=version_id, body=body.strip()
    )
    return _detail(u, version_id)


# ---- Agentverse chat agent (ASI:One) ----


@app.get("/status")
def agent_status() -> dict:
    return {"status": "OK - Agent is running"}


def _agent_check(text: str) -> CheckReport:
    """The app's check, run as the demo agency writer; nothing is saved."""
    s = cfg()
    token = agent.demo_token(s)
    claims = auth.verify_token(token, s)
    profile = db.fetch_profile(s, token, claims["sub"])
    u = User(id=claims["sub"], org_id=profile["org_id"], role=profile["role"], token=token)
    ctx = ops.cached(
        ("rulebook", u.org_id, u.role), lambda: db.load_org_context(s, token, u.org_id)
    )
    doc = parse_upload("paste.txt", text.encode(), s.max_upload_mb)
    report, events, _ = _report(u, ctx, doc, Intent(), submit=False)
    log.info(  # counts only, never content
        "agent check %s: %d findings, %d model calls, %d chars sent",
        report.run_id,
        len(report.findings),
        len(events),
        sum(e.chars_sent for e in events),
    )
    return report


@app.post("/chat")
def agent_chat(env: Envelope, background: BackgroundTasks) -> dict:
    s = cfg()
    if not s.agent_seed_phrase:
        raise ApiError(404, "not_found", "The chat agent isn't enabled here.")
    me = agent.identity(s.agent_seed_phrase)
    try:
        valid = env.target == me.address and env.verify()
    except Exception:
        valid = False
    if not valid:
        raise ApiError(400, "bad_envelope", "The message isn't signed for this agent.")
    msg = parse_envelope(env, {ChatMessage, ChatAcknowledgement})
    if isinstance(msg, ChatMessage):
        background.add_task(agent.answer, env.sender, env.session, msg, me, _agent_check, s.app_url)
    return {}
