from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class InvestigationNoteCreate(BaseModel):
    content: str = Field(..., min_length=2)
    is_confidential: bool = False

class InvestigationNoteResponse(BaseModel):
    id: str
    investigation_id: str
    author_id: str
    author_name: Optional[str] = None
    content: str
    is_confidential: bool
    created_at: str

class InvestigationTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None

class InvestigationTaskUpdate(BaseModel):
    is_completed: bool
    evidence_id: Optional[str] = None

class InvestigationTaskResponse(BaseModel):
    id: str
    investigation_id: str
    title: str
    description: Optional[str] = None
    is_completed: bool
    completed_by: Optional[str] = None
    completed_at: Optional[str] = None
    evidence_id: Optional[str] = None
    created_at: str

class DispositionSubmitRequest(BaseModel):
    disposition: str # CONFIRMED_FRAUD, SUSPICIOUS_UNCONFIRMED, LEGITIMATE_ACTIVITY, INCONCLUSIVE, DUPLICATE_CASE, ESCALATED
    rationale: str = Field(..., min_length=10, description="Detailed auditable justification for the case disposition")
    requires_peer_review: bool = False

class PeerReviewRequest(BaseModel):
    action: str # APPROVED, REJECTED
    notes: str = Field(..., min_length=5)

class InvestigationCreate(BaseModel):
    title: str
    summary: str
    priority: str = "HIGH"
    alert_ids: Optional[List[str]] = []
    account_ids: Optional[List[str]] = []

class InvestigationUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    priority: Optional[str] = None
    assigned_investigator_id: Optional[str] = None
    peer_reviewer_id: Optional[str] = None

class InvestigationResponse(BaseModel):
    id: str
    case_number: str
    title: str
    summary: str
    priority: str
    status: str
    assigned_investigator_id: Optional[str] = None
    assigned_investigator_name: Optional[str] = None
    peer_reviewer_id: Optional[str] = None
    disposition: Optional[str] = None
    disposition_rationale: Optional[str] = None
    disposition_submitted_at: Optional[str] = None
    peer_review_status: Optional[str] = None
    peer_review_notes: Optional[str] = None
    peer_reviewed_at: Optional[str] = None
    due_date: Optional[str] = None
    evidence_completeness_score: float = 0.0
    model_version: Optional[str] = None
    rule_version: Optional[str] = None
    created_at: str
    updated_at: str
    alerts_count: int = 0
    evidence_count: int = 0
    tasks_count: int = 0
    notes_count: int = 0
