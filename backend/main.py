import os
import sys
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Ensure workspace root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.schemas import (
    HealthResponse,
    CaseSummary,
    CaseDetailResponse,
    AnalyzeResponse,
    RecoveryRequest,
    RecoveryResponse,
    ApprovalRequest,
    BatchRunResponse,
    DashboardMetricsResponse,
    ModelMetricsResponse,
    AuditEvent
)
from backend.state import state_manager

app = FastAPI(
    title="Revenue Recovery Agent API",
    description="Razorpay AI Buildathon Track 03 - AI Revenue Recovery Platform (DETECT -> DIAGNOSE -> DECIDE -> EXECUTE)",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/api/health", methods=["GET", "HEAD"], response_model=HealthResponse)
def get_health():
    """Accurate health check: service, database, model, seeded demo cases."""
    return state_manager.health()


@app.get("/api/cases", response_model=List[CaseSummary])
def get_all_cases():
    """Return all available demo cases with risk scores, diagnoses, actions, and current statuses."""
    cases = state_manager.get_all_cases()
    summaries = []
    for c in cases:
        summaries.append(state_manager.get_case_summary(c["case_id"]))
    return summaries


@app.get("/api/cases/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(case_id: int):
    """Return detailed information for one case including AI decision flow."""
    case = state_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    analysis = state_manager.agent.analyze(case)
    decision_flow = state_manager.generate_decision_flow(case, analysis)
    audit_history = state_manager.get_audit_logs(case_id=case_id)

    return {
        "case": case,
        "analysis": analysis,
        "decision_flow": decision_flow,
        "audit_history": audit_history
    }


@app.post("/api/cases/{case_id}/analyze", response_model=AnalyzeResponse)
def analyze_case(case_id: int):
    """Run the existing agent's analysis (DETECT -> DIAGNOSE -> DECIDE -> POLICY) on a case."""
    try:
        return state_manager.analyze_case(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/cases/{case_id}/recover", response_model=RecoveryResponse)
def recover_case(case_id: int, request: Optional[RecoveryRequest] = None):
    """Execute recovery using the existing agent and policy engine in test mode."""
    simulate_failure = request.simulate_failure if request else False
    try:
        return state_manager.execute_recovery(case_id, simulate_failure=simulate_failure)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")


@app.post("/api/cases/{case_id}/retry", response_model=RecoveryResponse)
def retry_case(case_id: int):
    """Retry a failed recovery attempt respecting stopping rules."""
    try:
        return state_manager.retry_recovery(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@app.post("/api/cases/{case_id}/approve", response_model=RecoveryResponse)
def approve_case(case_id: int, request: Optional[ApprovalRequest] = None):
    """Approve a high-value human-approval case. Optional approver notes are
    recorded on the attempt and in the audit trail."""
    notes = request.notes if request else None
    try:
        return state_manager.approve_recovery(case_id, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/api/cases/{case_id}/reject", response_model=RecoveryResponse)
def reject_case(case_id: int, request: Optional[ApprovalRequest] = None):
    """Reject a high-value human-approval case. Rejection stops recovery."""
    notes = request.notes if request else None
    try:
        return state_manager.reject_recovery(case_id, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")


@app.post("/api/batch/run", response_model=BatchRunResponse)
def run_batch():
    """Run the existing batch recovery engine on all cases."""
    try:
        return state_manager.run_batch()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch execution failed: {str(e)}")


@app.get("/api/batch/{batch_id}", response_model=BatchRunResponse)
def get_batch_result(batch_id: str):
    """Fetch previously executed batch run metrics and case outcomes."""
    res = state_manager.get_batch(batch_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Batch run {batch_id} not found")
    return res


@app.get("/api/metrics", response_model=DashboardMetricsResponse)
def get_metrics():
    """Return live dynamically calculated dashboard metrics."""
    return state_manager.get_dashboard_metrics()


@app.get("/api/model/metrics", response_model=ModelMetricsResponse)
def get_model_metrics():
    """Read and return trained ML model metrics from model_metadata.json."""
    return state_manager.get_model_metrics()


@app.get("/api/audit", response_model=List[AuditEvent])
def get_audit_trail(
    status: Optional[str] = Query(None, description="Filter by status/event"),
    case_id: Optional[int] = Query(None, description="Filter by case ID")
):
    """Return compliance audit events from audit_log.json."""
    logs = state_manager.get_audit_logs(case_id=case_id)
    if status and status != "ALL":
        logs = [
            l for l in logs
            if l.get("status") == status or l.get("audit_event") == status or status.lower() in (l.get("audit_event") or "").lower()
        ]
    return logs


@app.get("/api/audit/{case_id}", response_model=List[AuditEvent])
def get_case_audit(case_id: int):
    """Return audit history for a single case."""
    return state_manager.get_audit_logs(case_id=case_id)


@app.post("/api/reset")
def reset_state():
    """Reset demo cases to initial state."""
    state_manager.reset_state()
    return {"status": "ok", "message": "Demo state reset successfully."}
