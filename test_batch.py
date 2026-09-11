"""Batch recovery (MEASURE stage) tests - metrics must be computed, not hardcoded."""

from agent import RevenueRecoveryAgent
from backend.data import INITIAL_CASES

agent = RevenueRecoveryAgent()


def test_batch_processes_full_loop_and_reports_dynamic_metrics():
    batch = agent.run_batch(INITIAL_CASES)

    assert batch["total_cases"] == 8
    # keys required by Track 03
    required = {
        "total_cases", "eligible_cases", "at_risk_cases", "recovered_cases",
        "blocked_cases", "approval_cases", "stopped_cases",
        "total_revenue_at_risk", "total_revenue_recovered", "recovery_rate",
        "average_risk_score", "results",
    }
    assert required <= set(batch)

    # recovery_rate is derived from the two revenue totals, not a constant
    if batch["total_revenue_at_risk"] > 0:
        expected = round(
            batch["total_revenue_recovered"] / batch["total_revenue_at_risk"] * 100, 2
        )
        assert abs(batch["recovery_rate"] - expected) < 0.01

    # counts are internally consistent with the per-case results
    recovered = sum(1 for r in batch["results"] if r["status"] == "RECOVERED")
    assert recovered == batch["recovered_cases"]
    assert sum(r["recovered_amount"] for r in batch["results"]) == batch["total_revenue_recovered"]


def test_batch_preserves_benchmark_behaviours():
    results = {r["case_id"]: r for r in agent.run_batch(INITIAL_CASES)["results"]}

    assert results[3]["status"] == "HUMAN_APPROVAL_REQUIRED"          # high value
    assert results[4]["status"] == "BLOCKED"                          # incentive > 10%
    assert results[5]["status"] in ("STOPPED", "BLOCKED")            # max attempts
    assert results[5]["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED"
    assert results[6]["status"] == "NO_ACTION"                        # successful payment
    assert results[7]["action"] in ("SEND_PAYMENT_REMINDER", "SEND_RECOVERY_LINK")  # abandonment
    assert results[8]["status"] == "HUMAN_APPROVAL_REQUIRED"         # enterprise high value
