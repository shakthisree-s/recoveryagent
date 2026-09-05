import joblib
import pandas as pd
from datetime import datetime


class RevenueRecoveryAgent:

    def __init__(self):
        self.model = joblib.load("revenue_risk_model.joblib")

        # Bounded policies
        self.MAX_INCENTIVE_PERCENT = 10
        self.MAX_PAYMENT_ATTEMPTS = 3
        self.MAX_RECOVERY_AMOUNT = 100000
        self.HIGH_VALUE_APPROVAL_THRESHOLD = 25000

    # =========================================================
    # STAGE 1: DETECT → STAGE 2: DIAGNOSE → STAGE 3: DECIDE
    # =========================================================
    def analyze(self, case):

        # Extract features for model
        feature_cols = [
            "amount", "promo_amount", "shipment_fee", "transaction_hour",
            "transaction_day", "payment_method", "gender", "device_type",
            "home_country", "total_transactions", "successful_payments",
            "failed_payments", "average_transaction_amount", "total_spend",
            "failure_rate"
        ]

        model_row = {}
        for col in feature_cols:
            if col in case:
                model_row[col] = case[col]
            elif col == "amount":
                model_row[col] = case.get("total_amount", 0)
            elif col == "failure_rate":
                tot = case.get("total_transactions", 0)
                fail = case.get("failed_payments", 0)
                model_row[col] = fail / tot if tot > 0 else 0.0
            else:
                model_row[col] = 0

        df = pd.DataFrame([model_row])

        risk_probability = self.model.predict_proba(df)[0][1]

        amount = float(
            case.get("amount", case.get("total_amount", 0))
        )

        payment_status = case.get("payment_status", "Unknown")
        failed_payments = case.get("failed_payments", 0)
        total_transactions = case.get("total_transactions", 0)
        requested_incentive = float(case.get("requested_incentive_percent", 0.0))
        attempts_count = int(case.get("current_attempts", len(case.get("attempts", []))))

        if total_transactions > 0:
            historical_failure_rate = failed_payments / total_transactions
        else:
            historical_failure_rate = 0.0

        # ---------------- STAGE 2: DIAGNOSE ----------------
        if payment_status == "Success":
            diagnosis = "PAYMENT_SUCCESSFUL"
            diagnosis_label = "Payment already succeeded."
        elif attempts_count >= self.MAX_PAYMENT_ATTEMPTS:
            diagnosis = "MAX_ATTEMPTS_EXHAUSTED"
            diagnosis_label = f"Customer reached maximum payment attempts limit ({self.MAX_PAYMENT_ATTEMPTS})."
        elif requested_incentive > self.MAX_INCENTIVE_PERCENT:
            diagnosis = "INCENTIVE_EXCEEDS_POLICY"
            diagnosis_label = f"Requested incentive of {requested_incentive}% exceeds policy limit of {self.MAX_INCENTIVE_PERCENT}%."
        elif amount >= self.HIGH_VALUE_APPROVAL_THRESHOLD:
            diagnosis = "HIGH_VALUE_PAYMENT_FAILURE"
            diagnosis_label = f"High-value failed transaction (₹{amount:,.0f}) exceeds autonomous threshold (₹{self.HIGH_VALUE_APPROVAL_THRESHOLD:,.0f})."
        elif failed_payments >= 3 or historical_failure_rate >= 0.50:
            diagnosis = "REPEATED_FAILURE"
            diagnosis_label = "High frequency of previous payment failures detected."
        elif case.get("is_checkout_abandoned", False):
            diagnosis = "CHECKOUT_ABANDONED"
            diagnosis_label = "Customer abandoned checkout flow prior to completion."
        elif risk_probability >= 0.60:
            diagnosis = "PAYMENT_RETRYABLE"
            diagnosis_label = "Strong payment failure risk detected; suitable for retry."
        elif risk_probability >= 0.30 or payment_status == "Failed":
            diagnosis = "PAYMENT_FAILED"
            diagnosis_label = "Moderate payment-risk signal detected; recovery intervention recommended."
        else:
            diagnosis = "LOW_RISK_HEALTHY"
            diagnosis_label = "No significant payment failure risk detected."

        # ---------------- STAGE 3: DECIDE & POLICY ----------------
        if payment_status == "Success":
            risk_level = "LOW"
            action = "NO_ACTION"
            reason = "Payment already succeeded."
            policy_evaluation = "ALLOWED"

        elif attempts_count >= self.MAX_PAYMENT_ATTEMPTS:
            risk_level = "HIGH"
            action = "STOP"
            reason = f"Maximum recovery attempts ({self.MAX_PAYMENT_ATTEMPTS}) reached. Stopping rules enforce cessation."
            policy_evaluation = "BLOCKED"

        elif requested_incentive > self.MAX_INCENTIVE_PERCENT:
            risk_level = "HIGH"
            action = "OFFER_BOUNDED_INCENTIVE"
            reason = f"Requested incentive of {requested_incentive}% exceeds allowed maximum of {self.MAX_INCENTIVE_PERCENT}%."
            policy_evaluation = "BLOCKED"

        elif amount >= self.HIGH_VALUE_APPROVAL_THRESHOLD:
            risk_level = "HIGH"
            action = "ESCALATE_TO_HUMAN"
            reason = f"High-value payment (₹{amount:,.0f}) requires human supervisor approval."
            policy_evaluation = "HUMAN_APPROVAL_REQUIRED"

        elif risk_probability >= 0.60 or historical_failure_rate >= 0.50:
            risk_level = "HIGH"
            action = "RETRY_PAYMENT"
            reason = "Strong payment-failure signal detected. Autonomous payment retry selected."
            policy_evaluation = "ALLOWED"

        elif risk_probability >= 0.30 or payment_status == "Failed":
            risk_level = "MEDIUM"
            action = "SEND_RECOVERY_LINK"
            reason = "Moderate payment-risk signal detected. Recovery link dispatch selected."
            policy_evaluation = "ALLOWED"

        elif case.get("is_checkout_abandoned", False):
            risk_level = "MEDIUM"
            action = "SEND_PAYMENT_REMINDER"
            reason = "Checkout abandoned. Payment reminder selected."
            policy_evaluation = "ALLOWED"

        else:
            risk_level = "LOW"
            action = "NO_ACTION"
            reason = "No recovery intervention required."
            policy_evaluation = "ALLOWED"

        return {
            "risk_probability": round(float(risk_probability), 4),
            "risk_score": round(float(risk_probability), 4),
            "risk_level": risk_level,
            "diagnosis": diagnosis,
            "diagnosis_label": diagnosis_label,
            "recommended_action": action,
            "decision": action,
            "policy_evaluation": policy_evaluation,
            "reason": reason,
            "amount": amount,
            "historical_failure_rate": round(historical_failure_rate, 4),
            "attempts_count": attempts_count,
            "requested_incentive_percent": requested_incentive,
            "stopping_reason": "MAX_PAYMENT_ATTEMPTS_REACHED" if attempts_count >= self.MAX_PAYMENT_ATTEMPTS else None
        }

    # =========================================================
    # STAGE 4: EXECUTE RECOVERY
    # =========================================================
    def execute_recovery(self, case, simulate_failure=False):

        analysis = self.analyze(case)

        action = analysis["recommended_action"]
        amount = analysis["amount"]
        attempts_count = analysis["attempts_count"] + 1

        timestamp = datetime.now().isoformat(timespec="seconds")

        result = {
            "timestamp": timestamp,
            "action": action,
            "status": "NOT_EXECUTED",
            "amount_at_risk": amount,
            "recovered_amount": 0.0,
            "reason": analysis["reason"],
            "diagnosis": analysis["diagnosis"],
            "policy_evaluation": analysis["policy_evaluation"],
            "audit_event": None,
            "attempt": attempts_count,
            "stopping_reason": None
        }

        # ---------------- STOPPING RULE: MAX ATTEMPTS ----------------
        if attempts_count > self.MAX_PAYMENT_ATTEMPTS or action == "STOP":
            result["status"] = "BLOCKED"
            result["action"] = "STOP"
            result["reason"] = f"Maximum recovery attempts limit ({self.MAX_PAYMENT_ATTEMPTS}) reached. Recovery halted by stopping rules."
            result["audit_event"] = "RECOVERY_STOPPED"
            result["stopping_reason"] = "MAX_PAYMENT_ATTEMPTS_REACHED"
            return result

        # ---------------- NO ACTION ----------------
        if action == "NO_ACTION":
            result["status"] = "NO_ACTION"
            result["reason"] = "No recovery required."
            result["audit_event"] = "NO_ACTION"
            return result

        # ---------------- POLICY BLOCK: INCENTIVE ----------------
        if action == "OFFER_BOUNDED_INCENTIVE" and analysis["policy_evaluation"] == "BLOCKED":
            result["status"] = "BLOCKED"
            result["reason"] = f"Incentive of {analysis['requested_incentive_percent']}% exceeds max allowed {self.MAX_INCENTIVE_PERCENT}%."
            result["audit_event"] = "POLICY_BLOCKED"
            result["stopping_reason"] = "POLICY_GUARDRAIL_VIOLATION"
            return result

        # ---------------- HUMAN APPROVAL ----------------
        if action == "ESCALATE_TO_HUMAN":
            result["status"] = "HUMAN_APPROVAL_REQUIRED"
            result["reason"] = f"High-value recovery (₹{amount:,.0f}) requires human supervisor approval."
            result["audit_event"] = "HUMAN_APPROVAL_REQUIRED"
            return result

        # ---------------- SAFETY LIMIT ----------------
        if amount > self.MAX_RECOVERY_AMOUNT:
            result["status"] = "BLOCKED"
            result["reason"] = f"Amount ₹{amount:,.0f} exceeds max autonomous recovery limit ₹{self.MAX_RECOVERY_AMOUNT:,.0f}."
            result["audit_event"] = "POLICY_BLOCKED"
            result["stopping_reason"] = "EXCEEDS_MAX_RECOVERY_AMOUNT"
            return result

        # ---------------- SIMULATED FAILURE ----------------
        if simulate_failure:
            result["status"] = "RETRY_AVAILABLE"
            result["recovered_amount"] = 0.0
            result["reason"] = "Recovery attempt 1 unfulfilled in test mode. Retry is permitted by policy."
            result["audit_event"] = "RECOVERY_FAILED"
            return result

        # ---------------- SUCCESSFUL RECOVERY ----------------
        if action == "RETRY_PAYMENT":
            result["status"] = "RECOVERED"
            result["recovered_amount"] = amount
            result["reason"] = "Autonomous payment retry succeeded in test mode."
            result["audit_event"] = "PAYMENT_RETRY_SUCCESS"

        elif action == "SEND_RECOVERY_LINK":
            result["status"] = "RECOVERED"
            result["recovered_amount"] = amount
            result["reason"] = "Customer completed payment via recovery link in test mode."
            result["audit_event"] = "RECOVERY_LINK_PAYMENT_SUCCESS"

        elif action == "SEND_PAYMENT_REMINDER":
            result["status"] = "RECOVERED"
            result["recovered_amount"] = amount
            result["reason"] = "Customer paid following recovery reminder in test mode."
            result["audit_event"] = "REMINDER_PAYMENT_SUCCESS"

        elif action == "OFFER_BOUNDED_INCENTIVE":
            result["status"] = "RECOVERED"
            result["recovered_amount"] = amount
            result["reason"] = "Customer converted with bounded 5% recovery incentive in test mode."
            result["audit_event"] = "RECOVERY_SUCCEEDED"

        else:
            result["status"] = "BLOCKED"
            result["reason"] = "Action not permitted by policy."
            result["audit_event"] = "POLICY_BLOCKED"

        return result

    # =========================================================
    # HUMAN APPROVAL
    # =========================================================
    def approve_recovery(self, case):

        analysis = self.analyze(case)
        amount = analysis["amount"]

        if analysis["recommended_action"] != "ESCALATE_TO_HUMAN":
            return {
                "status": "NOT_REQUIRED",
                "recovered_amount": 0.0,
                "audit_event": "APPROVAL_NOT_REQUIRED"
            }

        if amount > self.MAX_RECOVERY_AMOUNT:
            return {
                "status": "BLOCKED",
                "recovered_amount": 0.0,
                "audit_event": "POLICY_BLOCKED",
                "stopping_reason": "EXCEEDS_MAX_RECOVERY_AMOUNT"
            }

        timestamp = datetime.now().isoformat(timespec="seconds")

        return {
            "timestamp": timestamp,
            "status": "RECOVERED",
            "action": "APPROVED_RETRY_PAYMENT",
            "recovered_amount": amount,
            "amount_at_risk": amount,
            "reason": "Human operator approved high-value recovery execution.",
            "audit_event": "HUMAN_APPROVAL_AND_RECOVERY"
        }

    # =========================================================
    # RETRY RECOVERY
    # =========================================================
    def retry_recovery(self, case):

        analysis = self.analyze(case)
        amount = analysis["amount"]
        attempts_count = int(case.get("current_attempts", len(case.get("attempts", [])))) + 1

        timestamp = datetime.now().isoformat(timespec="seconds")

        if attempts_count > self.MAX_PAYMENT_ATTEMPTS:
            return {
                "timestamp": timestamp,
                "attempt": attempts_count,
                "action": "STOP",
                "status": "BLOCKED",
                "amount_at_risk": amount,
                "recovered_amount": 0.0,
                "reason": f"Maximum recovery attempts ({self.MAX_PAYMENT_ATTEMPTS}) reached. Recovery stopped.",
                "audit_event": "RECOVERY_STOPPED",
                "stopping_reason": "MAX_PAYMENT_ATTEMPTS_REACHED"
            }

        return {
            "timestamp": timestamp,
            "attempt": attempts_count,
            "action": "RETRY_RECOVERY",
            "status": "RECOVERED",
            "amount_at_risk": amount,
            "recovered_amount": amount,
            "reason": f"Payment retry succeeded on attempt {attempts_count} in test mode.",
            "audit_event": "RECOVERY_RETRY_SUCCESS"
        }

    # =========================================================
    # BATCH RECOVERY
    # =========================================================
    def run_batch(self, cases):

        results = []

        total_revenue_at_risk = 0.0
        total_revenue_recovered = 0.0

        recovered_cases = 0
        failed_cases = 0
        blocked_cases = 0
        approval_cases = 0
        at_risk_cases = 0

        for index, case in enumerate(cases, start=1):

            analysis = self.analyze(case)
            recovery = self.execute_recovery(case)

            amount = analysis["amount"]
            recovered = recovery["recovered_amount"]

            if analysis["recommended_action"] != "NO_ACTION":
                total_revenue_at_risk += amount
                at_risk_cases += 1

            total_revenue_recovered += recovered

            if recovery["status"] == "RECOVERED":
                recovered_cases += 1
            elif recovery["status"] == "HUMAN_APPROVAL_REQUIRED":
                approval_cases += 1
            elif recovery["status"] == "BLOCKED":
                blocked_cases += 1
            elif recovery["status"] in ["RETRY_AVAILABLE", "NOT_EXECUTED"]:
                failed_cases += 1

            result = {
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
                "status": recovery["status"],
                "recovered_amount": recovered,
                "audit_event": recovery["audit_event"],
                "stopping_reason": recovery.get("stopping_reason")
            }

            results.append(result)

        if total_revenue_at_risk > 0:
            recovery_rate = (total_revenue_recovered / total_revenue_at_risk) * 100
        else:
            recovery_rate = 0.0

        return {
            "total_cases": len(cases),
            "at_risk_cases": at_risk_cases,
            "recovered_cases": recovered_cases,
            "failed_cases": failed_cases,
            "blocked_cases": blocked_cases,
            "approval_cases": approval_cases,
            "total_revenue_at_risk": round(total_revenue_at_risk, 2),
            "total_revenue_recovered": round(total_revenue_recovered, 2),
            "recovery_rate": round(recovery_rate, 2),
            "results": results
        }