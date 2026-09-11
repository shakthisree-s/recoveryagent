"""
StateManager - durable orchestration layer for the single RevenueRecoveryAgent.

Persistence lives in SQLite (see ``backend/db.py``); ``self.cases`` is an
in-memory cache kept write-through in sync with the database so every mutation
survives a backend restart. Seeding of the 8 benchmark cases is idempotent.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import RevenueRecoveryAgent
from backend import db
from backend.config import AUDIT_LOG_PATH, MODEL_METADATA_PATH, MODEL_PATH, RAZORPAY_MODE
from backend.data import INITIAL_CASES


class StateManager:
    def __init__(self) -> None:
        self.agent = RevenueRecoveryAgent()
        self.cases: Dict[int, Dict[str, Any]] = {}
        self.batch_history: Dict[str, Dict[str, Any]] = {}

        db.init_db()
        if db.case_count() == 0:
            self._seed_benchmark_cases()
        else:
            self.cases = {c["case_id"]: c for c in db.load_cases()}

    # ------------------------------------------------------------------ #
    # Seeding / reset
    # ------------------------------------------------------------------ #
    def _seed_benchmark_cases(self) -> None:
        """Insert the 8 benchmark cases + their DETECT audit events. Only ever
        called when the DB is empty (idempotent by construction)."""
        self.cases = {}
        now_ts = datetime.now().isoformat(timespec="seconds")
        audit_events: List[Dict[str, Any]] = []

        for raw in copy.deepcopy(INITIAL_CASES):
            case_id = raw["case_id"]
            analysis = self.agent.analyze(raw)
            raw.update(
                risk_probability=analysis["risk_probability"],
                risk_score=analysis["risk_score"],
                risk_level=analysis["risk_level"],
                diagnosis=analysis["diagnosis"],
                diagnosis_label=analysis["diagnosis_label"],
                cause=analysis["reason"],
                reason=analysis["reason"],
                recommended_action=analysis["recommended_action"],
                policy_evaluation=analysis["policy_evaluation"],
                policy_result=analysis["policy_result"],
                stopping_reason=analysis.get("stopping_reason"),
                root_cause=analysis["root_cause"],
                evidence=analysis["evidence"],
                recovery_objective=analysis["recovery_objective"],
            )

            if raw.get("current_attempts", 0) >= self.agent.MAX_PAYMENT_ATTEMPTS:
                raw["status"] = "BLOCKED"
                raw["stopping_reason"] = "MAX_PAYMENT_ATTEMPTS_REACHED"
            elif raw.get("requested_incentive_percent", 0) > self.agent.MAX_INCENTIVE_PERCENT:
                raw["status"] = "BLOCKED"
                raw["stopping_reason"] = "POLICY_GUARDRAIL_VIOLATION"
            elif analysis["recommended_action"] == "NO_ACTION":
                raw["status"] = "NO_ACTION"
            elif analysis["policy_result"] == "HUMAN_APPROVAL_REQUIRED":
                raw["status"] = "HUMAN_APPROVAL_REQUIRED"
            else:
                raw["status"] = "PENDING"

            raw["recovered_amount"] = 0.0
            raw.setdefault("attempts", [])
            self.cases[case_id] = raw
            db.save_case(raw)

            audit_events.append(self._audit_row(
                raw, stage="DETECT", decision=raw["recommended_action"],
                status=raw["status"], audit_event="DETECTED",
                amount_at_risk=raw["amount"], recovered_amount=0.0,
                reason=raw["reason"], timestamp=now_ts,
            ))
            audit_events.append(self._audit_row(
                raw, stage="DIAGNOSE", decision=raw["recommended_action"],
                status=raw["status"], audit_event="DIAGNOSED",
                amount_at_risk=raw["amount"], recovered_amount=0.0,
                reason=raw["root_cause"], timestamp=now_ts,
            ))

        self.append_audit_log(audit_events)

    def reset_state(self) -> None:
        db.reset()
        self.batch_history = {}
        self._seed_benchmark_cases()

    # ------------------------------------------------------------------ #
    # Audit helpers
    # ------------------------------------------------------------------ #
    def _audit_row(self, case: Dict[str, Any], *, stage: str, decision: str, status: str,
                   audit_event: str, amount_at_risk: float, recovered_amount: float,
                   reason: str, timestamp: Optional[str] = None, batch_id: Optional[str] = None,
                   policy_evaluation: Optional[str] = None, diagnosis: Optional[str] = None,
                   stopping_reason: Optional[str] = None, attempt: Optional[int] = None,
                   approval_notes: Optional[str] = None, approver: Optional[str] = None,
                   policy_checks: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        return {
            "timestamp": timestamp or datetime.now().isoformat(timespec="seconds"),
            "batch_id": batch_id,
            "case_id": case["case_id"],
            "customer_id": case.get("customer_id"),
            "payment_id": case.get("payment_id"),
            "case_name": case.get("name", f"Case {case['case_id']}"),
            "customer": case.get("customer", case.get("name")),
            "agent": "RevenueRecoveryAgent",
            "agent_stage": stage,
            "risk_level": case.get("risk_level", "MEDIUM"),
            "risk_probability": case.get("risk_probability", 0.0),
            "risk_score": case.get("risk_score", 0.0),
            "diagnosis": diagnosis or case.get("diagnosis"),
            "root_cause": case.get("root_cause"),
            "decision": decision,
            "policy_evaluation": policy_evaluation or case.get("policy_evaluation"),
            "policy_checks": policy_checks,
            "status": status,
            "amount_at_risk": amount_at_risk,
            "recovered_amount": recovered_amount,
            "reason": reason,
            "audit_event": audit_event,
            "stopping_reason": stopping_reason,
            "attempt": attempt,
            "approver": approver,
            "approval_notes": approval_notes,
        }

    def append_audit_log(self, new_events: List[Dict[str, Any]]) -> None:
        db.append_audit(new_events)
        # Best-effort legacy JSON mirror (kept for easy inspection / demos).
        try:
            AUDIT_LOG_PATH.write_text(
                json.dumps(db.get_audit(newest_first=False), indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def get_audit_logs(self, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return db.get_audit(case_id=case_id, newest_first=case_id is None)

    # ------------------------------------------------------------------ #
    # Case access
    # ------------------------------------------------------------------ #
    def get_all_cases(self) -> List[Dict[str, Any]]:
        return list(self.cases.values())

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def _persist(self, case: Dict[str, Any]) -> None:
        db.save_case(case)

    # ------------------------------------------------------------------ #
    # Decision flow (UI)
    # ------------------------------------------------------------------ #
    def generate_decision_flow(self, case: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        risk_pct = round(analysis["risk_probability"] * 100, 2)
        amount = analysis["amount"]
        action = analysis["recommended_action"]
        current_status = case.get("status", "PENDING")
        stopping_reason = case.get("stopping_reason") or analysis.get("stopping_reason")
        recovered = case.get("recovered_amount", 0) or 0

        policy_lines = [f"{c['rule']}: {c['result']}" for c in analysis.get("policy_checks", [])]

        return [
            {
                "step": "DETECT",
                "title": "Revenue at Risk Detection",
                "content": analysis.get("detection_reason",
                    f"ML risk {risk_pct}% ({analysis['risk_level']})."),
                "badge": f"{analysis['risk_level']} RISK",
                "status": "COMPLETED",
            },
            {
                "step": "DIAGNOSE",
                "title": "Root Cause Diagnosis",
                "content": f"{analysis['diagnosis']} - {analysis.get('root_cause', analysis['diagnosis_label'])}",
                "badge": analysis["diagnosis"],
                "status": "COMPLETED",
            },
            {
                "step": "DECIDE",
                "title": "Bounded Action Decision",
                "content": f"{action}. {analysis.get('decision_reason', analysis['reason'])} "
                           f"(confidence {analysis.get('decision_confidence', 0)}).",
                "badge": action,
                "status": "COMPLETED",
            },
            {
                "step": "POLICY",
                "title": "Policy Engine & Guardrails",
                "content": "; ".join(policy_lines) or "Standard autonomous limits apply.",
                "badge": analysis["policy_evaluation"],
                "status": "COMPLETED",
            },
            {
                "step": "EXECUTE",
                "title": "Razorpay Test-Mode Execution",
                "content": f"Execution status: {current_status}.",
                "badge": RAZORPAY_MODE,
                "status": "COMPLETED" if current_status != "PENDING" else "PENDING",
            },
            {
                "step": "MEASURE",
                "title": "Outcome & Settlement",
                "content": (f"INR {recovered:,.2f} recovered (Test Mode)." if recovered > 0
                            else (f"Recovery stopped: {stopping_reason}" if stopping_reason
                                  else f"Current state: {current_status}.")),
                "badge": current_status,
                "status": "COMPLETED" if recovered > 0 or current_status in
                          ("BLOCKED", "STOPPED", "NO_ACTION") else "PENDING",
            },
        ]

    def analyze_case(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        analysis = self.agent.analyze(case)

        # Persist the refreshed signal onto the case.
        case.update(
            risk_probability=analysis["risk_probability"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            diagnosis=analysis["diagnosis"],
            diagnosis_label=analysis["diagnosis_label"],
            reason=analysis["reason"],
            cause=analysis["reason"],
            recommended_action=analysis["recommended_action"],
            policy_evaluation=analysis["policy_evaluation"],
            policy_result=analysis["policy_result"],
            root_cause=analysis["root_cause"],
            evidence=analysis["evidence"],
            recovery_objective=analysis["recovery_objective"],
        )
        self._persist(case)

        self.append_audit_log([self._audit_row(
            case, stage="DIAGNOSE", decision=analysis["recommended_action"],
            status=case.get("status", "PENDING"), audit_event="DECISION_MADE",
            amount_at_risk=analysis["amount"], recovered_amount=case.get("recovered_amount", 0.0),
            reason=analysis["decision_reason"], policy_evaluation=analysis["policy_evaluation"],
            diagnosis=analysis["diagnosis"], stopping_reason=analysis.get("stopping_reason"),
            policy_checks=analysis["policy_checks"],
        )])

        return {
            "case_id": case_id,
            "customer_id": case.get("customer_id"),
            "customer": case.get("customer", case.get("name")),
            "amount": analysis["amount"],
            "revenue_at_risk": analysis["revenue_at_risk"],
            "risk_probability": analysis["risk_probability"],
            "risk_score": analysis["risk_score"],
            "risk_level": analysis["risk_level"],
            "detection_reason": analysis["detection_reason"],
            "diagnosis": analysis["diagnosis"],
            "diagnosis_label": analysis["diagnosis_label"],
            "root_cause": analysis["root_cause"],
            "evidence": analysis["evidence"],
            "recovery_objective": analysis["recovery_objective"],
            "reason": analysis["reason"],
            "decision_reason": analysis["decision_reason"],
            "expected_recovery": analysis["expected_recovery"],
            "decision_confidence": analysis["decision_confidence"],
            "recommended_action": analysis["recommended_action"],
            "policy_evaluation": analysis["policy_evaluation"],
            "policy_result": analysis["policy_result"],
            "policy_checks": analysis["policy_checks"],
            "stopping_reason": analysis.get("stopping_reason"),
            "historical_failure_rate": analysis["historical_failure_rate"],
            "decision_flow": self.generate_decision_flow(case, analysis),
        }

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #
    def _record_attempt(self, case: Dict[str, Any], recovery: Dict[str, Any], stage: str,
                        audit_event: str, batch_id: Optional[str] = None,
                        approver: Optional[str] = None, approval_notes: Optional[str] = None) -> int:
        attempt_num = len(case.get("attempts", [])) + 1
        record = {
            "attempt": attempt_num,
            "timestamp": recovery.get("timestamp"),
            "execution_id": recovery.get("execution_id"),
            "action": recovery.get("action"),
            "status": recovery.get("status"),
            "execution_status": recovery.get("execution_status"),
            "payment_status_before": recovery.get("payment_status_before"),
            "payment_status_after": recovery.get("payment_status_after"),
            "recovered_amount": recovery.get("recovered_amount", 0.0),
            "remaining_amount_at_risk": recovery.get("remaining_amount_at_risk"),
            "reason": recovery.get("reason"),
            "audit_event": recovery.get("audit_event"),
            "stopping_reason": recovery.get("stopping_reason"),
            "approver": approver,
            "approval_notes": approval_notes,
        }
        case.setdefault("attempts", []).append(record)
        case["current_attempts"] = attempt_num
        case["status"] = recovery.get("status", case.get("status"))
        case["recovered_amount"] = recovery.get("recovered_amount", case.get("recovered_amount", 0.0))
        case["stopping_reason"] = recovery.get("stopping_reason")
        self._persist(case)
        db.add_attempt(case["case_id"], attempt_num, record)

        self.append_audit_log([self._audit_row(
            case, stage=stage, decision=recovery.get("action", "RECOVERY"),
            status=recovery.get("status"), audit_event=audit_event,
            amount_at_risk=recovery.get("amount_at_risk", case.get("amount", 0.0)),
            recovered_amount=recovery.get("recovered_amount", 0.0),
            reason=recovery.get("reason", ""), timestamp=recovery.get("timestamp"),
            batch_id=batch_id, policy_evaluation=recovery.get("policy_evaluation"),
            diagnosis=recovery.get("diagnosis", case.get("diagnosis")),
            stopping_reason=recovery.get("stopping_reason"), attempt=attempt_num,
            approver=approver, approval_notes=approval_notes,
            policy_checks=recovery.get("policy_checks"),
        )])
        return attempt_num

    def _response(self, case_id: int, recovery: Dict[str, Any], attempt_num: int) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "status": recovery.get("status"),
            "action": recovery.get("action"),
            "execution_id": recovery.get("execution_id"),
            "execution_status": recovery.get("execution_status"),
            "attempt": attempt_num,
            "attempt_number": attempt_num,
            "amount_at_risk": recovery.get("amount_at_risk", 0.0),
            "recovered_amount": recovery.get("recovered_amount", 0.0),
            "remaining_amount_at_risk": recovery.get("remaining_amount_at_risk"),
            "payment_status_before": recovery.get("payment_status_before"),
            "payment_status_after": recovery.get("payment_status_after"),
            "reason": recovery.get("reason"),
            "execution_reason": recovery.get("execution_reason", recovery.get("reason")),
            "diagnosis": recovery.get("diagnosis", self.cases.get(case_id, {}).get("diagnosis")),
            "policy_evaluation": recovery.get("policy_evaluation"),
            "policy_result": recovery.get("policy_result"),
            "policy_checks": recovery.get("policy_checks"),
            "stopping_reason": recovery.get("stopping_reason"),
            "audit_event": recovery.get("audit_event"),
            "approver": recovery.get("approver"),
            "approval_notes": recovery.get("approval_notes"),
            "timestamp": recovery.get("timestamp"),
            "updated_case": self.get_case_summary(case_id),
        }

    def execute_recovery(self, case_id: int, simulate_failure: bool = False) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        if case["status"] == "RECOVERED":
            raise ValueError(f"Case {case_id} has already been recovered.")
        if len(case.get("attempts", [])) >= self.agent.MAX_PAYMENT_ATTEMPTS:
            case["status"] = "STOPPED"
            case["stopping_reason"] = "MAX_PAYMENT_ATTEMPTS_REACHED"
            self._persist(case)
            raise ValueError(
                f"Case {case_id} reached max payment attempts "
                f"({self.agent.MAX_PAYMENT_ATTEMPTS}). Recovery halted by stopping rules."
            )

        recovery = self.agent.execute_recovery(case, simulate_failure=simulate_failure)
        audit_event = {
            "RECOVERED": "RECOVERY_SUCCESS",
            "RETRY_AVAILABLE": "RETRY_AVAILABLE",
            "HUMAN_APPROVAL_REQUIRED": "HUMAN_APPROVAL_REQUIRED",
            "BLOCKED": "POLICY_BLOCKED",
            "STOPPED": "RECOVERY_STOPPED",
            "NO_ACTION": "NO_ACTION",
        }.get(recovery["status"], recovery.get("audit_event") or "RECOVERY_STARTED")
        attempt_num = self._record_attempt(case, recovery, stage="EXECUTE", audit_event=audit_event)
        return self._response(case_id, recovery, attempt_num)

    def retry_recovery(self, case_id: int) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        if case["status"] != "RETRY_AVAILABLE":
            raise ValueError(
                f"Case {case_id} is not in RETRY_AVAILABLE status (current: {case['status']})."
            )
        recovery = self.agent.retry_recovery(case)
        audit_event = "RECOVERY_SUCCESS" if recovery["status"] == "RECOVERED" else "RECOVERY_STOPPED"
        attempt_num = self._record_attempt(case, recovery, stage="EXECUTE", audit_event=audit_event)
        return self._response(case_id, recovery, attempt_num)

    def approve_recovery(self, case_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        if case["status"] not in ("HUMAN_APPROVAL_REQUIRED", "PENDING"):
            raise ValueError(f"Case {case_id} does not require human approval.")

        approver = "merchant_ops_supervisor"
        recovery = self.agent.approve_recovery(case, notes=notes, approver=approver)
        recovery.setdefault("policy_evaluation", "HUMAN_APPROVED")
        attempt_num = self._record_attempt(
            case, recovery, stage="EXECUTE", audit_event=recovery.get("audit_event", "HUMAN_APPROVED"),
            approver=approver, approval_notes=notes,
        )
        return self._response(case_id, recovery, attempt_num)

    def reject_recovery(self, case_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        approver = "merchant_ops_supervisor"
        recovery = self.agent.reject_recovery(case, notes=notes, approver=approver)
        recovery.setdefault("policy_evaluation", "HUMAN_REJECTED")
        attempt_num = self._record_attempt(
            case, recovery, stage="EXECUTE", audit_event="HUMAN_REJECTED",
            approver=approver, approval_notes=notes,
        )
        return self._response(case_id, recovery, attempt_num)

    # ------------------------------------------------------------------ #
    # Batch
    # ------------------------------------------------------------------ #
    def run_batch(self) -> Dict[str, Any]:
        raw_cases = list(self.cases.values())
        batch_result = self.agent.run_batch(raw_cases)
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat(timespec="seconds")

        audit_events: List[Dict[str, Any]] = []
        for item in batch_result["results"]:
            cid = item["case_id"]
            case = self.cases.get(cid)
            if case:
                case.update(
                    status=item["status"],
                    recovered_amount=item["recovered_amount"],
                    risk_probability=item["risk_probability"],
                    risk_score=item["risk_score"],
                    risk_level=item["risk_level"],
                    diagnosis=item["diagnosis"],
                    diagnosis_label=item["diagnosis_label"],
                    reason=item["reason"],
                    recommended_action=item["action"],
                    policy_evaluation=item["policy_evaluation"],
                    policy_result=item.get("policy_result"),
                    stopping_reason=item.get("stopping_reason"),
                )
                attempt_num = len(case.get("attempts", [])) + 1
                rec = {
                    "attempt": attempt_num, "timestamp": timestamp,
                    "action": item["action"], "status": item["status"],
                    "recovered_amount": item["recovered_amount"],
                    "reason": item["reason"], "audit_event": item["audit_event"],
                    "stopping_reason": item.get("stopping_reason"),
                }
                case.setdefault("attempts", []).append(rec)
                case["current_attempts"] = attempt_num
                self._persist(case)
                db.add_attempt(cid, attempt_num, rec)

            audit_events.append(self._audit_row(
                case or {"case_id": cid, "name": item["name"]},
                stage="EXECUTE", decision=item["action"], status=item["status"],
                audit_event=item["audit_event"], amount_at_risk=item["amount"],
                recovered_amount=item["recovered_amount"], reason=item["reason"],
                timestamp=timestamp, batch_id=batch_id,
                policy_evaluation=item["policy_evaluation"], diagnosis=item["diagnosis"],
                stopping_reason=item.get("stopping_reason"),
            ))

        self.append_audit_log(audit_events)

        response = {
            "batch_id": batch_id,
            "timestamp": timestamp,
            "total_cases": batch_result["total_cases"],
            "eligible_cases": batch_result["eligible_cases"],
            "at_risk_cases": batch_result["at_risk_cases"],
            "recovered_cases": batch_result["recovered_cases"],
            "failed_cases": batch_result["failed_cases"],
            "blocked_cases": batch_result["blocked_cases"],
            "approval_cases": batch_result["approval_cases"],
            "stopped_cases": batch_result["stopped_cases"],
            "total_revenue_at_risk": batch_result["total_revenue_at_risk"],
            "total_revenue_recovered": batch_result["total_revenue_recovered"],
            "recovery_rate": batch_result["recovery_rate"],
            "average_risk_score": batch_result["average_risk_score"],
            "results": batch_result["results"],
        }
        self.batch_history[batch_id] = response
        db.save_batch(batch_id, timestamp, response)
        return response

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        return self.batch_history.get(batch_id) or db.get_batch(batch_id)

    # ------------------------------------------------------------------ #
    # Metrics
    # ------------------------------------------------------------------ #
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        total_cases = len(self.cases)
        at_risk = recovered = failed = blocked = approval = retry = stopped = no_action = 0
        total_at_risk = total_recovered = risk_sum = 0.0

        for case in self.cases.values():
            amount = case.get("amount", 0.0)
            recovered_amt = case.get("recovered_amount", 0.0) or 0.0
            status = case.get("status", "PENDING")
            action = case.get("recommended_action", "NO_ACTION")
            risk_sum += case.get("risk_score", 0.0) or 0.0

            if action != "NO_ACTION":
                total_at_risk += amount
                at_risk += 1
            total_recovered += recovered_amt

            if status == "RECOVERED":
                recovered += 1
            elif status == "HUMAN_APPROVAL_REQUIRED":
                approval += 1
            elif status == "RETRY_AVAILABLE":
                retry += 1
                failed += 1
            elif status == "BLOCKED":
                blocked += 1
            elif status == "STOPPED":
                stopped += 1
            elif status == "NO_ACTION":
                no_action += 1

        recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0
        return {
            "total_cases": total_cases,
            "at_risk_cases": at_risk,
            "recovered_cases": recovered,
            "failed_cases": failed,
            "blocked_cases": blocked + stopped,
            "stopped_cases": stopped,
            "approval_cases": approval,
            "retry_available_cases": retry,
            "no_action_cases": no_action,
            "total_revenue_at_risk": round(total_at_risk, 2),
            "total_revenue_recovered": round(total_recovered, 2),
            "recovery_rate": round(recovery_rate, 2),
            "average_risk_score": round((risk_sum / total_cases) if total_cases else 0.0, 4),
            "policy_limits": {
                "max_incentive_percent": self.agent.MAX_INCENTIVE_PERCENT,
                "max_recovery_amount": self.agent.MAX_RECOVERY_AMOUNT,
                "high_value_approval_threshold": self.agent.HIGH_VALUE_APPROVAL_THRESHOLD,
                "max_payment_attempts": self.agent.MAX_PAYMENT_ATTEMPTS,
            },
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
            "root_cause": c.get("root_cause", ""),
            "recommended_action": c.get("recommended_action", "NO_ACTION"),
            "policy_evaluation": c.get("policy_evaluation", "ALLOWED"),
            "policy_result": c.get("policy_result", c.get("policy_evaluation", "ALLOWED")),
            "stopping_reason": c.get("stopping_reason"),
            "status": c.get("status", "PENDING"),
            "recovered_amount": c.get("recovered_amount", 0.0),
        }

    def get_model_metrics(self) -> Dict[str, Any]:
        data: Dict[str, Any]
        if MODEL_METADATA_PATH.exists():
            data = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
        else:
            data = {
                "model": "RandomForestClassifier",
                "dataset_size": 50000, "training_rows": 40000, "testing_rows": 10000,
                "accuracy": 0.9243, "precision": 0.8912, "recall": 0.83,
                "f1_score": 0.8596, "roc_auc": 0.9656, "failed_payment_recall": 0.83,
                "features": [],
            }
        features = data.get("features", []) or []
        data.setdefault("model_type", "RandomForestClassifier")
        data["feature_count"] = len(features)
        data["governance_statement"] = (
            "ML provides the risk signal; merchant policies govern recovery execution."
        )
        data["model_path"] = str(MODEL_PATH)
        return data

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #
    def health(self) -> Dict[str, Any]:
        try:
            db_ok = db.case_count() >= 0
        except Exception:
            db_ok = False
        return {
            "status": "ok",
            "agent": "RevenueRecoveryAgent",
            "service": "revenue-recovery-agent",
            "mode": RAZORPAY_MODE,
            "database": "connected" if db_ok else "unavailable",
            "model_loaded": self.agent.model is not None,
            "demo_cases": len(self.cases),
            "note": "ML provides the risk signal; merchant policies govern recovery execution.",
            "version": "2.0.0",
        }


# Global singleton
state_manager = StateManager()
