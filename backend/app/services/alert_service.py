import sqlite3
from typing import Dict, Any, Optional
from app.utils.time import utc_now_iso
from app.services.audit_service import record_audit_event
from app.services.intelligence_service import orchestrate_self_directed_investigation

def assign_alert(conn: sqlite3.Connection, alert_id: str, user_id: str, actor_name: str) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET assigned_to = ?, status = 'IN_REVIEW', updated_at = ? WHERE id = ?", (user_id, now, alert_id))
    record_audit_event(conn, user_id, actor_name, "ASSIGN_ALERT", "ALERT", alert_id)
    return {"success": True, "alert_id": alert_id, "assigned_to": user_id}

def triage_alert(conn: sqlite3.Connection, alert_id: str, severity: str, notes: Optional[str], actor_name: str) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET severity = ?, status = 'TRIAGED', updated_at = ? WHERE id = ?", (severity.upper(), now, alert_id))
    record_audit_event(conn, None, actor_name, "TRIAGE_ALERT", "ALERT", alert_id, {"severity": severity, "notes": notes})
    return {"success": True, "alert_id": alert_id, "severity": severity}

def dismiss_alert(conn: sqlite3.Connection, alert_id: str, reason: str, actor_name: str) -> Dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = 'DISMISSED', dismissal_reason = ?, updated_at = ? WHERE id = ?", (reason, now, alert_id))
    record_audit_event(conn, None, actor_name, "DISMISS_ALERT", "ALERT", alert_id, {"reason": reason})
    return {"success": True, "alert_id": alert_id, "status": "DISMISSED"}

def convert_alert_to_investigation(conn: sqlite3.Connection, alert_id: str, actor_name: str) -> Dict[str, Any]:
    res = orchestrate_self_directed_investigation(conn, alert_id)
    record_audit_event(conn, None, actor_name, "CONVERT_ALERT_TO_INVESTIGATION", "ALERT", alert_id, res)
    return res
