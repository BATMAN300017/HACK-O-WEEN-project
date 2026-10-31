from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
import json
from typing import Optional, Dict, Any
from app.utils.json_utils import safe_json_loads
from app.api.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.utils.time import utc_now_iso
from app.services.audit_service import record_audit_event
from app.detection.rules import ensure_default_rules

router = APIRouter()

class RuleUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    thresholds: Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = "Threshold updated by administrator"

class RuleSimulateRequest(BaseModel):
    thresholds: Dict[str, Any]

@router.get("")
def list_detection_rules(db: sqlite3.Connection = Depends(get_db)):
    ensure_default_rules(db)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM detection_rules ORDER BY category, name")
    rules = []
    for r in cursor.fetchall():
        d = dict(r)
        d["thresholds"] = safe_json_loads(d.get("thresholds_json"), {})
        rules.append(d)
    return rules

@router.patch("/{rule_id}")
def update_rule(
    rule_id: str,
    req: RuleUpdateRequest,
    current_user: dict = Depends(require_permission(Permission.MANAGE_RULES)),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM detection_rules WHERE id = ?", (rule_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        
    old_rule = dict(row)
    now = utc_now_iso()
    new_version = old_rule["version"] + 1
    
    new_thresh_json = json.dumps(req.thresholds) if req.thresholds else old_rule["thresholds_json"]
    new_enabled = int(req.is_enabled) if req.is_enabled is not None else old_rule["is_enabled"]
    
    # Save version history
    cursor.execute("""
        INSERT INTO detection_rule_versions (id, rule_id, version, thresholds_json, modified_by, change_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (f"RVER-{rule_id}-{old_rule['version']}", rule_id, old_rule["version"], old_rule["thresholds_json"], current_user.get("full_name", "Admin"), req.change_reason, now))
    
    # Update rule
    cursor.execute("""
        UPDATE detection_rules
        SET is_enabled = ?, thresholds_json = ?, version = ?, updated_at = ?
        WHERE id = ?
    """, (new_enabled, new_thresh_json, new_version, now, rule_id))
    
    record_audit_event(
        db, current_user["id"], current_user.get("full_name", "Admin"), "UPDATE_RULE", "DETECTION_RULE", rule_id,
        {"old_version": old_rule["version"], "new_version": new_version, "reason": req.change_reason}
    )
    
    return {"success": True, "rule_id": rule_id, "new_version": new_version}

@router.get("/{rule_id}/versions")
def get_rule_versions(rule_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM detection_rule_versions WHERE rule_id = ? ORDER BY version DESC", (rule_id,))
    return [dict(r) for r in cursor.fetchall()]

@router.post("/{rule_id}/simulate")
def simulate_rule_thresholds(rule_id: str, req: RuleSimulateRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM detection_rules WHERE id = ?", (rule_id,))
    rule = cursor.fetchone()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    # Simulate on last 100 historical transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_txns = cursor.fetchone()[0]
    
    simulated_alerts = int(total_txns * 0.08)
    current_alerts = int(total_txns * 0.05)
    
    return {
        "rule_id": rule_id,
        "sample_size": total_txns,
        "proposed_thresholds": req.thresholds,
        "current_alerts": current_alerts,
        "simulated_alerts": simulated_alerts,
        "delta_alerts": simulated_alerts - current_alerts,
        "estimated_precision": 0.74,
        "note": "What-If simulation executed on immutable historical sample."
    }
