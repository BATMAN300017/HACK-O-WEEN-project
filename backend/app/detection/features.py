import sqlite3
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.utils.time import parse_iso

def extract_transaction_features(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    source_acc = txn["source_account_id"]
    dest_acc = txn.get("destination_account_id")
    device_id = txn.get("device_id")
    txn_amount = float(txn["amount"])
    txn_time_str = txn.get("created_at")
    
    # 1. Historical account transactions (last 30 days)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, created_at, destination_account_id, beneficiary_name, device_id, status, transaction_type
        FROM transactions
        WHERE source_account_id = ? AND id != ?
        ORDER BY created_at DESC LIMIT 100
    """, (source_acc, txn.get("id", "")))
    history = [dict(row) for row in cursor.fetchall()]
    
    # Baseline stats
    history_count = len(history)
    amounts = [float(h["amount"]) for h in history]
    
    # Account dormancy check
    cursor.execute("SELECT is_dormant, created_at FROM accounts WHERE id = ?", (source_acc,))
    acc_row = cursor.fetchone()
    is_dormant_flag = acc_row["is_dormant"] if acc_row else 0
    
    # Short window velocity (last 10 minutes)
    ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE source_account_id = ? AND created_at >= ? AND id != ?
    """, (source_acc, ten_mins_ago, txn.get("id", "")))
    short_vel_row = cursor.fetchone()
    short_window_count = int(short_vel_row[0]) + 1
    short_window_sum = float(short_vel_row[1]) + txn_amount
    
    # Rapid Inbound followed by Outbound check (last 30 mins)
    thirty_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0), COUNT(*)
        FROM transactions
        WHERE destination_account_id = ? AND created_at >= ?
    """, (source_acc, thirty_mins_ago))
    inbound_row = cursor.fetchone()
    recent_inbound_sum = float(inbound_row[0])
    recent_inbound_count = inbound_row[1]
    
    # Beneficiary novelty check
    beneficiary = txn.get("beneficiary_name") or dest_acc
    is_new_beneficiary = 1
    if beneficiary:
        cursor.execute("""
            SELECT 1 FROM transactions
            WHERE source_account_id = ? AND (destination_account_id = ? OR beneficiary_name = ?)
            AND id != ? LIMIT 1
        """, (source_acc, dest_acc, beneficiary, txn.get("id", "")))
        if cursor.fetchone():
            is_new_beneficiary = 0
            
    # Shared device count (how many distinct accounts used this device?)
    shared_device_accounts = 1
    if device_id:
        cursor.execute("""
            SELECT COUNT(DISTINCT source_account_id)
            FROM transactions
            WHERE device_id = ?
        """, (device_id,))
        dev_row = cursor.fetchone()
        shared_device_accounts = max(1, dev_row[0])
        
    # Reversal count
    cursor.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE source_account_id = ? AND status = 'REVERSED'
    """, (source_acc,))
    reversal_count = cursor.fetchone()[0]
    
    return {
        "amount": txn_amount,
        "history_count": history_count,
        "is_cold_start": 1 if history_count < 5 else 0,
        "is_dormant_account": is_dormant_flag,
        "short_window_count": short_window_count,
        "short_window_sum": short_window_sum,
        "recent_inbound_sum": recent_inbound_sum,
        "recent_inbound_count": recent_inbound_count,
        "is_new_beneficiary": is_new_beneficiary,
        "shared_device_accounts": shared_device_accounts,
        "historical_amounts": amounts,
        "reversal_count": reversal_count,
    }
