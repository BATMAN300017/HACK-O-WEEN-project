from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class EvidenceCreate(BaseModel):
    evidence_type: str # TRANSACTION, BEHAVIORAL_ANOMALY, RULE_MATCH, RELATIONSHIP, FUND_FLOW, ACCOUNT_HISTORY, TIMELINE_EVENT, NOTE, CONTRADICTORY
    source_record_id: Optional[str] = None
    description: str
    observed_facts: Dict[str, Any]
    associated_entities: Optional[List[Dict[str, str]]] = []
    associated_transactions: Optional[List[str]] = []
    verification_status: str = "SUPPORTING" # SUPPORTING, CONTRADICTORY, UNVERIFIED, NOT_RELEVANT
    collector: str = "ANALYST" # AGENT, ANALYST

class EvidenceUpdate(BaseModel):
    verification_status: Optional[str] = None
    description: Optional[str] = None

class EvidenceResponse(BaseModel):
    id: str
    investigation_id: str
    evidence_type: str
    source_record_id: Optional[str] = None
    description: str
    observed_facts: Dict[str, Any]
    associated_entities: List[Dict[str, str]]
    associated_transactions: List[str]
    verification_status: str
    collector: str
    integrity_hash: Optional[str] = None
    created_at: str

class TimelineEventResponse(BaseModel):
    id: str
    investigation_id: str
    event_type: str
    description: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
