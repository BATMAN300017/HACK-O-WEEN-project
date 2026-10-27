from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class KPISummary(BaseModel):
    transactions_processed: int
    transactions_per_minute: float
    alerts_generated: int
    open_investigations: int
    high_priority_cases: int
    avg_investigation_age_hours: float
    verified_false_positive_rate: float
    confirmed_fraud_count: int
    investigation_completion_rate: float

class AnalyticsTrends(BaseModel):
    volume_by_hour: List[Dict[str, Any]]
    alerts_by_hour: List[Dict[str, Any]]
    risk_score_distribution: List[Dict[str, Any]]
    alerts_by_source: List[Dict[str, Any]]
    case_outcomes: List[Dict[str, Any]]
    investigation_status_breakdown: List[Dict[str, Any]]

class RulePerformanceItem(BaseModel):
    rule_code: str
    rule_name: str
    trigger_count: int
    confirmed_fraud_count: int
    false_positive_count: int
    precision: Optional[float] = None
    is_sufficient_sample: bool
