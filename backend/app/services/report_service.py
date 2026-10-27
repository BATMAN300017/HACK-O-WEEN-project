import sqlite3
import json
from typing import Dict, Any
from app.utils.time import utc_now_iso
from app.repositories.investigation_repository import get_investigation_by_id
from app.repositories.evidence_repository import list_evidence_for_case

def generate_case_report(conn: sqlite3.Connection, investigation_id: str) -> Dict[str, Any]:
    inv = get_investigation_by_id(conn, investigation_id)
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")
        
    evidence_items = list_evidence_for_case(conn, inv["id"])
    
    # Associated transactions
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*
        FROM investigation_alerts ia
        JOIN alerts a ON ia.alert_id = a.id
        JOIN transactions t ON a.transaction_id = t.id
        WHERE ia.investigation_id = ?
    """, (inv["id"],))
    txns = [dict(r) for r in cursor.fetchall()]
    
    # Timeline
    cursor.execute("SELECT * FROM investigation_events WHERE investigation_id = ? ORDER BY created_at ASC", (inv["id"],))
    events = [dict(r) for r in cursor.fetchall()]
    
    methodology = (
        "METHODOLOGY & LIMITATIONS:\n"
        "This case report was compiled by SentinelFlow AI using multi-detector risk telemetry, "
        "including configurable rule evaluations, account-specific rolling median/MAD anomaly scoring, "
        "and topological graph signal analysis. In accordance with platform governance, all conclusions "
        "and final case dispositions represent human investigator determinations supported by verified evidentiary items. "
        "Synthetic demo data has been utilized for all events."
    )
    
    return {
        "case_number": inv["case_number"],
        "title": inv["title"],
        "summary": inv["summary"],
        "priority": inv["priority"],
        "status": inv["status"],
        "disposition": inv.get("disposition"),
        "disposition_rationale": inv.get("disposition_rationale"),
        "investigator_name": inv.get("assigned_investigator_name") or "Primary Investigator",
        "reviewer_name": inv.get("reviewer_name"),
        "evidence_completeness_score": inv.get("evidence_completeness_score", 0.0),
        "evidence_items": evidence_items,
        "associated_transactions": txns,
        "timeline_events": events,
        "methodology_and_limitations": methodology,
        "is_synthetic_demo": True,
        "generated_at": utc_now_iso()
    }
