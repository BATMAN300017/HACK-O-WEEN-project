from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class GraphNode(BaseModel):
    id: str
    label: str
    type: str # CUSTOMER, ACCOUNT, TRANSACTION, MERCHANT, BENEFICIARY, DEVICE, IP
    risk_level: Optional[str] = "LOW"
    properties: Dict[str, Any]

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str # OWNS, TRANSFERS_TO, USES_DEVICE, PAYS_MERCHANT, SHARES_BENEFICIARY, SHARES_IP
    amount: Optional[float] = None
    currency: Optional[str] = "USD"
    timestamp: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class GraphExpandRequest(BaseModel):
    node_id: str
    max_hops: int = 1
    entity_types: Optional[List[str]] = None

class PathFindRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    max_depth: int = 4

class SuspiciousPathResult(BaseModel):
    pattern_name: str
    path_nodes: List[str]
    path_edges: List[str]
    total_amount: float
    time_window_minutes: float
    explanation: str
    alternative_explanations: str
