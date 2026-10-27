import sqlite3
from typing import Dict, Any, List

def evaluate_graph_signals(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    source_acc = txn["source_account_id"]
    dest_acc = txn.get("destination_account_id")
    device_id = txn.get("device_id")
    
    score = 0.0
    signals = []
    
    cursor = conn.cursor()
    
    # 1. Multi-account shared device
    if device_id:
        cursor.execute("""
            SELECT COUNT(DISTINCT source_account_id)
            FROM transactions
            WHERE device_id = ?
        """, (device_id,))
        acc_count = cursor.fetchone()[0]
        if acc_count >= 4:
            score += 40.0
            signals.append({
                "code": "GRAPH_DEVICE_CLUSTER",
                "score": 40.0,
                "description": f"Device {device_id[:8]}... is shared by {acc_count} distinct source accounts"
            })
        elif acc_count >= 2:
            score += 15.0
            signals.append({
                "code": "GRAPH_SHARED_DEVICE",
                "score": 15.0,
                "description": f"Device shared with {acc_count - 1} other account(s)"
            })
            
    # 2. Fan-in pattern: Destination account received transfers from many distinct sources recently
    if dest_acc:
        cursor.execute("""
            SELECT COUNT(DISTINCT source_account_id)
            FROM transactions
            WHERE destination_account_id = ?
        """, (dest_acc,))
        in_degrees = cursor.fetchone()[0]
        if in_degrees >= 4:
            score += 35.0
            signals.append({
                "code": "GRAPH_FAN_IN_COLLECTOR",
                "score": 35.0,
                "description": f"Destination account {dest_acc} acts as collection node receiving funds from {in_degrees} distinct accounts"
            })
            
    # 3. Two-hop chain / Intermediary account forwarding
    if dest_acc:
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE source_account_id = ?
        """, (dest_acc,))
        forward_row = cursor.fetchone()
        if forward_row[0] > 0:
            score += 20.0
            signals.append({
                "code": "GRAPH_INTERMEDIARY_NODE",
                "score": 20.0,
                "description": f"Destination account {dest_acc} also acts as an active forwarder ({forward_row[0]} outgoing transfers)"
            })
            
    # 4. Circular cycle: Has dest_acc previously sent funds back to source_acc?
    if dest_acc:
        cursor.execute("""
            SELECT 1 FROM transactions
            WHERE source_account_id = ? AND destination_account_id = ?
            LIMIT 1
        """, (dest_acc, source_acc))
        if cursor.fetchone():
            score += 30.0
            signals.append({
                "code": "GRAPH_CIRCULAR_FLOW",
                "score": 30.0,
                "description": f"Circular fund flow detected: Counterparty {dest_acc} has transferred funds back to {source_acc}"
            })
            
    return {
        "graph_score": min(100.0, score),
        "signals": signals
    }
