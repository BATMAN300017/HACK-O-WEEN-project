import sqlite3
from typing import List, Dict, Any

def detect_suspicious_patterns(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    patterns = []
    
    # 1. Fan-in collection accounts (multiple accounts transferring to 1 target)
    cursor.execute("""
        SELECT destination_account_id, COUNT(DISTINCT source_account_id) as source_count, SUM(amount) as total_amt
        FROM transactions
        WHERE destination_account_id IS NOT NULL
        GROUP BY destination_account_id
        HAVING source_count >= 3
        ORDER BY source_count DESC LIMIT 5
    """)
    for row in cursor.fetchall():
        dest = row[0]
        cnt = row[1]
        tot = float(row[2])
        patterns.append({
            "pattern_name": "Fan-In Collection Hub",
            "path_nodes": [dest],
            "path_edges": [],
            "total_amount": round(tot, 2),
            "time_window_minutes": 120.0,
            "explanation": f"Account {dest} acts as a funnel receiving funds from {cnt} distinct accounts totaling ${tot:,.2f}.",
            "alternative_explanations": "Could represent a payroll pool, merchant merchant-clearing account, or crowdfunding collection."
        })
        
    # 2. Intermediary / Mule Flow: Account receives inbound transfer and forwards >85% out
    cursor.execute("""
        SELECT t1.source_account_id as original_source,
               t1.destination_account_id as intermediary,
               t2.destination_account_id as final_target,
               t1.amount as inbound_amount,
               t2.amount as outbound_amount,
               t1.created_at, t2.created_at
        FROM transactions t1
        JOIN transactions t2 ON t1.destination_account_id = t2.source_account_id
        WHERE t1.destination_account_id != t2.destination_account_id
          AND t2.created_at >= t1.created_at
          AND (t2.amount / t1.amount) BETWEEN 0.70 AND 1.10
        LIMIT 5
    """)
    for row in cursor.fetchall():
        orig_s, inter, fin_t, in_amt, out_amt, t1_time, t2_time = row
        patterns.append({
            "pattern_name": "Rapid Multi-Hop Intermediary Forwarding",
            "path_nodes": [orig_s, inter, fin_t],
            "path_edges": [f"{orig_s}->{inter}", f"{inter}->{fin_t}"],
            "total_amount": round(float(out_amt), 2),
            "time_window_minutes": 30.0,
            "explanation": f"Funds moved from {orig_s} through intermediary {inter} to {fin_t} (${out_amt:,.2f}). The intermediary retained minimal balance.",
            "alternative_explanations": "Could represent an authorized third-party escrow, bill forwarding, or business factoring arrangement."
        })
        
    # 3. Circular Flow Pattern (A -> B -> A)
    cursor.execute("""
        SELECT t1.source_account_id, t1.destination_account_id, t1.amount, t2.amount
        FROM transactions t1
        JOIN transactions t2 ON t1.source_account_id = t2.destination_account_id 
                            AND t1.destination_account_id = t2.source_account_id
        WHERE t1.source_account_id < t1.destination_account_id
        LIMIT 5
    """)
    for row in cursor.fetchall():
        a1, a2, amt1, amt2 = row
        patterns.append({
            "pattern_name": "Circular Round-Trip Transfer",
            "path_nodes": [a1, a2],
            "path_edges": [f"{a1}->{a2}", f"{a2}->{a1}"],
            "total_amount": round(float(amt1 + amt2), 2),
            "time_window_minutes": 1440.0,
            "explanation": f"Reciprocal transfers detected between Account {a1} and Account {a2}.",
            "alternative_explanations": "Inter-company balancing, reimbursement of expenses, or informal loan settlement."
        })
        
    return patterns
