"""Request ids, phase timings and one structured log line per request. Nothing here records what a
user wrote: the log line has the route, status and timings only."""

import contextvars
import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
PHASES: contextvars.ContextVar[dict[str, float] | None] = contextvars.ContextVar(
    "phases", default=None
)
# A caller's id is echoed only if it can't inject anything.
SAFE_ID = re.compile(r"[A-Za-z0-9-]{1,64}")

log = logging.getLogger("plumbline.request")
if not log.handlers:  # Render collects stdout; uvicorn configures only its own loggers
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)


def new_request(incoming: str | None) -> tuple[str, dict[str, float]]:
    rid = incoming if incoming and SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex[:16]
    phases: dict[str, float] = {}
    REQUEST_ID.set(rid)
    # A shared dict: sync endpoints run in a copied context, but they mutate this same object.
    PHASES.set(phases)
    return rid, phases


@contextmanager
def phase(name: str) -> Iterator[None]:
    """Time a step of the request; shows up in Server-Timing and the log line."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        phases = PHASES.get()
        if phases is not None:
            phases[name] = phases.get(name, 0.0) + (time.perf_counter() - t0) * 1000


def server_timing(phases: dict[str, float], total_ms: float) -> str:
    return ", ".join(f"{k};dur={v:.0f}" for k, v in {**phases, "total": total_ms}.items())


def log_request(rid: str, method: str, path: str, status: int, ms: float, phases: dict) -> None:
    log.info(
        json.dumps(
            {
                "request_id": rid,
                "method": method,
                "path": path,
                "status": status,
                "ms": round(ms),
                "phases": {k: round(v) for k, v in phases.items()},
            }
        )
    )
