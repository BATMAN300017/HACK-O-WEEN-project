from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class EntityProfile(BaseModel):
    id: str
    entity_type: str # CUSTOMER, ACCOUNT, MERCHANT, DEVICE, IP
    label: str
    details: Dict[str, Any]
    risk_signals: List[Dict[str, Any]]
    associated_accounts: List[str]
    alert_count: int
    investigation_count: int
    created_at: str
