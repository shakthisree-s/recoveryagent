import copy
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import RevenueRecoveryAgent
from backend.data import INITIAL_CASES


AUDIT_LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_log.json"
)
MODEL_METADATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_metadata.json"
)


class StateManager:
    def __init__(self):
        self.agent = RevenueRecoveryAgent()
        self.cases: Dict[int, Dict[str, Any]] = {}
        self.batch_history: Dict[str, Dict[str, Any]] = {}
        self.reset_state()

    def reset_state(self):
        """Reset state to initial benchmark cases with analyzed defaults."""
        self.cases = {}
        initial_audit_events = []
        now_ts = datetime.now().isoformat(timespec="seconds")

        for c in copy.deepcopy(INITIAL_CASES):
            case_id = c["case_id"]
            analysis = self.agent.analyze(c)
            c["risk_probability"] = analysis["risk_probability"]
            c["risk_score"] = analysis["risk_score"]
            c["risk_level"] = analysis["risk_level"]
            c["diagnosis"] = analysis["diagnosis"]
            c["diagnosis_label"] = analysis["diagnosis_label"]
            c["cause"] = analysis["reason"]
            c["reason"] = analysis["reason"]
            c["recommended_action"] = analysis["recommended_action"]
            c["policy_evaluation"] = analysis["policy_evaluation"]
            c["stopping_reason"] = analysis.get("stopping_reason")

            # Determine initial status
            if c.get("current_attempts", 0) >= self.agent.MAX_PAYMENT_ATTEMPTS:
                c["status"] = "BLOCKED"
                c["stopping_reason"] = "MAX_PAYMENT_ATTEMPTS_REACHED"
            elif c.get("requested_incentive_percent", 0) > self.agent.MAX_INCENTIVE_PERCENT:
                c["status"] = "BLOCKED"
                c["stopping_reason"] = "POLICY_GUARDRAIL_VIOLATION"
            elif analysis["recommended_action"] == "NO_ACTION":
                c["status"] = "NO_ACTION"
            elif analysis["recommended_action"] == "ESCALATE_TO_HUMAN":
                c["status"] = "HUMAN_APPROVAL_REQUIRED"
            else:
                c["status"] = "PENDING"

            c["recovered_amount"] = 0.0
            if not c.get("attempts"):
                c["attempts"] = []
            self.cases[case_id] = c

            initial_audit_events.append({
                "timestamp": now_ts,
                "batch_id": None,
                "case_id": case_id,
                "customer_id": c.get("customer_id"),
                "payment_id": c.get("payment_id"),
                "case_name": c.get("name", f"Case {case_id}"),
                "agent": "RevenueRecoveryAgent",
                "agent_stage": "DETECT",
                "risk_level": c["risk_level"],
                "risk_probability": c["risk_probability"],
                "risk_score": c["risk_score"],
                "diagnosis": c["diagnosis"],
                "decision": c["recommended_action"],
                "policy_evaluation": c["policy_evaluation"],
                "status": c["status"],
                "amount_at_risk": c["amount"],
                "recovered_amount": 0.0,
                "reason": c["reason"],
                "audit_event": "CASE_DETECTED",
                "stopping_reason": c.get("stopping_reason")
            })

        self.append_audit_log(initial_audit_events)

    def get_all_cases(self) -> List[Dict[str, Any]]:
        return list(self.cases.values())

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def generate_decision_flow(self, case: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates visual steps for the single Revenue Recovery Agent flow."""
        risk_pct = round(analysis["risk_probability"] * 100, 2)
        amount = analysis["amount"]
        action = analysis["recommended_action"]
        current_status = case.get("status", "PENDING")
        stopping_reason = case.get("stopping_reason") or analysis.get("stopping_reason")

        policy_note = "Standard autonomous recovery limits apply."
        if case.get("current_attempts", len(case.get("attempts", []))) >= self.agent.MAX_PAYMENT_ATTEMPTS:
            policy_note = f"Stopping Rule: Max attempts ({self.agent.MAX_PAYMENT_ATTEMPTS}) reached. Autonomous recovery ceased."
        elif case.get("requested_incentive_percent", 0) > self.agent.MAX_INCENTIVE_PERCENT:
            policy_note = f"Policy Block: Requested incentive ({case['requested_incentive_percent']}%) exceeds max limit ({self.agent.MAX_INCENTIVE_PERCENT}%)."
        elif amount > self.agent.MAX_RECOVERY_AMOUNT:
            policy_note = f"Amount ₹{amount:,.0f} exceeds max recovery limit of ₹{self.agent.MAX_RECOVERY_AMOUNT:,.0f}."
        elif amount >= self.agent.HIGH_VALUE_APPROVAL_THRESHOLD:
            policy_note = f"High-value policy: Amount ₹{amount:,.0f} >= human threshold ₹{self.agent.HIGH_VALUE_APPROVAL_THRESHOLD:,.0f}. Escalation required."
        else:
            policy_note = f"Policy Allowed: Amount ₹{amount:,.0f} is within autonomous bounds (< ₹{self.agent.HIGH_VALUE_APPROVAL_THRESHOLD:,.0f})."

        steps = [
            {
                "step": "DETECT",
                "title": "Revenue at Risk Detection",
                "content": f"ML Model scored payment failure risk at {risk_pct}% (Risk Level: {analysis['risk_level']}). Historical customer failure rate: {round(analysis['historical_failure_rate'] * 100, 1)}%.",
                "badge": f"{analysis['risk_level']} RISK",
                "status": "COMPLETED"
            },
            {
                "step": "DIAGNOSE",
                "title": "Root Cause Diagnosis",
                "content": f"Diagnosis: {analysis['diagnosis']} — {analysis['diagnosis_label']}",
                "badge": analysis['diagnosis'],
                "status": "COMPLETED"
            },
            {
                "step": "DECIDE",
                "title": "Action Determination",
                "content": f"Agent selected bounded action: {action}. {analysis['reason']}",
                "badge": action,
                "status": "COMPLETED"
            },
            {
                "step": "POLICY",
                "title": "Policy Engine & Guardrails",
                "content": policy_note,
                "badge": analysis['policy_evaluation'],
                "status": "COMPLETED"
            },
            {
                "step": "EXECUTE",
                "title": "Test-Mode Recovery Execution",
                "content": f"Execution status: {current_status}. Bounded simulation in Razorpay Test Mode.",
                "badge": "RAZORPAY_TEST_MODE",
                "status": "COMPLETED" if current_status != "PENDING" else "PENDING"
            },
            {
                "step": "RESULT",
                "title": "Outcome & Settlement",
                "content": f"₹{case.get('recovered_amount', 0):,.2f} recovered successfully (Simulated)." if case.get('recovered_amount', 0) > 0 else (f"Recovery stopped. Reason: {stopping_reason}" if stopping_reason else f"Current state: {current_status}."),
                "badge": current_status,
                "status": "COMPLETED" if case.get('recovered_amount', 0) > 0 or current_status in ["BLOCKED", "NO_ACTION"] else "PENDING"
            }
        ]
        return steps

    def analyze_case(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        analysis = self.agent.analyze(case)
        decision_flow = self.generate_decision_flow(case, analysis)
        return {
            "case_id": case_id,
            "customer_id": case.get("customer_id"),
            "customer": case.get("customer", case.get("name")),
            "amount": analysis["amount"],
            "risk_probability": analysis["risk_probability"],
            "risk_score": analysis["risk_score"],
            "risk_level": analysis["risk_level"],
            "diagnosis": analysis["diagnosis"],
            "diagnosis_label": analysis["diagnosis_label"],
            "reason": analysis["reason"],
            "recommended_action": analysis["recommended_action"],
            "policy_evaluation": analysis["policy_evaluation"],
            "stopping_reason": analysis.get("stopping_reason"),
            "historical_failure_rate": analysis["historical_failure_rate"],
            "decision_flow": decision_flow
        }

    def execute_recovery(self, case_id: int, simulate_failure: bool = False) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        if case["status"] == "RECOVERED":
            raise ValueError(f"Case {case_id} has already been recovered.")

        # Check stopping rule
        current_attempts = len(case.get("attempts", []))
        if current_attempts >= self.agent.MAX_PAYMENT_ATTEMPTS:
            case["status"] = "BLOCKED"
            case["stopping_reason"] = "MAX_PAYMENT_ATTEMPTS_REACHED"
            raise ValueError(f"Case {case_id} reached max payment attempts ({self.agent.MAX_PAYMENT_ATTEMPTS}). Recovery halted by stopping rules.")

        # Execute using agent
        recovery = self.agent.execute_recovery(case, simulate_failure=simulate_failure)
        timestamp = recovery["timestamp"]
        attempt_num = len(case.get("attempts", [])) + 1

        # Record attempt
        attempt_record = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "action": recovery["action"],
            "status": recovery["status"],
            "recovered_amount": recovery["recovered_amount"],
            "reason": recovery["reason"],
            "audit_event": recovery["audit_event"],
            "stopping_reason": recovery.get("stopping_reason")
        }
        case["attempts"].append(attempt_record)
        case["current_attempts"] = attempt_num
        case["status"] = recovery["status"]
        case["recovered_amount"] = recovery["recovered_amount"]
        case["stopping_reason"] = recovery.get("stopping_reason")

        # Add to audit log
        audit_entry = {
            "timestamp": timestamp,
            "batch_id": None,
            "case_id": case["case_id"],
            "customer_id": case.get("customer_id"),
            "payment_id": case.get("payment_id"),
            "case_name": case.get("name", f"Case {case_id}"),
            "agent": "RevenueRecoveryAgent",
            "agent_stage": "EXECUTE",
            "risk_level": case.get("risk_level", "MEDIUM"),
            "risk_probability": case.get("risk_probability", 0.0),
            "risk_score": case.get("risk_score", 0.0),
            "diagnosis": recovery.get("diagnosis", case.get("diagnosis")),
            "decision": recovery["action"],
            "policy_evaluation": recovery.get("policy_evaluation", case.get("policy_evaluation")),
            "status": recovery["status"],
            "amount_at_risk": recovery["amount_at_risk"],
            "recovered_amount": recovery["recovered_amount"],
            "reason": recovery["reason"],
            "audit_event": recovery["audit_event"],
            "stopping_reason": recovery.get("stopping_reason")
        }
        self.append_audit_log([audit_entry])

        summary = self.get_case_summary(case_id)
        return {
            "case_id": case_id,
            "status": recovery["status"],
            "action": recovery["action"],
            "amount_at_risk": recovery["amount_at_risk"],
            "recovered_amount": recovery["recovered_amount"],
            "reason": recovery["reason"],
            "diagnosis": recovery.get("diagnosis"),
            "policy_evaluation": recovery.get("policy_evaluation"),
            "stopping_reason": recovery.get("stopping_reason"),
            "audit_event": recovery["audit_event"],
            "attempt": attempt_num,
            "timestamp": timestamp,
            "updated_case": summary
        }

    def retry_recovery(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        if case["status"] != "RETRY_AVAILABLE":
            raise ValueError(f"Case {case_id} is not in RETRY_AVAILABLE status (Current: {case['status']}).")

        retry_result = self.agent.retry_recovery(case)
        timestamp = retry_result["timestamp"]
        attempt_num = len(case.get("attempts", [])) + 1

        attempt_record = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "action": retry_result["action"],
            "status": retry_result["status"],
            "recovered_amount": retry_result["recovered_amount"],
            "reason": retry_result["reason"],
            "audit_event": retry_result["audit_event"],
            "stopping_reason": retry_result.get("stopping_reason")
        }
        case["attempts"].append(attempt_record)
        case["current_attempts"] = attempt_num
        case["status"] = retry_result["status"]
        case["recovered_amount"] = retry_result["recovered_amount"]
        case["stopping_reason"] = retry_result.get("stopping_reason")

        audit_entry = {
            "timestamp": timestamp,
            "batch_id": None,
            "case_id": case["case_id"],
            "customer_id": case.get("customer_id"),
            "payment_id": case.get("payment_id"),
            "case_name": case.get("name", f"Case {case_id}"),
            "agent": "RevenueRecoveryAgent",
            "agent_stage": "EXECUTE",
            "risk_level": case.get("risk_level", "MEDIUM"),
            "risk_probability": case.get("risk_probability", 0.0),
            "risk_score": case.get("risk_score", 0.0),
            "diagnosis": case.get("diagnosis"),
            "decision": retry_result["action"],
            "policy_evaluation": "ALLOWED",
            "status": retry_result["status"],
            "amount_at_risk": retry_result["amount_at_risk"],
            "recovered_amount": retry_result["recovered_amount"],
            "reason": retry_result["reason"],
            "audit_event": retry_result["audit_event"],
            "stopping_reason": retry_result.get("stopping_reason")
        }
        self.append_audit_log([audit_entry])

        summary = self.get_case_summary(case_id)
        return {
            "case_id": case_id,
            "status": retry_result["status"],
            "action": retry_result["action"],
            "amount_at_risk": retry_result["amount_at_risk"],
            "recovered_amount": retry_result["recovered_amount"],
            "reason": retry_result["reason"],
            "diagnosis": case.get("diagnosis"),
            "policy_evaluation": "ALLOWED",
            "stopping_reason": retry_result.get("stopping_reason"),
            "audit_event": retry_result["audit_event"],
            "attempt": attempt_num,
            "timestamp": timestamp,
            "updated_case": summary
        }

    def approve_recovery(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        if case["status"] not in ["HUMAN_APPROVAL_REQUIRED", "PENDING"]:
            raise ValueError(f"Case {case_id} does not require human approval.")

        approval_result = self.agent.approve_recovery(case)
        timestamp = approval_result.get("timestamp", datetime.now().isoformat(timespec="seconds"))
        attempt_num = len(case.get("attempts", [])) + 1

        case["status"] = approval_result["status"]
        case["recovered_amount"] = approval_result["recovered_amount"]
        case["current_attempts"] = attempt_num

        attempt_record = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "action": approval_result.get("action", "APPROVED_RETRY_PAYMENT"),
            "status": approval_result["status"],
            "recovered_amount": approval_result["recovered_amount"],
            "reason": approval_result["reason"],
            "audit_event": approval_result["audit_event"]
        }
        case["attempts"].append(attempt_record)

        audit_entry = {
            "timestamp": timestamp,
            "batch_id": None,
            "case_id": case["case_id"],
            "customer_id": case.get("customer_id"),
            "payment_id": case.get("payment_id"),
            "case_name": case.get("name", f"Case {case_id}"),
            "agent": "RevenueRecoveryAgent",
            "agent_stage": "EXECUTE",
            "risk_level": case.get("risk_level", "HIGH"),
            "risk_probability": case.get("risk_probability", 0.0),
            "risk_score": case.get("risk_score", 0.0),
            "diagnosis": case.get("diagnosis", "HIGH_VALUE_PAYMENT_FAILURE"),
            "decision": approval_result.get("action", "APPROVED_RETRY_PAYMENT"),
            "policy_evaluation": "HUMAN_APPROVED",
            "status": approval_result["status"],
            "amount_at_risk": case["amount"],
            "recovered_amount": approval_result["recovered_amount"],
            "reason": approval_result["reason"],
            "audit_event": approval_result["audit_event"]
        }
        self.append_audit_log([audit_entry])

        summary = self.get_case_summary(case_id)
        return {
            "case_id": case_id,
            "status": approval_result["status"],
            "action": approval_result.get("action", "APPROVED_RETRY_PAYMENT"),
            "amount_at_risk": case["amount"],
            "recovered_amount": approval_result["recovered_amount"],
            "reason": approval_result["reason"],
            "diagnosis": case.get("diagnosis"),
            "policy_evaluation": "HUMAN_APPROVED",
            "stopping_reason": None,
            "audit_event": approval_result["audit_event"],
            "attempt": attempt_num,
            "timestamp": timestamp,
            "updated_case": summary
        }

    def reject_recovery(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        timestamp = datetime.now().isoformat(timespec="seconds")
        attempt_num = len(case.get("attempts", [])) + 1
        case["status"] = "BLOCKED"
        case["recovered_amount"] = 0.0
        case["stopping_reason"] = "HUMAN_OPERATOR_REJECTED"

        attempt_record = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "action": "REJECT_RECOVERY",
            "status": "BLOCKED",
            "recovered_amount": 0.0,
            "reason": "Human operator rejected high-value recovery execution.",
            "audit_event": "HUMAN_REJECTED",
            "stopping_reason": "HUMAN_OPERATOR_REJECTED"
        }
        case["attempts"].append(attempt_record)

        audit_entry = {
            "timestamp": timestamp,
            "batch_id": None,
            "case_id": case["case_id"],
            "customer_id": case.get("customer_id"),
            "payment_id": case.get("payment_id"),
            "case_name": case.get("name", f"Case {case_id}"),
            "agent": "RevenueRecoveryAgent",
            "agent_stage": "EXECUTE",
            "risk_level": case.get("risk_level", "HIGH"),
            "risk_probability": case.get("risk_probability", 0.0),
            "risk_score": case.get("risk_score", 0.0),
            "diagnosis": case.get("diagnosis"),
            "decision": "REJECT_RECOVERY",
            "policy_evaluation": "HUMAN_REJECTED",
            "status": "BLOCKED",
            "amount_at_risk": case["amount"],
            "recovered_amount": 0.0,
            "reason": "Human operator rejected high-value recovery execution.",
            "audit_event": "HUMAN_REJECTED",
            "stopping_reason": "HUMAN_OPERATOR_REJECTED"
        }
        self.append_audit_log([audit_entry])

        summary = self.get_case_summary(case_id)
        return {
            "case_id": case_id,
            "status": "BLOCKED",
            "action": "REJECT_RECOVERY",
            "amount_at_risk": case["amount"],
            "recovered_amount": 0.0,
            "reason": "Human operator rejected high-value recovery execution.",
            "diagnosis": case.get("diagnosis"),
            "policy_evaluation": "HUMAN_REJECTED",
            "stopping_reason": "HUMAN_OPERATOR_REJECTED",
            "audit_event": "HUMAN_REJECTED",
            "attempt": attempt_num,
            "timestamp": timestamp,
            "updated_case": summary
        }

    def run_batch(self) -> Dict[str, Any]:
        """Runs the agent's batch execution across all cases."""
        raw_cases = list(self.cases.values())

        batch_result = self.agent.run_batch(raw_cases)
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat(timespec="seconds")

        audit_events = []
        for item in batch_result["results"]:
            cid = item["case_id"]
            if cid in self.cases:
                self.cases[cid]["status"] = item["status"]
                self.cases[cid]["recovered_amount"] = item["recovered_amount"]
                self.cases[cid]["risk_probability"] = item["risk_probability"]
                self.cases[cid]["risk_score"] = item["risk_score"]
                self.cases[cid]["risk_level"] = item["risk_level"]
                self.cases[cid]["diagnosis"] = item["diagnosis"]
                self.cases[cid]["diagnosis_label"] = item["diagnosis_label"]
                self.cases[cid]["reason"] = item["reason"]
                self.cases[cid]["recommended_action"] = item["action"]
                self.cases[cid]["policy_evaluation"] = item["policy_evaluation"]
                self.cases[cid]["stopping_reason"] = item.get("stopping_reason")
                
                self.cases[cid]["attempts"].append({
                    "attempt": len(self.cases[cid]["attempts"]) + 1,
                    "timestamp": timestamp,
                    "action": item["action"],
                    "status": item["status"],
                    "recovered_amount": item["recovered_amount"],
                    "reason": item["reason"],
                    "audit_event": item["audit_event"],
                    "stopping_reason": item.get("stopping_reason")
                })

            audit_events.append({
                "timestamp": timestamp,
                "batch_id": batch_id,
                "case_id": cid,
                "customer_id": item.get("customer_id"),
                "payment_id": item.get("payment_id"),
                "case_name": item["name"],
                "agent": "RevenueRecoveryAgent",
                "agent_stage": "EXECUTE",
                "risk_level": item["risk_level"],
                "risk_probability": item["risk_probability"],
                "risk_score": item["risk_score"],
                "diagnosis": item["diagnosis"],
                "decision": item["action"],
                "policy_evaluation": item["policy_evaluation"],
                "status": item["status"],
                "amount_at_risk": item["amount"],
                "recovered_amount": item["recovered_amount"],
                "reason": item["reason"],
                "audit_event": item["audit_event"],
                "stopping_reason": item.get("stopping_reason")
            })

        self.append_audit_log(audit_events)

        response_data = {
            "batch_id": batch_id,
            "timestamp": timestamp,
            "total_cases": batch_result["total_cases"],
            "at_risk_cases": batch_result["at_risk_cases"],
            "recovered_cases": batch_result["recovered_cases"],
            "failed_cases": batch_result["failed_cases"],
            "blocked_cases": batch_result["blocked_cases"],
            "approval_cases": batch_result["approval_cases"],
            "total_revenue_at_risk": batch_result["total_revenue_at_risk"],
            "total_revenue_recovered": batch_result["total_revenue_recovered"],
            "recovery_rate": batch_result["recovery_rate"],
            "results": batch_result["results"]
        }
        self.batch_history[batch_id] = response_data
        return response_data

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        return self.batch_history.get(batch_id)

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates live metrics from active cases dynamically."""
        total_cases = len(self.cases)
        at_risk_cases = 0
        recovered_cases = 0
        failed_cases = 0
        blocked_cases = 0
        approval_cases = 0
        retry_available_cases = 0

        total_revenue_at_risk = 0.0
        total_revenue_recovered = 0.0

        for case in self.cases.values():
            amount = case["amount"]
            recovered = case.get("recovered_amount", 0.0)
            status = case.get("status", "PENDING")
            action = case.get("recommended_action", "NO_ACTION")

            if action != "NO_ACTION":
                total_revenue_at_risk += amount
                at_risk_cases += 1

            total_revenue_recovered += recovered

            if status == "RECOVERED":
                recovered_cases += 1
            elif status == "HUMAN_APPROVAL_REQUIRED":
                approval_cases += 1
            elif status == "RETRY_AVAILABLE":
                retry_available_cases += 1
                failed_cases += 1
            elif status == "BLOCKED":
                blocked_cases += 1
            elif status == "NOT_EXECUTED":
                failed_cases += 1

        recovery_rate = (
            (total_revenue_recovered / total_revenue_at_risk * 100)
            if total_revenue_at_risk > 0 else 0.0
        )

        return {
            "total_cases": total_cases,
            "at_risk_cases": at_risk_cases,
            "recovered_cases": recovered_cases,
            "failed_cases": failed_cases,
            "blocked_cases": blocked_cases,
            "approval_cases": approval_cases,
            "retry_available_cases": retry_available_cases,
            "total_revenue_at_risk": round(total_revenue_at_risk, 2),
            "total_revenue_recovered": round(total_revenue_recovered, 2),
            "recovery_rate": round(recovery_rate, 2),
            "policy_limits": {
                "max_incentive_percent": self.agent.MAX_INCENTIVE_PERCENT,
                "max_recovery_amount": self.agent.MAX_RECOVERY_AMOUNT,
                "high_value_approval_threshold": self.agent.HIGH_VALUE_APPROVAL_THRESHOLD,
                "max_payment_attempts": self.agent.MAX_PAYMENT_ATTEMPTS
            }
        }

    def get_case_summary(self, case_id: int) -> Dict[str, Any]:
        c = self.get_case(case_id)
        if not c:
            raise ValueError(f"Case {case_id} not found")
        return {
            "case_id": c["case_id"],
            "customer_id": c.get("customer_id"),
            "payment_id": c.get("payment_id"),
            "customer": c.get("customer", c.get("name")),
            "amount": c["amount"],
            "payment_status": c.get("payment_status", "Unknown"),
            "risk_probability": c.get("risk_probability", 0.0),
            "risk_score": c.get("risk_score", 0.0),
            "risk_level": c.get("risk_level", "LOW"),
            "diagnosis": c.get("diagnosis", "LOW_RISK_HEALTHY"),
            "diagnosis_label": c.get("diagnosis_label", ""),
            "cause": c.get("cause", c.get("reason", "")),
            "recommended_action": c.get("recommended_action", "NO_ACTION"),
            "policy_evaluation": c.get("policy_evaluation", "ALLOWED"),
            "stopping_reason": c.get("stopping_reason"),
            "status": c.get("status", "PENDING"),
            "recovered_amount": c.get("recovered_amount", 0.0)
        }

    def get_model_metrics(self) -> Dict[str, Any]:
        if os.path.exists(MODEL_METADATA_FILE):
            with open(MODEL_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "model": "RandomForestClassifier",
            "dataset_size": 50000,
            "training_rows": 40000,
            "testing_rows": 10000,
            "accuracy": 0.9243,
            "precision": 0.8912,
            "recall": 0.83,
            "f1_score": 0.8596,
            "roc_auc": 0.9656,
            "failed_payment_recall": 0.83,
            "features": []
        }

    def get_audit_logs(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(AUDIT_LOG_FILE):
            return []
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if case_id is not None:
                return [l for l in logs if l.get("case_id") == case_id]
            return list(reversed(logs))
        except Exception:
            return []

    def append_audit_log(self, new_events: List[Dict[str, Any]]):
        current_logs = []
        if os.path.exists(AUDIT_LOG_FILE):
            try:
                with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                    current_logs = json.load(f)
            except Exception:
                current_logs = []

        current_logs.extend(new_events)
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(current_logs, f, indent=4)


# Global singleton
state_manager = StateManager()
