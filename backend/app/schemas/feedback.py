from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class FeedbackSubmitRequest(BaseModel):
    investigation_id: str
    disposition: str
    rationale: str = Field(..., min_length=10)

class FeedbackSummaryResponse(BaseModel):
    total_feedback_count: int
    confirmed_fraud_count: int
    false_positive_count: int
    inconclusive_count: int
    suspicious_unconfirmed_count: int
    eligible_for_training_count: int
    positive_labels: int
    negative_labels: int
    last_feedback_at: Optional[str] = None

class LearningStatusResponse(BaseModel):
    current_active_model: str
    active_model_metrics: Dict[str, Any]
    candidate_model_available: bool
    candidate_model_metrics: Optional[Dict[str, Any]] = None
    training_data_readiness: str # INSUFFICIENT, READY, CRITICAL_MASS
    labeled_samples_count: int
    minimum_required_samples: int
    drift_warning: bool
    last_evaluation_status: Optional[str] = None
    last_evaluation_reason: Optional[str] = None
