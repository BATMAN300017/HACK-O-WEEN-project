from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TransactionBase(BaseModel):
    event_id: str
    source_account_id: str
    destination_account_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    customer_id: str
    amount: float = Field(..., gt=0.0)
    currency: str = "USD"
    transaction_type: str = "TRANSFER" # TRANSFER, CARD_PAYMENT, ATM_WITHDRAWAL, MERCHANT_PAYMENT, REFUND
    payment_channel: str = "ONLINE" # ONLINE, MOBILE_APP, ATM, POS, WIRE
    merchant_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: str = "COMPLETED"
    scenario_id: Optional[str] = None

class TransactionCreate(TransactionBase):
    is_ground_truth_fraud: Optional[int] = 0
    ground_truth_label: Optional[str] = None

class TransactionResponse(TransactionBase):
    id: str
    risk_score: float = 0.0
    risk_band: str = "ROUTINE"
    created_at: str

class TransactionRiskBreakdown(BaseModel):
    transaction_id: str
    final_risk_score: float
    risk_band: str
    ensemble_weights: Dict[str, float]
    component_scores: Dict[str, float]
    triggered_rules: List[Dict[str, Any]]
    behavioral_anomalies: List[Dict[str, Any]]
    graph_signals: List[Dict[str, Any]]
    supervised_prediction: Optional[Dict[str, Any]] = None
    narrative_explanation: str
