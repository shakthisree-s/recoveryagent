"""
RevenueRecoveryAgent - ONE autonomous agent for Razorpay AI Buildathon Track 03.

It closes the loop:

    Revenue at Risk -> DETECT -> DIAGNOSE -> DECIDE -> POLICY -> EXECUTE -> MEASURE -> AUDIT

Design notes
------------
* There is a single agent class. The six stages are internal methods
  (``detect`` / ``diagnose`` / ``decide`` / ``apply_policy`` / ``execute`` /
  ``measure_batch``) - NOT separate agents.
* The ML model produces ONLY the risk signal. It never decides whether an
  action is allowed to run - merchant policy guardrails do that.
* Evidence is never invented: the ``evidence`` list only contains values that
  are actually present on the case.
* All monetary interventions are bounded by explicit policy constants.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import joblib
import pandas as pd

try:  # normal path (repo root on sys.path)
    from backend.config import MODEL_PATH
except Exception:  # pragma: no cover - fallback if backend package not importable
    from pathlib import Path as _Path
    import os as _os

    MODEL_PATH = _Path(
        _os.environ.get("REVENUE_MODEL_PATH")
        or (_Path(__file__).resolve().parent / "revenue_risk_model.joblib")
    ).resolve()

# Feature columns the trained RandomForest expects, in order.
FEATURE_COLS: List[str] = [
    "amount", "promo_amount", "shipment_fee", "transaction_hour",
    "transaction_day", "payment_method", "gender", "device_type",
    "home_country", "total_transactions", "successful_payments",
    "failed_payments", "average_transaction_amount", "total_spend",
    "failure_rate",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueRecoveryAgent:
    """Single Revenue Recovery Agent. Stateless w.r.t. persistence - the
    StateManager owns durable state; this class owns the decision logic."""

    def __init__(self) -> None:
        # Working-directory-independent load (pathlib + __file__ via config).
        self.model = joblib.load(MODEL_PATH)

        # --- Bounded merchant policy (defaults; overridable by env if needed) ---
        self.MAX_INCENTIVE_PERCENT = 10
        self.MAX_PAYMENT_ATTEMPTS = 3
        self.MAX_RECOVERY_AMOUNT = 100000
        self.HIGH_VALUE_APPROVAL_THRESHOLD = 25000

    # =====================================================================
    # Helpers
    # =====================================================================
    def _amount(self, case: Dict[str, Any]) -> float:
        return float(case.get("amount", case.get("total_amount", 0)) or 0)

    def _attempts(self, case: Dict[str, Any]) -> int:
        return int(case.get("current_attempts", len(case.get("attempts", []))) or 0)

    def _failure_rate(self, case: Dict[str, Any]) -> float:
        tot = case.get("total_transactions", 0) or 0
        fail = case.get("failed_payments", 0) or 0
        return (fail / tot) if tot > 0 else 0.0

    # =====================================================================
    # STAGE 1 - DETECT   (ML risk signal + revenue at risk)
    # =====================================================================
    def detect(self, case: Dict[str, Any]) -> Dict[str, Any]:
        model_row: Dict[str, Any] = {}
        for col in FEATURE_COLS:
            if col in case and case[col] is not None:
                model_row[col] = case[col]
            elif col == "amount":
                model_row[col] = case.get("total_amount", 0)
            elif col == "failure_rate":
                model_row[col] = self._failure_rate(case)
            else:
                model_row[col] = 0

        risk_probability = float(self.model.predict_proba(pd.DataFrame([model_row]))[0][1])

        if risk_probability >= 0.60:
            risk_level = "HIGH"
        elif risk_probability >= 0.30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        amount = self._amount(case)
        payment_status = case.get("payment_status", "Unknown")
        # Revenue is "at risk" only when money has not already been captured.
        revenue_at_risk = 0.0 if payment_status == "Success" else amount

        hist = self._failure_rate(case)
        detection_reason = (
            f"ML payment-failure risk {risk_probability * 100:.1f}% ({risk_level}); "
            f"payment_status={payment_status}; historical failure rate {hist * 100:.1f}%."
        )

        return {
            "risk_probability": round(risk_probability, 4),
            "risk_score": round(risk_probability, 4),
            "risk_level": risk_level,
            "revenue_at_risk": round(revenue_at_risk, 2),
            "detection_reason": detection_reason,
            "historical_failure_rate": round(hist, 4),
            "amount": amount,
        }

    # =====================================================================
    # STAGE 2 - DIAGNOSE  (root cause; evidence only from real data)
    # =====================================================================
    def diagnose(self, case: Dict[str, Any], detection: Dict[str, Any]) -> Dict[str, Any]:
        amount = detection["amount"]
        risk_probability = detection["risk_probability"]
        payment_status = case.get("payment_status", "Unknown")
        failed_payments = int(case.get("failed_payments", 0) or 0)
        attempts = self._attempts(case)
        requested_incentive = float(case.get("requested_incentive_percent", 0.0) or 0.0)
        hist = detection["historical_failure_rate"]

        # ---- Evidence: only append facts that are actually present -----------
        evidence: List[str] = []
        if payment_status and payment_status != "Unknown":
            evidence.append(f"payment_status = {payment_status}")
        if amount:
            evidence.append(f"amount = INR {amount:,.0f}")
        if case.get("payment_method"):
            evidence.append(f"payment_method = {case['payment_method']}")
        if case.get("total_transactions"):
            evidence.append(
                f"history = {failed_payments} failed / {case.get('total_transactions')} txns "
                f"({hist * 100:.1f}% failure rate)"
            )
        if attempts:
            evidence.append(f"recovery attempts so far = {attempts}")
        if requested_incentive:
            evidence.append(f"requested incentive = {requested_incentive:.0f}%")
        if case.get("is_checkout_abandoned"):
            evidence.append("checkout abandoned before completion")
        evidence.append(f"ML risk probability = {risk_probability:.4f}")

        if payment_status == "Success":
            diagnosis, root_cause = "PAYMENT_SUCCESSFUL", "Payment already captured; nothing at risk."
            objective = "None - monitor only."
        elif attempts >= self.MAX_PAYMENT_ATTEMPTS:
            diagnosis = "MAX_ATTEMPTS_EXHAUSTED"
            root_cause = f"Recovery attempts reached the bounded maximum ({self.MAX_PAYMENT_ATTEMPTS})."
            objective = "Stop autonomous recovery; hand back to merchant."
        elif requested_incentive > self.MAX_INCENTIVE_PERCENT:
            diagnosis = "INCENTIVE_EXCEEDS_POLICY"
            root_cause = (
                f"Requested incentive {requested_incentive:.0f}% exceeds the "
                f"{self.MAX_INCENTIVE_PERCENT}% policy ceiling."
            )
            objective = "Block the incentive; only sub-ceiling recovery may proceed."
        elif amount >= self.HIGH_VALUE_APPROVAL_THRESHOLD:
            diagnosis = "HIGH_VALUE_PAYMENT_FAILURE"
            root_cause = (
                f"Failed payment of INR {amount:,.0f} is at/above the high-value "
                f"approval threshold (INR {self.HIGH_VALUE_APPROVAL_THRESHOLD:,.0f})."
            )
            objective = "Escalate to a human approver before any execution."
        elif failed_payments >= 3 or hist >= 0.50:
            diagnosis = "REPEATED_FAILURE"
            root_cause = "Customer shows a persistent pattern of payment failures."
            objective = "Retry the payment through the agent, within attempt limits."
        elif case.get("is_checkout_abandoned"):
            diagnosis = "CHECKOUT_ABANDONED"
            root_cause = "Customer left the checkout flow before authorising payment."
            objective = "Bring the customer back with a reminder / recovery link."
        elif payment_status == "Failed" or risk_probability >= 0.30:
            diagnosis = "PAYMENT_FAILED"
            root_cause = "Single payment failure with a recoverable risk profile."
            objective = "Send a recovery link so the customer can complete payment."
        else:
            diagnosis = "LOW_RISK_HEALTHY"
            root_cause = "No material payment-failure signal."
            objective = "No intervention required."

        return {
            "diagnosis": diagnosis,
            "root_cause": root_cause,
            "evidence": evidence,
            "recovery_objective": objective,
            # human-readable label kept for backwards compatibility with the UI
            "diagnosis_label": root_cause,
        }

    # =====================================================================
    # STAGE 3 - DECIDE   (bounded action; ML informs, does not authorise)
    # =====================================================================
    def decide(
        self,
        case: Dict[str, Any],
        detection: Dict[str, Any],
        diagnosis: Dict[str, Any],
    ) -> Dict[str, Any]:
        amount = detection["amount"]
        risk_probability = detection["risk_probability"]
        hist = detection["historical_failure_rate"]
        dx = diagnosis["diagnosis"]

        if dx == "PAYMENT_SUCCESSFUL":
            action, reason = "NO_ACTION", "Payment already succeeded - no recovery needed."
            expected, confidence = 0.0, 0.99
        elif dx == "MAX_ATTEMPTS_EXHAUSTED":
            action, reason = "STOP", (
                f"Maximum recovery attempts ({self.MAX_PAYMENT_ATTEMPTS}) reached - "
                "stopping rule enforced."
            )
            expected, confidence = 0.0, 0.99
        elif dx == "INCENTIVE_EXCEEDS_POLICY":
            action, reason = "OFFER_BOUNDED_INCENTIVE", (
                f"Incentive request exceeds the {self.MAX_INCENTIVE_PERCENT}% ceiling; "
                "policy will block execution."
            )
            expected, confidence = 0.0, 0.9
        elif dx == "HIGH_VALUE_PAYMENT_FAILURE":
            action, reason = "ESCALATE_TO_HUMAN", (
                f"High-value failure (INR {amount:,.0f}) requires human approval before execution."
            )
            expected, confidence = round(amount * 0.6, 2), 0.7
        elif dx == "REPEATED_FAILURE":
            action, reason = "RETRY_PAYMENT", (
                "Persistent failure pattern - autonomous payment retry within attempt limits."
            )
            expected, confidence = round(amount * max(risk_probability, hist), 2), 0.6
        elif dx == "CHECKOUT_ABANDONED":
            action, reason = "SEND_PAYMENT_REMINDER", (
                "Checkout abandoned - send a payment reminder to bring the customer back."
            )
            expected, confidence = round(amount * 0.5, 2), 0.55
        elif dx == "PAYMENT_FAILED":
            action, reason = "SEND_RECOVERY_LINK", (
                "Recoverable single failure - dispatch a recovery link for self-serve completion."
            )
            expected, confidence = round(amount * max(risk_probability, 0.5), 2), 0.6
        else:  # LOW_RISK_HEALTHY
            action, reason = "NO_ACTION", "No significant risk detected."
            expected, confidence = 0.0, 0.9

        return {
            "recommended_action": action,
            "decision_reason": reason,
            "expected_recovery": expected,
            "decision_confidence": round(confidence, 2),
        }

    # =====================================================================
    # STAGE 4 - POLICY   (guardrails; the only authority on execution)
    # =====================================================================
    def apply_policy(self, case: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        amount = self._amount(case)
        attempts = self._attempts(case)
        requested_incentive = float(case.get("requested_incentive_percent", 0.0) or 0.0)
        payment_status = case.get("payment_status", "Unknown")
        action = decision["recommended_action"]

        checks: List[Dict[str, str]] = []

        def add(rule: str, ok: bool, reason: str) -> None:
            checks.append({"rule": rule, "result": "PASS" if ok else "FAIL", "reason": reason})

        add(
            "payment_not_already_successful",
            payment_status != "Success",
            "Payment already captured - no execution." if payment_status == "Success"
            else "Payment is not yet captured.",
        )
        add(
            f"attempts_below_max ({self.MAX_PAYMENT_ATTEMPTS})",
            attempts < self.MAX_PAYMENT_ATTEMPTS,
            f"{attempts} attempt(s) used; max {self.MAX_PAYMENT_ATTEMPTS}."
            + ("" if attempts < self.MAX_PAYMENT_ATTEMPTS else " Stopping rule triggered."),
        )
        add(
            f"incentive_within_{self.MAX_INCENTIVE_PERCENT}pct",
            requested_incentive <= self.MAX_INCENTIVE_PERCENT,
            f"Requested incentive {requested_incentive:.0f}% vs ceiling {self.MAX_INCENTIVE_PERCENT}%.",
        )
        add(
            f"amount_within_autonomous_limit ({self.MAX_RECOVERY_AMOUNT})",
            amount <= self.MAX_RECOVERY_AMOUNT,
            f"Amount INR {amount:,.0f} vs autonomous limit INR {self.MAX_RECOVERY_AMOUNT:,.0f}.",
        )
        needs_human = amount >= self.HIGH_VALUE_APPROVAL_THRESHOLD
        add(
            f"amount_below_high_value_threshold ({self.HIGH_VALUE_APPROVAL_THRESHOLD})",
            not needs_human,
            f"Amount INR {amount:,.0f} vs human-approval threshold "
            f"INR {self.HIGH_VALUE_APPROVAL_THRESHOLD:,.0f}."
            + (" Human approval required." if needs_human else ""),
        )

        # ---- Resolve final policy verdict -----------------------------------
        if payment_status == "Success":
            policy_result, stopping_reason = "ALLOWED", None  # NO_ACTION path
        elif attempts >= self.MAX_PAYMENT_ATTEMPTS or action == "STOP":
            policy_result, stopping_reason = "BLOCKED", "MAX_PAYMENT_ATTEMPTS_REACHED"
        elif requested_incentive > self.MAX_INCENTIVE_PERCENT:
            policy_result, stopping_reason = "BLOCKED", "POLICY_GUARDRAIL_VIOLATION"
        elif amount > self.MAX_RECOVERY_AMOUNT:
            policy_result, stopping_reason = "BLOCKED", "EXCEEDS_MAX_RECOVERY_AMOUNT"
        elif needs_human:
            policy_result, stopping_reason = "HUMAN_APPROVAL_REQUIRED", None
        else:
            policy_result, stopping_reason = "ALLOWED", None

        return {
            "policy_result": policy_result,
            "policy_evaluation": policy_result,  # backwards-compatible alias
            "policy_checks": checks,
            "stopping_reason": stopping_reason,
        }

    # =====================================================================
    # analyze() - compose DETECT -> DIAGNOSE -> DECIDE -> POLICY
    # (kept as the public entrypoint used across the codebase / tests)
    # =====================================================================
    def analyze(self, case: Dict[str, Any]) -> Dict[str, Any]:
        detection = self.detect(case)
        diagnosis = self.diagnose(case, detection)
        decision = self.decide(case, detection, diagnosis)
        policy = self.apply_policy(case, decision)

        # A blocked incentive still surfaces the incentive action, but the
        # policy verdict is what governs execution.
        action = decision["recommended_action"]
        if policy["policy_result"] == "HUMAN_APPROVAL_REQUIRED":
            action = "ESCALATE_TO_HUMAN"
        elif policy["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED":
            action = "STOP"

        risk_level = detection["risk_level"]
        if policy["policy_result"] in ("BLOCKED", "HUMAN_APPROVAL_REQUIRED"):
            risk_level = "HIGH"

        reason = decision["decision_reason"]
        if policy["policy_result"] == "BLOCKED":
            reason = next(
                (c["reason"] for c in policy["policy_checks"] if c["result"] == "FAIL"),
                reason,
            )

        return {
            # ---- legacy keys (unchanged contract) ----
            "risk_probability": detection["risk_probability"],
            "risk_score": detection["risk_score"],
            "risk_level": risk_level,
            "diagnosis": diagnosis["diagnosis"],
            "diagnosis_label": diagnosis["diagnosis_label"],
            "recommended_action": action,
            "decision": action,
            "policy_evaluation": policy["policy_evaluation"],
            "reason": reason,
            "amount": detection["amount"],
            "historical_failure_rate": detection["historical_failure_rate"],
            "attempts_count": self._attempts(case),
            "requested_incentive_percent": float(case.get("requested_incentive_percent", 0.0) or 0.0),
            "stopping_reason": policy["stopping_reason"],
            # ---- new structured stage output ----
            "revenue_at_risk": detection["revenue_at_risk"],
            "detection_reason": detection["detection_reason"],
            "root_cause": diagnosis["root_cause"],
            "evidence": diagnosis["evidence"],
            "recovery_objective": diagnosis["recovery_objective"],
            "decision_reason": decision["decision_reason"],
            "expected_recovery": decision["expected_recovery"],
            "decision_confidence": decision["decision_confidence"],
            "policy_result": policy["policy_result"],
            "policy_checks": policy["policy_checks"],
        }

    # =====================================================================
    # STAGE 5 - EXECUTE
    # =====================================================================
    def execute_recovery(self, case: Dict[str, Any], simulate_failure: bool = False) -> Dict[str, Any]:
        analysis = self.analyze(case)

        action = analysis["recommended_action"]
        amount = analysis["amount"]
        attempt_number = analysis["attempts_count"] + 1
        payment_status_before = case.get("payment_status", "Unknown")
        timestamp = _now()
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        result: Dict[str, Any] = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "action": action,
            "attempt": attempt_number,
            "attempt_number": attempt_number,
            "status": "NOT_EXECUTED",
            "execution_status": "NO_ACTION",
            "payment_status_before": payment_status_before,
            "payment_status_after": payment_status_before,
            "amount_at_risk": amount,
            "recovered_amount": 0.0,
            "remaining_amount_at_risk": amount,
            "reason": analysis["reason"],
            "execution_reason": analysis["reason"],
            "diagnosis": analysis["diagnosis"],
            "policy_evaluation": analysis["policy_evaluation"],
            "policy_result": analysis["policy_result"],
            "policy_checks": analysis["policy_checks"],
            "audit_event": None,
            "stopping_reason": None,
        }

        # ---- Stopping rule: max attempts ----
        if attempt_number > self.MAX_PAYMENT_ATTEMPTS or action == "STOP":
            result.update(
                status="STOPPED", execution_status="STOPPED", action="STOP",
                audit_event="RECOVERY_STOPPED",
                stopping_reason="MAX_PAYMENT_ATTEMPTS_REACHED",
                reason=(
                    f"Maximum recovery attempts ({self.MAX_PAYMENT_ATTEMPTS}) reached. "
                    "Recovery halted by stopping rules."
                ),
            )
            result["execution_reason"] = result["reason"]
            return result

        # ---- No action ----
        if action == "NO_ACTION":
            result.update(
                status="NO_ACTION", execution_status="NO_ACTION",
                audit_event="NO_ACTION", reason="No recovery required.",
                remaining_amount_at_risk=0.0,
            )
            result["execution_reason"] = result["reason"]
            return result

        # ---- Policy block: incentive above ceiling ----
        if analysis["policy_result"] == "BLOCKED":
            result.update(
                status="BLOCKED", execution_status="BLOCKED", action="STOP",
                audit_event="POLICY_BLOCKED",
                stopping_reason=analysis["stopping_reason"] or "POLICY_GUARDRAIL_VIOLATION",
                reason=analysis["reason"],
            )
            result["execution_reason"] = result["reason"]
            return result

        # ---- Human approval required ----
        if action == "ESCALATE_TO_HUMAN" or analysis["policy_result"] == "HUMAN_APPROVAL_REQUIRED":
            result.update(
                status="HUMAN_APPROVAL_REQUIRED", execution_status="HUMAN_APPROVAL_REQUIRED",
                action="ESCALATE_TO_HUMAN", audit_event="HUMAN_APPROVAL_REQUIRED",
                reason=f"High-value recovery (INR {amount:,.0f}) requires human supervisor approval.",
            )
            result["execution_reason"] = result["reason"]
            return result

        # ---- Simulated failed recovery attempt -> retry available ----
        if simulate_failure:
            result.update(
                status="RETRY_AVAILABLE", execution_status="RETRY_AVAILABLE",
                recovered_amount=0.0, audit_event="RECOVERY_FAILED",
                reason=(
                    f"Recovery attempt {attempt_number} did not complete in Razorpay Test Mode. "
                    "Retry is permitted by policy."
                ),
            )
            result["execution_reason"] = result["reason"]
            return result

        # ---- Successful bounded recovery ----
        success_reason = {
            "RETRY_PAYMENT": "Autonomous payment retry succeeded in Razorpay Test Mode.",
            "SEND_RECOVERY_LINK": "Customer completed payment via recovery link in Razorpay Test Mode.",
            "SEND_PAYMENT_REMINDER": "Customer paid after the recovery reminder in Razorpay Test Mode.",
            "OFFER_BOUNDED_INCENTIVE": "Customer converted with a bounded incentive in Razorpay Test Mode.",
        }.get(action, "Recovery executed in Razorpay Test Mode.")

        result.update(
            status="RECOVERED", execution_status="SUCCESS",
            payment_status_after="Success",
            recovered_amount=amount, remaining_amount_at_risk=0.0,
            audit_event="RECOVERY_SUCCESS", reason=success_reason,
        )
        result["execution_reason"] = result["reason"]
        return result

    # =====================================================================
    # RETRY
    # =====================================================================
    def retry_recovery(self, case: Dict[str, Any]) -> Dict[str, Any]:
        analysis = self.analyze(case)
        amount = analysis["amount"]
        attempt_number = self._attempts(case) + 1
        timestamp = _now()
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        base = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "attempt": attempt_number,
            "attempt_number": attempt_number,
            "amount_at_risk": amount,
            "payment_status_before": case.get("payment_status", "Unknown"),
            "policy_checks": analysis["policy_checks"],
        }

        if attempt_number > self.MAX_PAYMENT_ATTEMPTS:
            base.update(
                action="STOP", status="STOPPED", execution_status="STOPPED",
                payment_status_after=case.get("payment_status", "Unknown"),
                recovered_amount=0.0, remaining_amount_at_risk=amount,
                reason=(
                    f"Maximum recovery attempts ({self.MAX_PAYMENT_ATTEMPTS}) reached. Recovery stopped."
                ),
                audit_event="RECOVERY_STOPPED",
                stopping_reason="MAX_PAYMENT_ATTEMPTS_REACHED",
            )
            base["execution_reason"] = base["reason"]
            return base

        base.update(
            action="RETRY_PAYMENT", status="RECOVERED", execution_status="SUCCESS",
            payment_status_after="Success",
            recovered_amount=amount, remaining_amount_at_risk=0.0,
            reason=f"Payment retry succeeded on attempt {attempt_number} in Razorpay Test Mode.",
            audit_event="RECOVERY_SUCCESS",
            stopping_reason=None,
        )
        base["execution_reason"] = base["reason"]
        return base

    # =====================================================================
    # HUMAN APPROVAL
    # =====================================================================
    def approve_recovery(self, case: Dict[str, Any], notes: str | None = None,
                         approver: str = "merchant_ops_supervisor") -> Dict[str, Any]:
        analysis = self.analyze(case)
        amount = analysis["amount"]
        timestamp = _now()

        if analysis["policy_result"] != "HUMAN_APPROVAL_REQUIRED" and \
           analysis["recommended_action"] != "ESCALATE_TO_HUMAN":
            return {
                "timestamp": timestamp,
                "status": "NOT_REQUIRED",
                "action": "APPROVAL_NOT_REQUIRED",
                "recovered_amount": 0.0,
                "amount_at_risk": amount,
                "reason": "This case does not require human approval.",
                "audit_event": "APPROVAL_NOT_REQUIRED",
                "approver": approver,
                "approval_notes": notes,
            }

        if amount > self.MAX_RECOVERY_AMOUNT:
            return {
                "timestamp": timestamp,
                "status": "BLOCKED",
                "action": "STOP",
                "recovered_amount": 0.0,
                "amount_at_risk": amount,
                "reason": (
                    f"Amount INR {amount:,.0f} exceeds the maximum recovery limit "
                    f"INR {self.MAX_RECOVERY_AMOUNT:,.0f}; approval cannot proceed."
                ),
                "audit_event": "POLICY_BLOCKED",
                "stopping_reason": "EXCEEDS_MAX_RECOVERY_AMOUNT",
                "approver": approver,
                "approval_notes": notes,
            }

        return {
            "timestamp": timestamp,
            "status": "RECOVERED",
            "action": "APPROVED_RETRY_PAYMENT",
            "recovered_amount": amount,
            "amount_at_risk": amount,
            "payment_status_after": "Success",
            "reason": "Human operator approved high-value recovery execution.",
            "audit_event": "HUMAN_APPROVED",
            "approver": approver,
            "approval_notes": notes,
        }

    def reject_recovery(self, case: Dict[str, Any], notes: str | None = None,
                        approver: str = "merchant_ops_supervisor") -> Dict[str, Any]:
        amount = self._amount(case)
        return {
            "timestamp": _now(),
            "status": "BLOCKED",
            "action": "REJECT_RECOVERY",
            "recovered_amount": 0.0,
            "amount_at_risk": amount,
            "reason": "Human operator rejected high-value recovery execution.",
            "audit_event": "HUMAN_REJECTED",
            "stopping_reason": "HUMAN_OPERATOR_REJECTED",
            "approver": approver,
            "approval_notes": notes,
        }

    # =====================================================================
    # STAGE 6 - MEASURE (batch)
    # =====================================================================
    def run_batch(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        total_revenue_at_risk = 0.0
        total_revenue_recovered = 0.0
        risk_score_sum = 0.0

        recovered_cases = failed_cases = blocked_cases = 0
        approval_cases = at_risk_cases = stopped_cases = eligible_cases = 0

        for index, case in enumerate(cases, start=1):
            analysis = self.analyze(case)
            recovery = self.execute_recovery(case)

            amount = analysis["amount"]
            recovered = recovery["recovered_amount"]
            risk_score_sum += analysis["risk_score"]

            is_at_risk = analysis["recommended_action"] != "NO_ACTION"
            if is_at_risk:
                total_revenue_at_risk += amount
                at_risk_cases += 1

            total_revenue_recovered += recovered

            status = recovery["status"]
            if status == "RECOVERED":
                recovered_cases += 1
                eligible_cases += 1
            elif status == "HUMAN_APPROVAL_REQUIRED":
                approval_cases += 1
                eligible_cases += 1
            elif status == "BLOCKED":
                blocked_cases += 1
            elif status == "STOPPED":
                stopped_cases += 1
            elif status in ("RETRY_AVAILABLE", "NOT_EXECUTED"):
                failed_cases += 1
                eligible_cases += 1

            results.append({
                "case_id": case.get("case_id", index),
                "customer_id": case.get("customer_id", f"CUST_{index:03d}"),
                "payment_id": case.get("payment_id", f"pay_{index:04d}"),
                "name": case.get("name", f"Case {index}"),
                "amount": amount,
                "risk_probability": analysis["risk_probability"],
                "risk_score": analysis["risk_score"],
                "risk_level": analysis["risk_level"],
                "diagnosis": analysis["diagnosis"],
                "diagnosis_label": analysis["diagnosis_label"],
                "reason": analysis["reason"],
                "action": analysis["recommended_action"],
                "policy_evaluation": analysis["policy_evaluation"],
                "policy_result": analysis["policy_result"],
                "status": status,
                "recovered_amount": recovered,
                "audit_event": recovery["audit_event"],
                "stopping_reason": recovery.get("stopping_reason"),
            })

        recovery_rate = (
            (total_revenue_recovered / total_revenue_at_risk * 100)
            if total_revenue_at_risk > 0 else 0.0
        )
        average_risk_score = (risk_score_sum / len(cases)) if cases else 0.0

        return {
            "total_cases": len(cases),
            "eligible_cases": eligible_cases,
            "at_risk_cases": at_risk_cases,
            "recovered_cases": recovered_cases,
            "failed_cases": failed_cases,
            "blocked_cases": blocked_cases,
            "approval_cases": approval_cases,
            "stopped_cases": stopped_cases,
            "total_revenue_at_risk": round(total_revenue_at_risk, 2),
            "total_revenue_recovered": round(total_revenue_recovered, 2),
            "recovery_rate": round(recovery_rate, 2),
            "average_risk_score": round(average_risk_score, 4),
            "results": results,
        }
