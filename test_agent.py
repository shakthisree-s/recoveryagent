"""Unit tests for the single RevenueRecoveryAgent decision stages."""

from agent import RevenueRecoveryAgent

agent = RevenueRecoveryAgent()


PAYMENT_FAILURE = {
    "name": "Payment Failure", "gender": "M", "amount": 8000, "total_amount": 8000,
    "payment_method": "Credit Card", "payment_status": "Failed", "device_type": "Android",
    "home_country": "India", "shipment_fee": 100, "promo_amount": 0, "total_spend": 45000,
    "total_transactions": 5, "successful_payments": 3, "failed_payments": 2,
    "average_transaction_amount": 8000, "transaction_day": 15, "transaction_hour": 20,
    "failure_rate": 0.40,
}

HIGH_VALUE_FAILURE = {
    "name": "High Value Failure", "gender": "F", "amount": 30000, "total_amount": 30000,
    "payment_method": "Credit Card", "payment_status": "Failed", "device_type": "iOS",
    "home_country": "India", "shipment_fee": 150, "promo_amount": 0, "total_spend": 70000,
    "total_transactions": 7, "successful_payments": 5, "failed_payments": 2,
    "average_transaction_amount": 10000, "transaction_day": 22, "transaction_hour": 21,
    "failure_rate": 0.29,
}

SUCCESSFUL = {**PAYMENT_FAILURE, "name": "Healthy", "payment_status": "Success",
              "failed_payments": 0, "failure_rate": 0.0}


def test_model_loaded_and_pathlib_resolved():
    from backend.config import MODEL_PATH
    assert MODEL_PATH.exists()
    assert agent.model is not None


def test_detect_returns_risk_signal_and_revenue_at_risk():
    d = agent.detect(PAYMENT_FAILURE)
    assert set(d) >= {"risk_probability", "risk_score", "risk_level",
                      "revenue_at_risk", "detection_reason"}
    assert 0.0 <= d["risk_probability"] <= 1.0
    assert d["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert d["revenue_at_risk"] == 8000
    assert agent.detect(SUCCESSFUL)["revenue_at_risk"] == 0.0


def test_diagnose_evidence_is_never_invented():
    d = agent.detect(PAYMENT_FAILURE)
    dx = agent.diagnose(PAYMENT_FAILURE, d)
    assert dx["diagnosis"] == "PAYMENT_FAILED"
    assert dx["root_cause"] and dx["recovery_objective"]
    # every evidence line must reference a field actually present on the case
    joined = " ".join(dx["evidence"]).lower()
    assert "failed" in joined and "8,000" in joined


def test_decide_does_not_authorise_execution():
    d = agent.detect(PAYMENT_FAILURE)
    dx = agent.diagnose(PAYMENT_FAILURE, d)
    decision = agent.decide(PAYMENT_FAILURE, d, dx)
    assert decision["recommended_action"] == "SEND_RECOVERY_LINK"
    assert 0.0 <= decision["decision_confidence"] <= 1.0


def test_policy_is_the_execution_authority():
    analysis = agent.analyze(PAYMENT_FAILURE)
    assert analysis["policy_result"] == "ALLOWED"
    checks = {c["rule"]: c["result"] for c in analysis["policy_checks"]}
    assert all(v == "PASS" for v in checks.values())


def test_high_value_requires_human_approval():
    analysis = agent.analyze(HIGH_VALUE_FAILURE)
    assert analysis["policy_result"] == "HUMAN_APPROVAL_REQUIRED"
    assert analysis["recommended_action"] == "ESCALATE_TO_HUMAN"


def test_incentive_over_ceiling_is_blocked():
    case = {**PAYMENT_FAILURE, "requested_incentive_percent": 15.0}
    analysis = agent.analyze(case)
    assert analysis["policy_result"] == "BLOCKED"
    assert analysis["stopping_reason"] == "POLICY_GUARDRAIL_VIOLATION"


def test_max_attempts_triggers_stop():
    case = {**PAYMENT_FAILURE, "current_attempts": 3}
    analysis = agent.analyze(case)
    assert analysis["recommended_action"] == "STOP"
    assert analysis["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED"


def test_failed_recovery_then_retry_then_success():
    attempt1 = agent.execute_recovery(PAYMENT_FAILURE, simulate_failure=True)
    assert attempt1["status"] == "RETRY_AVAILABLE"
    assert attempt1["recovered_amount"] == 0.0
    assert attempt1["audit_event"] == "RECOVERY_FAILED"

    retry = agent.retry_recovery(PAYMENT_FAILURE)
    assert retry["status"] == "RECOVERED"
    assert retry["recovered_amount"] == 8000
    assert retry["audit_event"] == "RECOVERY_SUCCESS"


def test_human_approval_and_rejection_paths():
    approved = agent.approve_recovery(HIGH_VALUE_FAILURE, notes="ops sign-off")
    assert approved["status"] == "RECOVERED"
    assert approved["recovered_amount"] == 30000
    assert approved["approval_notes"] == "ops sign-off"

    rejected = agent.reject_recovery(HIGH_VALUE_FAILURE, notes="fraud risk")
    assert rejected["status"] == "BLOCKED"
    assert rejected["stopping_reason"] == "HUMAN_OPERATOR_REJECTED"


def test_successful_payment_is_no_action():
    analysis = agent.analyze(SUCCESSFUL)
    assert analysis["diagnosis"] == "PAYMENT_SUCCESSFUL"
    assert analysis["recommended_action"] == "NO_ACTION"
