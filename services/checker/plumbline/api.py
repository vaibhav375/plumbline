"""FastAPI app: health, checks (full pipeline, persisted as the caller), and submission."""

import json
import logging
import os
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import Body, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from plumbline import auth, db
from plumbline.auth import ApiError, User
from plumbline.config import Settings
from plumbline.fixes import apply_fixes
from plumbline.llm import LLM, EgressEvent, default_chain
from plumbline.models import CheckReport, Document, Fix, Intent, OrgContext, ParseError
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check

VERSION = os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]
log = logging.getLogger("plumbline")
settings: Settings | None = None


def cfg() -> Settings:
    global settings
    if settings is None:
        settings = Settings()
    return settings


app = FastAPI(title="Plumbline checker", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX", r"https://plumbline[\w-]*\.vercel\.app"),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ApiError)
def _api_error(_request: Request, e: ApiError) -> JSONResponse:
    return JSONResponse({"code": e.code, "message": e.message}, status_code=e.status)


@app.exception_handler(ParseError)
def _parse_error(_request: Request, e: ParseError) -> JSONResponse:
    return JSONResponse({"code": e.code, "message": str(e)}, status_code=422)


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
    return auth.current_user(request, cfg())


CurrentUser = Annotated[User, Depends(user)]


def org_context(u: CurrentUser) -> OrgContext:
    try:
        return db.load_org_context(cfg(), u.token, u.org_id)
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
    secret: list | None = None
    if s.checker_database_url:
        try:
            secret = db.load_confidential_facts(s, u.org_id)
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
        report = run_check(doc, full, intent, u.role, not submit, llm, _today(), cache=cache)
    except httpx.HTTPError:
        raise ApiError(
            503, "db_unavailable", "The database is not reachable. Try again shortly."
        ) from None
    if secret is None and u.role not in SEES_CONFIDENTIAL:
        report.coverage.not_checked.append(CONFIDENTIAL_UNAVAILABLE)
    try:
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
    doc = parse_upload(name, data, s.max_upload_mb)
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
    return _check_and_save(
        u, ctx, doc, intent, submit=True, content_id=content_id, title=content["title"]
    )


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
    """A writer's dismissal (reason required). Blocking findings can't be dismissed: they need a fix,
    an edit, or a reviewer's decision."""
    s = cfg()
    if action != "dismiss":
        raise ApiError(
            422,
            "unsupported_action",
            "Use Accept or Edit to change the text; only Dismiss is recorded here.",
        )
    if not (reason or "").strip():
        raise ApiError(422, "reason_required", "Say why you're dismissing this finding.")
    finding = db.get_finding(s, u.token, record_id)
    if not finding:
        raise NOT_FOUND
    if finding["severity"] == "blocking":
        raise ApiError(
            409,
            "blocking",
            "Blocking findings can't be dismissed. Fix or edit the text, or submit it for a reviewer to decide.",
        )
    db.insert_decision(
        s,
        u.token,
        org_id=u.org_id,
        user_id=u.id,
        finding_id=record_id,
        action="dismiss",
        reason=reason.strip(),
    )
    return {"ok": True}
