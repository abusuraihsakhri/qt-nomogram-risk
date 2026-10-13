"""FastAPI endpoints for the legacy audit supervisor and the QT calculator."""
import hmac
import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor
from qt_nomogram import calculate_qtc

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(title="QT Nomogram Risk API", version="3.0.1")


def _authorize(authorization: str | None) -> None:
    """Require a bearer token when one has been configured."""
    configured = os.getenv("API_ACCESS_TOKEN")
    if configured and not hmac.compare_digest(authorization or "", f"Bearer {configured}"):
        raise HTTPException(status_code=401, detail="Authorization required")


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class QTRequest(BaseModel):
    qt_ms: float = Field(gt=0, allow_inf_nan=False)
    hr_bpm: float = Field(gt=0, allow_inf_nan=False)


@app.get("/health")
def health():
    return {"status": "ok", "service": "qt-nomogram-risk", "version": "3.0.1"}


@app.get("/metrics")
def metrics(authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
    }


@app.post("/api/qt")
def api_qt(payload: QTRequest, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return calculate_qtc(payload.qt_ms, hr_bpm=payload.hr_bpm)


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try:
        return supervisor.process_task(payload).to_dict()
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifier pattern detected") from None


@app.post("/api/chat")
def api_chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifier pattern detected") from None


@app.get("/api/audit/logs")
def api_audit_logs(authorization: str | None = Header(default=None)):
    # Never serve the audit ledger anonymously, even in development.
    if not os.getenv("API_ACCESS_TOKEN"):
        raise HTTPException(status_code=403, detail="Audit log access disabled")
    _authorize(authorization)
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
