import sqlite3
from typing import Dict, Any, Optional, List
from app.utils.time import utc_now_iso
from app.utils.ids import generate_id
from app.services.audit_service import record_audit_event
from app.learning.label_policy import evaluate_disposition_label
from app.repositories.feedback_repository import record_feedback

def add_investigation_note(
    conn: sqlite3.Connection,
    investigation_id: str,
    author_id: str,
    content: str,
    is_confidential: bool = False
) -> Dict[str, Any]:
    note_id = generate_id("NOT")
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO investigation_notes (id, investigation_id, author_id, content, is_confidential, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (note_id, investigation_id, author_id, content, 1 if is_confidential else 0, now))
    
    cursor.execute("UPDATE investigations SET updated_at = ? WHERE id = ?", (now, investigation_id))
    return {"id": note_id, "investigation_id": investigation_id, "content": content, "created_at": now}

def complete_investigation_task(
    conn: sqlite3.Connection,
    task_id: str,
    completed_by: str,
    evidence_id: Optional[str] = None
) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE investigation_tasks
        SET is_completed = 1, completed_by = ?, completed_at = ?, evidence_id = ?
        WHERE id = ?
    """, (completed_by, now, evidence_id, task_id))
    return {"task_id": task_id, "is_completed": True, "completed_at": now}

def submit_case_disposition(
    conn: sqlite3.Connection,
    investigation_id: str,
    analyst_id: str,
    analyst_name: str,
    disposition: str,
    rationale: str,
    requires_peer_review: bool = False
) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    
    # Check current case
    cursor.execute("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
    inv_row = cursor.fetchone()
    if not inv_row:
        raise ValueError("Investigation not found")
        
    inv = dict(inv_row)
    
    if requires_peer_review:
        new_status = "PENDING_PEER_REVIEW"
        peer_status = "REQUESTED"
    else:
        new_status = "RESOLVED"
        peer_status = "NONE"
        
    cursor.execute("""
        UPDATE investigations
        SET disposition = ?, disposition_rationale = ?, disposition_submitted_at = ?,
            status = ?, peer_review_status = ?, updated_at = ?
        WHERE id = ?
    """, (disposition, rationale, now, new_status, peer_status, now, investigation_id))
    
    # Count reviewed evidence
    cursor.execute("SELECT COUNT(*) FROM evidence_items WHERE investigation_id = ?", (investigation_id,))
    ev_count = cursor.fetchone()[0]
    
    # Controlled learning label policy check
    is_eligible, label_val, exclusion_reason = evaluate_disposition_label(disposition, peer_status)
    
    record_feedback(conn, {
        "investigation_id": investigation_id,
        "analyst_id": analyst_id,
        "disposition": disposition,
        "rationale": rationale,
        "evidence_reviewed_count": ev_count,
        "is_eligible_for_training": 1 if is_eligible else 0,
        "training_label": label_val,
        "exclusion_reason": exclusion_reason,
        "model_version": inv.get("model_version", "v1.0"),
        "rule_version": inv.get("rule_version", "v1.0")
    })
    
    record_audit_event(
        conn, analyst_id, analyst_name, "SUBMIT_DISPOSITION", "INVESTIGATION", investigation_id,
        {"disposition": disposition, "status": new_status, "eligible_training": is_eligible}
    )
    
    return {
        "investigation_id": investigation_id,
        "status": new_status,
        "disposition": disposition,
        "peer_review_status": peer_status,
        "feedback_recorded": True,
        "training_label_eligible": is_eligible
    }

def process_peer_review(
    conn: sqlite3.Connection,
    investigation_id: str,
    reviewer_id: str,
    reviewer_name: str,
    action: str, # APPROVED, REJECTED
    notes: str
) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("SELECT disposition FROM investigations WHERE id = ?", (investigation_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError("Investigation not found")
        
    disposition = row[0]
    
    if action.upper() == "APPROVED":
        new_status = "RESOLVED"
        peer_status = "APPROVED"
        # Update feedback eligibility now that it is approved
        is_eligible, label_val, reason = evaluate_disposition_label(disposition, peer_status)
        cursor.execute("""
            UPDATE analyst_feedback
            SET is_eligible_for_training = ?, training_label = ?, exclusion_reason = ?
            WHERE investigation_id = ?
        """, (1 if is_eligible else 0, label_val, reason, investigation_id))
    else:
        new_status = "REOPENED"
        peer_status = "REJECTED"
        
    cursor.execute("""
        UPDATE investigations
        SET peer_reviewer_id = ?, peer_review_status = ?, peer_review_notes = ?,
            peer_reviewed_at = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (reviewer_id, peer_status, notes, now, new_status, now, investigation_id))
    
    record_audit_event(
        conn, reviewer_id, reviewer_name, f"PEER_REVIEW_{action.upper()}", "INVESTIGATION", investigation_id,
        {"action": action, "notes": notes, "new_status": new_status}
    )
    
    return {
        "investigation_id": investigation_id,
        "status": new_status,
        "peer_review_status": peer_status,
        "message": f"Peer review {action.lower()} recorded."
    }
