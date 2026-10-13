"""Regression tests for clinical input validation and audit integrity."""
import math

import pytest
from fastapi.testclient import TestClient

from qt_nomogram import calculate_meld_na, calculate_qtc, assess_row
from agents.base import AuditTrail, SecurityException
from agents.api import app


def test_qt_nonfinite_and_invalid_rr_rejected():
    assert "error" in calculate_qtc(float("nan"), hr_bpm=60)
    assert "error" in calculate_qtc(400, hr_bpm=float("inf"))
    assert "error" in calculate_qtc(400, rr_ms="-1", hr_bpm=60)


def test_qtc_not_misrepresented_as_nomogram():
    result = calculate_qtc(420, hr_bpm=72)
    assert result["nomogram_assessed"] is False
    assert "Bazett" in result["assessment_method"]
    assert result["qtc_ms"] == 460.1


def test_historical_meld_uses_log_of_creatinine():
    result = calculate_meld_na(2, 1.5, 1.2)
    assert result["meld_na"] == 15
    assert result["method"].startswith("Historical")


def test_unsupported_schema_never_gets_fabricated_score():
    assert "error" in assess_row({"unknown": 123})


def test_hmac_verification_detects_modified_audit_content():
    trail = AuditTrail(secret_key="long-independent-test-key")
    trail.log("worker", "tier", "event", {"status": "ok"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "modified"
    assert not trail.verify_integrity()


def test_api_reports_sensitive_data_as_client_error(monkeypatch):
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.post("/api/audit", json={
            "task_id": "MRN-123456", "target_identifier": "X",
            "primary_metric": 10.0
        })
        assert response.status_code == 422


def test_audit_logs_require_configured_token(monkeypatch):
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/audit/logs").status_code == 403
    monkeypatch.setenv("API_ACCESS_TOKEN", "example-local-test-token")
    with TestClient(app) as client:
        assert client.get("/api/audit/logs").status_code == 401
        assert client.get("/api/audit/logs", headers={
            "Authorization": "Bearer example-local-test-token"
        }).status_code == 200
