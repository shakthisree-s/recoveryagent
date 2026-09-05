from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class CaseItem(BaseModel):
    case_id: int
    customer_id: Optional[str] = None
    payment_id: Optional[str] = None
    name: str
    customer: str
    amount: float
    total_amount: float
    payment_method: str
    payment_status: str
    device_type: str
    home_country: str
    shipment_fee: float
    promo_amount: float
    total_spend: float
    total_transactions: int
    successful_payments: int
    failed_payments: int
    average_transaction_amount: float
    transaction_day: int
    transaction_hour: int
    failure_rate: float
    requested_incentive_percent: Optional[float] = 0.0
    current_attempts: Optional[int] = 0
    created_at: Optional[str] = None
    risk_probability: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    diagnosis: Optional[str] = None
    diagnosis_label: Optional[str] = None
    cause: Optional[str] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None
    policy_evaluation: Optional[str] = None
    stopping_reason: Optional[str] = None
    status: str
    recovered_amount: float = 0.0
    attempts: List[Dict[str, Any]] = []


class CaseSummary(BaseModel):
    case_id: int
    customer_id: Optional[str] = None
    payment_id: Optional[str] = None
    customer: str
    amount: float
    payment_status: str
    risk_probability: float
    risk_score: float
    risk_level: str
    diagnosis: str
    diagnosis_label: str
    cause: str
    recommended_action: str
    policy_evaluation: str
    stopping_reason: Optional[str] = None
    status: str
    recovered_amount: float


class DecisionFlowStep(BaseModel):
    step: str
    title: str
    content: str
    badge: Optional[str] = None
    status: Optional[str] = None


class CaseDetailResponse(BaseModel):
    case: CaseItem
    analysis: Dict[str, Any]
    decision_flow: List[DecisionFlowStep]
    audit_history: List[Dict[str, Any]]


class AnalyzeResponse(BaseModel):
    case_id: int
    customer_id: Optional[str] = None
    customer: str
    amount: float
    risk_probability: float
    risk_score: float
    risk_level: str
    diagnosis: str
    diagnosis_label: str
    reason: str
    recommended_action: str
    policy_evaluation: str
    stopping_reason: Optional[str] = None
    historical_failure_rate: float
    decision_flow: List[DecisionFlowStep]


class RecoveryRequest(BaseModel):
    simulate_failure: bool = False


class RecoveryResponse(BaseModel):
    case_id: int
    status: str
    action: str
    amount_at_risk: float
    recovered_amount: float
    reason: str
    diagnosis: Optional[str] = None
    policy_evaluation: Optional[str] = None
    stopping_reason: Optional[str] = None
    audit_event: Optional[str] = None
    attempt: int
    timestamp: str
    updated_case: CaseSummary


class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


class BatchResultItem(BaseModel):
    case_id: int
    customer_id: Optional[str] = None
    payment_id: Optional[str] = None
    name: str
    amount: float
    risk_probability: float
    risk_score: float
    risk_level: str
    diagnosis: str
    diagnosis_label: str
    reason: str
    action: str
    policy_evaluation: str
    status: str
    recovered_amount: float
    audit_event: Optional[str] = None
    stopping_reason: Optional[str] = None


class BatchRunResponse(BaseModel):
    batch_id: str
    timestamp: str
    total_cases: int
    at_risk_cases: int
    recovered_cases: int
    failed_cases: int
    blocked_cases: int
    approval_cases: int
    total_revenue_at_risk: float
    total_revenue_recovered: float
    recovery_rate: float
    results: List[BatchResultItem]


class DashboardMetricsResponse(BaseModel):
    total_cases: int
    at_risk_cases: int
    recovered_cases: int
    failed_cases: int
    blocked_cases: int
    approval_cases: int
    retry_available_cases: int
    total_revenue_at_risk: float
    total_revenue_recovered: float
    recovery_rate: float
    policy_limits: Dict[str, Any]


class ModelMetricsResponse(BaseModel):
    model: str
    dataset_size: int
    training_rows: int
    testing_rows: int
    accuracy: float
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: float
    failed_payment_recall: float
    features: List[str]


class AuditEvent(BaseModel):
    timestamp: str
    batch_id: Optional[str] = None
    case_id: int
    customer_id: Optional[str] = None
    payment_id: Optional[str] = None
    case_name: str
    agent: str = "RevenueRecoveryAgent"
    agent_stage: Optional[str] = "EXECUTE"
    risk_level: str
    risk_probability: float
    risk_score: Optional[float] = None
    diagnosis: Optional[str] = None
    decision: str
    policy_evaluation: Optional[str] = None
    status: str
    amount_at_risk: float
    recovered_amount: float
    reason: str
    audit_event: Optional[str] = None
    stopping_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    agent: str
    mode: str
    model_loaded: bool
    version: str = "1.0.0"
