"""Campus Customs Ops Desk API.

    cd backend && uvicorn main:app --reload --port 8000

All shop data goes through the campus-customs MCP server (backend/shop.py). Money only moves
from the human approve route.
"""
import asyncio
import os
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

# Works both as `uvicorn main:app` from inside backend/ and as `uvicorn backend.main:app` from the root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend.audit import AuditTrail  # noqa: E402
from backend.config import AUDIT_PATH, ROOT  # noqa: E402
from backend.shop import ShopClient, ShopError  # noqa: E402
from backend.team import create_team  # noqa: E402

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"
DEFAULT_APPROVER = "human (board)"


class RunRecord:
    """In-memory state of one agent run."""

    def __init__(self, run_id: str, ticket_id: int):
        self.run_id = run_id
        self.ticket_id = ticket_id
        self.finished = False
        self.error: Optional[str] = None
        self.result: Optional[dict[str, Any]] = None


class ApprovalBody(BaseModel):
    approved_by: str = DEFAULT_APPROVER


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runs = {}
    app.state.active_run = None  # run_id of the run in progress, if any
    app.state.audit = AuditTrail(AUDIT_PATH)
    async with ShopClient() as shop:
        app.state.shop = shop
        yield


app = FastAPI(title="Campus Customs Ops Desk", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# -- tickets and runs ------------------------------------------------------------------------
@app.get("/api/tickets")
async def get_tickets():
    data = await app.state.shop.call("list_tickets")
    return {"tickets": data["tickets"]}


async def _run_in_background(run_id: str, ticket_id: int) -> None:
    record: RunRecord = app.state.runs[run_id]
    try:
        async with create_team() as team:
            result = await team.run_ticket(ticket_id, run_id=run_id)
        record.result = result.model_dump()
    except Exception as exc:  # config problems, MCP failures, anything unexpected
        record.error = f"{type(exc).__name__}: {exc}"
    finally:
        record.finished = True
        if app.state.active_run == run_id:
            app.state.active_run = None


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int):
    if app.state.active_run is not None:
        raise HTTPException(409, f"Run {app.state.active_run} is still going. Only one run at a time.")
    tickets = (await app.state.shop.call("list_tickets"))["tickets"]
    if ticket_id not in {t["id"] for t in tickets}:
        raise HTTPException(404, f"No ticket with id {ticket_id}.")
    if app.state.active_run is not None:  # another request got in while we checked the ticket
        raise HTTPException(409, f"Run {app.state.active_run} is still going. Only one run at a time.")
    run_id = uuid.uuid4().hex[:12]
    app.state.runs[run_id] = RunRecord(run_id, ticket_id)
    app.state.active_run = run_id
    app.state.task = asyncio.create_task(_run_in_background(run_id, ticket_id))
    return {"run_id": run_id, "ticket_id": ticket_id}


def _event_text(e: dict[str, Any]) -> str:
    if e["step_type"] == "model_call":
        text = e.get("result") or ""
    else:
        text = f"{e.get('args') or ''} → {e.get('result') or ''}".strip(" →")
    return text if len(text) <= 300 else text[:299] + "…"


@app.get("/api/events")
def get_events(run_id: str = Query(...), after: int = Query(0, ge=0)):
    record: Optional[RunRecord] = app.state.runs.get(run_id)
    entries = app.state.audit.read_run(run_id)
    if record is None and not entries:
        raise HTTPException(404, f"No run with id {run_id}.")
    events = [
        {
            "index": i,
            "timestamp": e["timestamp"],
            "agent": e["agent"],
            "step_type": e["step_type"],
            "tool_or_target": e.get("tool_or_target"),
            "text": _event_text(e),
            "tokens": e.get("tokens"),
            "stop_reason": e.get("stop_reason"),
        }
        for i, e in enumerate(entries, start=1)
        if i > after
    ]
    finished = True if record is None else record.finished  # a run from before a restart is over
    result = record.result if record else None
    return {
        "run_id": run_id,
        "ticket_id": (record.ticket_id if record else entries[0]["ticket_id"]),
        "events": events,
        "next_after": len(entries),
        "finished": finished,
        "summary": result["outcome"] if result else None,
        "stopped_reason": result["stopped_reason"] if result else None,
        "error": record.error if record else None,
        "result": result,
    }


# -- approvals: the only way money moves ----------------------------------------------------
@app.get("/api/approvals")
async def get_approvals():
    data = await app.state.shop.call("list_all_pending_payments")
    return {"payments": data["pending_payments"], "pending_total": data["pending_total"]}


@app.post("/api/approvals/{payment_id}/approve")
async def approve(payment_id: int, body: ApprovalBody = ApprovalBody()):
    data = await app.state.shop.call("approve_payment", payment_id=payment_id, approved_by=body.approved_by)
    if not data.get("approved"):
        code = 404 if data["message"].startswith("No pending payment") else 409
        raise HTTPException(code, data["message"])
    return data


@app.post("/api/approvals/{payment_id}/reject")
async def reject(payment_id: int):
    data = await app.state.shop.call("reject_payment", payment_id=payment_id)
    if not data.get("rejected"):
        code = 404 if data["message"].startswith("No pending payment") else 409
        raise HTTPException(code, data["message"])
    return data


# -- cash and reset --------------------------------------------------------------------------
@app.get("/api/cash")
async def get_cash():
    data = await app.state.shop.call("get_cash_balance")
    if not data.get("found"):
        raise HTTPException(404, data.get("message", "No cash account."))
    checking = next(a for a in data["accounts"] if a["name"] == "checking")
    return {
        "account": "checking",
        "balance": checking["balance"],
        "as_of": checking["date"],
        "pending_payments_total": data["pending_payments_total"],
        "balance_after_pending": checking["balance_after_pending"],
    }


@app.post("/api/reset")
def reset():
    if app.state.active_run is not None:
        raise HTTPException(409, f"Run {app.state.active_run} is still going. Can't reset now.")
    tmp = WORKING_DB.with_suffix(".db.tmp")
    shutil.copyfile(ORIGINAL_DB, tmp)
    os.replace(tmp, WORKING_DB)  # the audit trail is not touched
    app.state.runs.clear()
    return {"reset": True}
