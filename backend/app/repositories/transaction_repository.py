import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from app.utils.ids import generate_transaction_id
from app.utils.time import utc_now_iso

def create_transaction(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    txn_id = data.get("id") or generate_transaction_id()
    now = data.get("created_at") or utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (
            id, event_id, source_account_id, destination_account_id, beneficiary_name,
            customer_id, amount, currency, transaction_type, payment_channel,
            merchant_id, device_id, ip_address, status, scenario_id,
            is_ground_truth_fraud, ground_truth_label, risk_score, risk_band, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        txn_id, data["event_id"], data["source_account_id"], data.get("destination_account_id"),
        data.get("beneficiary_name"), data["customer_id"], float(data["amount"]),
        data.get("currency", "USD"), data.get("transaction_type", "TRANSFER"),
        data.get("payment_channel", "ONLINE"), data.get("merchant_id"),
        data.get("device_id"), data.get("ip_address"), data.get("status", "COMPLETED"),
        data.get("scenario_id"), data.get("is_ground_truth_fraud", 0),
        data.get("ground_truth_label"), data.get("risk_score", 0.0),
        data.get("risk_band", "ROUTINE"), now
    ))
    return {**data, "id": txn_id, "created_at": now}

def get_transaction_by_id(conn: sqlite3.Connection, txn_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE id = ? OR event_id = ?", (txn_id, txn_id))
    row = cursor.fetchone()
    return dict(row) if row else None

def list_transactions(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
    risk_band: Optional[str] = None,
    account_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    cursor = conn.cursor()
    query = "SELECT * FROM transactions WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
    params = []
    
    if risk_band:
        query += " AND risk_band = ?"
        count_query += " AND risk_band = ?"
        params.append(risk_band.upper())
    if account_id:
        query += " AND (source_account_id = ? OR destination_account_id = ?)"
        count_query += " AND (source_account_id = ? OR destination_account_id = ?)"
        params.extend([account_id, account_id])
        
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    return items, total
