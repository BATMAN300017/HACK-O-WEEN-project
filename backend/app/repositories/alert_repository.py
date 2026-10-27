import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple
from app.utils.ids import generate_alert_id
from app.utils.time import utc_now_iso

def create_alert(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    alert_id = data.get("id") or generate_alert_id()
    alert_ref = data.get("alert_ref") or f"ALT-{alert_id[-6:].upper()}"
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (
            id, alert_ref, transaction_id, account_id, customer_id,
            severity, status, risk_score, title, summary, assigned_to,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_id, alert_ref, data["transaction_id"], data["account_id"],
        data["customer_id"], data["severity"], data.get("status", "NEW"),
        float(data["risk_score"]), data["title"], data["summary"],
        data.get("assigned_to"), now, now
    ))
    
    # Save findings
    findings = data.get("findings", [])
    for f in findings:
        f_id = f.get("id") or f"FND-{generate_alert_id()[-6:]}"
        feat_json = json.dumps(f.get("feature_values", {}))
        cursor.execute("""
            INSERT INTO alert_findings (id, alert_id, source, code, description, score_contribution, feature_values_json, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f_id, alert_id, f.get("source", "RULE"), f.get("code", "UNKNOWN"), f.get("description", ""), float(f.get("score_contribution", 0.0)), feat_json, f.get("version", "v1"), now))
        
    return {**data, "id": alert_id, "alert_ref": alert_ref, "created_at": now, "updated_at": now}

def get_alert_by_id(conn: sqlite3.Connection, alert_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE id = ? OR alert_ref = ?", (alert_id, alert_id))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    cursor.execute("SELECT * FROM alert_findings WHERE alert_id = ?", (d["id"],))
    findings = []
    for f_row in cursor.fetchall():
        f_dict = dict(f_row)
        f_dict["feature_values"] = json.loads(f_dict.get("feature_values_json") or "{}")
        findings.append(f_dict)
    d["findings"] = findings
    return d

def list_alerts(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    severity: Optional[str] = None,
    status: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    cursor = conn.cursor()
    query = "SELECT * FROM alerts WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM alerts WHERE 1=1"
    params = []
    
    if severity:
        query += " AND severity = ?"
        count_query += " AND severity = ?"
        params.append(severity.upper())
    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status.upper())
        
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY risk_score DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    return items, total
