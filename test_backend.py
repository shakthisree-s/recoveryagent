"""API-level tests for the Revenue Recovery Agent backend (FastAPI TestClient)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    client.post("/api/reset")
    yield


# --------------------------------------------------------------------------- #
# Health + model
# --------------------------------------------------------------------------- #
def test_health_reports_accurate_state():
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    assert h["agent"] == "RevenueRecoveryAgent"
    assert h["mode"] == "TEST_MODE"
    assert h["database"] == "connected"
    assert h["model_loaded"] is True
    assert h["demo_cases"] == 8
    assert "policies govern recovery execution" in h["note"]


def test_model_metrics_are_exposed_without_fabricated_explainability():
    m = client.get("/api/model/metrics").json()
    assert m["model"] == "RandomForestClassifier"
    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc"):
        assert 0.0 <= m[key] <= 1.0
    assert m["feature_count"] == len(m["features"]) == 15
    assert m["model_type"]
    assert "risk signal" in m["governance_statement"]


# --------------------------------------------------------------------------- #
# Cases + analyze
# --------------------------------------------------------------------------- #
def test_eight_benchmark_cases_present():
    cases = client.get("/api/cases").json()
    assert len(cases) == 8
    assert {c["case_id"] for c in cases} == set(range(1, 9))


def test_analyze_exposes_all_six_stages():
    a = client.post("/api/cases/1/analyze").json()
    assert a["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert a["diagnosis"] == "PAYMENT_FAILED"
    assert a["recommended_action"] == "SEND_RECOVERY_LINK"
    assert a["policy_result"] == "ALLOWED"
    assert a["evidence"] and isinstance(a["evidence"], list)
    steps = [s["step"] for s in a["decision_flow"]]
    assert steps == ["DETECT", "DIAGNOSE", "DECIDE", "POLICY", "EXECUTE", "MEASURE"]


# --------------------------------------------------------------------------- #
# Recovery / retry / approval / policy / stopping
# --------------------------------------------------------------------------- #
def test_case1_autonomous_recovery_success():
    r = client.post("/api/cases/1/recover", json={"simulate_failure": False}).json()
    assert r["status"] == "RECOVERED"
    assert r["recovered_amount"] == 8000.0
    assert r["execution_status"] == "SUCCESS"
    assert r["payment_status_after"] == "Success"


def test_case2_failed_then_retry_then_success_both_in_audit():
    r1 = client.post("/api/cases/2/recover", json={"simulate_failure": True}).json()
    assert r1["status"] == "RETRY_AVAILABLE"
    assert r1["recovered_amount"] == 0.0

    r2 = client.post("/api/cases/2/retry").json()
    assert r2["status"] == "RECOVERED"
    assert r2["recovered_amount"] == 12000.0

    events = [e["audit_event"] for e in client.get("/api/audit/2").json()]
    assert "RETRY_AVAILABLE" in events
    assert "RECOVERY_SUCCESS" in events


def test_case3_high_value_requires_then_accepts_human_approval_with_notes():
    case3 = client.get("/api/cases/3").json()["case"]
    assert case3["status"] == "HUMAN_APPROVAL_REQUIRED"

    r = client.post("/api/cases/3/approve", json={"notes": "Approved by ops supervisor"}).json()
    assert r["status"] == "RECOVERED"
    assert r["recovered_amount"] == 50000.0
    assert r["approval_notes"] == "Approved by ops supervisor"
    assert r["approver"] == "merchant_ops_supervisor"

    audit = client.get("/api/audit/3").json()
    assert any(e["audit_event"] == "HUMAN_APPROVED" for e in audit)


def test_case3_rejection_stops_recovery():
    client.post("/api/reset")
    r = client.post("/api/cases/3/reject", json={"notes": "Chargeback history"}).json()
    assert r["status"] == "BLOCKED"
    assert r["stopping_reason"] == "HUMAN_OPERATOR_REJECTED"
    assert r["recovered_amount"] == 0.0


def test_case4_incentive_over_ceiling_is_blocked():
    case4 = client.get("/api/cases/4").json()["case"]
    assert case4["status"] == "BLOCKED"
    assert case4["requested_incentive_percent"] == 15.0
    assert case4["policy_evaluation"] == "BLOCKED"


def test_case5_stopping_rule_after_max_attempts():
    case5 = client.get("/api/cases/5").json()["case"]
    assert case5["status"] == "BLOCKED"
    assert case5["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED"
    r = client.post("/api/cases/5/recover")
    assert r.status_code == 400  # stopping rule enforced


def test_case6_successful_payment_is_no_action():
    case6 = client.get("/api/cases/6").json()["case"]
    assert case6["status"] == "NO_ACTION"
    assert case6["recommended_action"] == "NO_ACTION"


def test_case7_checkout_abandonment_recovery():
    case7 = client.get("/api/cases/7").json()["case"]
    assert case7["diagnosis"] == "CHECKOUT_ABANDONED"
    assert case7["recommended_action"] in ("SEND_PAYMENT_REMINDER", "SEND_RECOVERY_LINK")
    r = client.post("/api/cases/7/recover").json()
    assert r["status"] == "RECOVERED"


# --------------------------------------------------------------------------- #
# Metrics / batch
# --------------------------------------------------------------------------- #
def test_metrics_are_calculated_dynamically():
    client.post("/api/cases/1/recover", json={"simulate_failure": False})
    client.post("/api/cases/2/recover", json={"simulate_failure": True})
    client.post("/api/cases/2/retry")
    client.post("/api/cases/3/approve", json={"notes": "ok"})

    m = client.get("/api/metrics").json()
    assert m["total_revenue_recovered"] == 70000.0   # 8000 + 12000 + 50000
    assert m["recovered_cases"] == 3
    expected_rate = round(m["total_revenue_recovered"] / m["total_revenue_at_risk"] * 100, 2)
    assert abs(m["recovery_rate"] - expected_rate) < 0.01


def test_batch_run_and_fetch_roundtrip():
    b = client.post("/api/batch/run").json()
    assert b["total_cases"] == 8
    assert b["at_risk_cases"] == 7
    assert b["recovered_cases"] >= 1
    # dynamic: rate matches the revenue ratio
    if b["total_revenue_at_risk"]:
        exp = round(b["total_revenue_recovered"] / b["total_revenue_at_risk"] * 100, 2)
        assert abs(b["recovery_rate"] - exp) < 0.01

    fetched = client.get(f"/api/batch/{b['batch_id']}").json()
    assert fetched["batch_id"] == b["batch_id"]


# --------------------------------------------------------------------------- #
# Audit / reset / persistence
# --------------------------------------------------------------------------- #
def test_audit_trail_is_chronological_and_persistent():
    client.post("/api/cases/1/recover", json={"simulate_failure": False})
    logs = client.get("/api/audit").json()
    assert len(logs) > 0
    # newest-first ordering
    ts = [l["timestamp"] for l in logs]
    assert ts == sorted(ts, reverse=True)
    assert any(l["audit_event"] == "RECOVERY_SUCCESS" for l in logs)


def test_reset_restores_clean_benchmark_state():
    client.post("/api/cases/1/recover", json={"simulate_failure": False})
    client.post("/api/reset")
    cases = client.get("/api/cases").json()
    assert len(cases) == 8
    assert all(c["recovered_amount"] == 0.0 for c in cases)


def test_persistence_survives_state_manager_reload():
    from backend import state as state_module
    from backend.state import StateManager

    client.post("/api/cases/1/recover", json={"simulate_failure": False})
    before = client.get("/api/cases/1").json()["case"]["status"]
    assert before == "RECOVERED"

    # simulate a backend restart: build a fresh StateManager on the same DB
    reloaded = StateManager()
    assert len(reloaded.cases) == 8            # no duplication on reload
    assert reloaded.cases[1]["status"] == "RECOVERED"
