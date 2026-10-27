from typing import Dict, Any, Tuple, Optional

def evaluate_disposition_label(disposition: str, peer_review_status: Optional[str] = None) -> Tuple[bool, Optional[int], Optional[str]]:
    disp = disposition.upper()
    
    # Check if peer review was required and approved
    if peer_review_status == "REQUESTED":
        return False, None, "Pending mandatory senior peer review"
    elif peer_review_status == "REJECTED":
        return False, None, "Peer review rejected the proposed disposition"
        
    if disp == "CONFIRMED_FRAUD":
        return True, 1, None # Positive training label
    elif disp in ("LEGITIMATE_ACTIVITY", "FALSE_POSITIVE"):
        return True, 0, None # Negative training label
    elif disp == "SUSPICIOUS_UNCONFIRMED":
        return False, None, "Suspicious but unconfirmed cases cannot be converted into definitive training labels"
    elif disp == "INCONCLUSIVE":
        return False, None, "Inconclusive outcomes lack sufficient evidentiary certainty for binary training"
    elif disp == "DUPLICATE_CASE":
        return False, None, "Duplicate cases are excluded to prevent target leakage and double-counting"
    elif disp == "ESCALATED":
        return False, None, "Escalated cases remain open and unresolved"
        
    return False, None, f"Unknown disposition: {disposition}"
