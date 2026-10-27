from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class CaseReportResponse(BaseModel):
    case_number: str
    title: str
    summary: str
    priority: str
    status: str
    disposition: Optional[str] = None
    disposition_rationale: Optional[str] = None
    investigator_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    evidence_completeness_score: float
    evidence_items: List[Dict[str, Any]]
    associated_transactions: List[Dict[str, Any]]
    timeline_events: List[Dict[str, Any]]
    methodology_and_limitations: str
    is_synthetic_demo: bool = True
    generated_at: str
