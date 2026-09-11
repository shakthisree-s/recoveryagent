"""End-to-end walkthrough of the Track 03 loop:

Revenue at Risk -> DETECT -> DIAGNOSE -> DECIDE -> POLICY -> EXECUTE -> MEASURE -> AUDIT

Runs against the in-process app via TestClient, so `python -m pytest -v` needs
no separately running server.
"""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_full_recovery_loop_end_to_end():
    assert client.post("/api/reset").status_code == 200

    # DETECT / health
    health = client.get("/api/health").json()
    assert health["model_loaded"] and health["demo_cases"] == 8

    # CASE 1 - Aarav, INR 8,000 payment failed -> recovery link -> success
    c1 = client.get("/api/cases/1").json()["case"]
    assert c1["diagnosis"] == "PAYMENT_FAILED"
    assert c1["recommended_action"] == "SEND_RECOVERY_LINK"
    r1 = client.post("/api/cases/1/recover", json={"simulate_failure": False}).json()
    assert r1["status"] == "RECOVERED" and r1["recovered_amount"] == 8000.0

    # CASE 2 - failed recovery -> retry -> success (both attempts audited)
    a1 = client.post("/api/cases/2/recover", json={"simulate_failure": True}).json()
    assert a1["status"] == "RETRY_AVAILABLE"
    a2 = client.post("/api/cases/2/retry").json()
    assert a2["status"] == "RECOVERED" and a2["recovered_amount"] == 12000.0
    assert len(client.get("/api/audit/2").json()) >= 2

    # CASE 3 - high value -> human approval required -> approved
    assert client.get("/api/cases/3").json()["case"]["status"] == "HUMAN_APPROVAL_REQUIRED"
    r3 = client.post("/api/cases/3/approve", json={"notes": "ops ok"}).json()
    assert r3["status"] == "RECOVERED" and r3["recovered_amount"] == 50000.0

    # CASE 4 - incentive > 10% -> blocked
    assert client.get("/api/cases/4").json()["case"]["status"] == "BLOCKED"
    # CASE 5 - max attempts -> stopped
    assert client.get("/api/cases/5").json()["case"]["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED"
    # CASE 6 - already successful -> no action
    assert client.get("/api/cases/6").json()["case"]["recommended_action"] == "NO_ACTION"

    # MEASURE - dynamic dashboard metrics
    m = client.get("/api/metrics").json()
    assert m["total_revenue_recovered"] == 70000.0

    # BATCH - full loop across all 8 cases
    b = client.post("/api/batch/run").json()
    assert b["total_cases"] == 8 and b["at_risk_cases"] == 7

    # AUDIT - chronological, persistent, non-empty
    logs = client.get("/api/audit").json()
    assert len(logs) > 0
    assert any(l["audit_event"] == "RECOVERY_SUCCESS" for l in logs)
