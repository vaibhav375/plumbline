"""FastAPI app. Task 6 skeleton: the check runs code rules only; Task 14 replaces the stub
with the full pipeline (AI, validators, persistence)."""

import json
import os
import time
import uuid
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from plumbline import auth, db
from plumbline.auth import ApiError, User
from plumbline.config import Settings
from plumbline.models import DEFAULT_NOT_CHECKED, CheckReport, Coverage, OrgContext, ParseError
from plumbline.parsers import parse_upload
from plumbline.rules.engine import run_rules

VERSION = os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]
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


def _stub_coverage(ctx: OrgContext, doc) -> Coverage:
    ran = [r for r in ctx.rules if r.cls != "C" and r.check_type != "ai_rule"]
    not_run = {
        r.id: "Judgement only (class C): stays in the rulebook, never run."
        for r in ctx.rules
        if r.cls == "C"
    }
    not_run |= {
        r.id: "AI rule: AI checks are not connected in this build."
        for r in ctx.rules
        if r.cls != "C" and r.check_type == "ai_rule"
    }
    not_checked = [DEFAULT_NOT_CHECKED]
    if any(b.busy_background for i in doc.images for b in i.ocr):
        not_checked.append(
            "Contrast of text over photo-like backgrounds (colours can't be measured reliably)."
        )
    return Coverage(
        rules_run=[r.id for r in ran],
        rules_advisory=[r.id for r in ran if not r.blocks],
        rules_not_run=not_run,
        not_checked=not_checked,
        ai_status="unavailable",
        ai_note=(
            "AI checks did not run: not connected in this build. Code checks above are complete."
        ),
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
    started = time.perf_counter()
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
    if intent_json:
        try:
            json.loads(intent_json)
        except json.JSONDecodeError:
            raise ApiError(
                422, "invalid_intent", "The intent couldn't be read. Try setting it again."
            ) from None
    doc = parse_upload(name, data, s.max_upload_mb)
    findings = run_rules(doc, ctx.rules, ctx.terms)
    ms_code = round((time.perf_counter() - started) * 1000)
    return CheckReport(
        run_id=str(uuid.uuid4()),
        version_id=None,
        findings=findings,
        coverage=_stub_coverage(ctx, doc),
        ms_code=ms_code,
        ms_total=round((time.perf_counter() - started) * 1000),
    )
