from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AlertFindingSchema(BaseModel):
    id: str
    source: str # RULE, ANOMALY, GRAPH, SUPERVISED
    code: str
    description: str
    score_contribution: float
    feature_values: Optional[Dict[str, Any]] = None
    version: str

class AlertResponse(BaseModel):
    id: str
    alert_ref: str
    transaction_id: str
    account_id: str
    customer_id: str
    severity: str # LOW, MEDIUM, HIGH, CRITICAL
    status: str # NEW, TRIAGED, IN_REVIEW, DISMISSED, CONVERTED_TO_INVESTIGATION
    risk_score: float
    title: str
    summary: str
    assigned_to: Optional[str] = None
    dismissal_reason: Optional[str] = None
    created_at: str
    updated_at: str
    findings: Optional[List[AlertFindingSchema]] = None

class AlertAssignRequest(BaseModel):
    user_id: str

class AlertTriageRequest(BaseModel):
    severity: str
    notes: Optional[str] = None

class AlertDismissRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Auditable justification for alert dismissal")

class AlertInvestigateRequest(BaseModel):
    priority: Optional[str] = "HIGH"
    initial_notes: Optional[str] = None
