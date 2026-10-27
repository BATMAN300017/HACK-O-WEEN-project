import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple
from app.utils.ids import generate_investigation_id
from app.utils.time import utc_now_iso

def create_investigation(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    inv_id = data.get("id") or generate_investigation_id()
    case_num = data.get("case_number") or f"CASE-2026-{inv_id[-5:].upper()}"
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO investigations (
            id, case_number, title, summary, priority, status,
            assigned_investigator_id, due_date, evidence_completeness_score,
            model_version, rule_version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        inv_id, case_num, data["title"], data["summary"], data.get("priority", "HIGH"),
        data.get("status", "NEW"), data.get("assigned_investigator_id"),
        data.get("due_date"), float(data.get("evidence_completeness_score", 0.0)),
        data.get("model_version", "v1.0"), data.get("rule_version", "v1.0"),
        now, now
    ))
    
    # Associate alerts
    alert_ids = data.get("alert_ids", [])
    for aid in alert_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO investigation_alerts (investigation_id, alert_id, added_at)
            VALUES (?, ?, ?)
        """, (inv_id, aid, now))
        cursor.execute("UPDATE alerts SET status = 'CONVERTED_TO_INVESTIGATION' WHERE id = ?", (aid,))
        
    return {**data, "id": inv_id, "case_number": case_num, "created_at": now, "updated_at": now}

def get_investigation_by_id(conn: sqlite3.Connection, inv_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, u.full_name as assigned_investigator_name, r.full_name as reviewer_name
        FROM investigations i
        LEFT JOIN users u ON i.assigned_investigator_id = u.id
        LEFT JOIN users r ON i.peer_reviewer_id = r.id
        WHERE i.id = ? OR i.case_number = ?
    """, (inv_id, inv_id))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    
    # Counts
    cursor.execute("SELECT COUNT(*) FROM investigation_alerts WHERE investigation_id = ?", (d["id"],))
    d["alerts_count"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM evidence_items WHERE investigation_id = ?", (d["id"],))
    d["evidence_count"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM investigation_tasks WHERE investigation_id = ?", (d["id"],))
    d["tasks_count"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM investigation_notes WHERE investigation_id = ?", (d["id"],))
    d["notes_count"] = cursor.fetchone()[0]
    
    return d

def list_investigations(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    cursor = conn.cursor()
    query = "SELECT * FROM investigations WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM investigations WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status.upper())
    if priority:
        query += " AND priority = ?"
        count_query += " AND priority = ?"
        params.append(priority.upper())
        
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    return items, total
