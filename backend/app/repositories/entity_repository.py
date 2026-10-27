import sqlite3
from typing import Dict, Any, List, Optional

def get_entity_profile(conn: sqlite3.Connection, entity_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    # 1. Try Customer
    cursor.execute("SELECT * FROM customers WHERE id = ? OR customer_ref = ?", (entity_id, entity_id))
    cust = cursor.fetchone()
    if cust:
        c_dict = dict(cust)
        cursor.execute("SELECT id FROM accounts WHERE customer_id = ?", (c_dict["id"],))
        accs = [r[0] for r in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE customer_id = ?", (c_dict["id"],))
        alt_cnt = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT investigation_id) FROM investigation_alerts ia
            JOIN alerts a ON ia.alert_id = a.id
            WHERE a.customer_id = ?
        """, (c_dict["id"],))
        inv_cnt = cursor.fetchone()[0]
        
        return {
            "id": c_dict["id"],
            "entity_type": "CUSTOMER",
            "label": c_dict["full_name"],
            "details": {"email": c_dict["email"], "risk_tier": c_dict["risk_tier"], "kyc_status": c_dict["kyc_status"]},
            "risk_signals": [{"code": "TIER", "label": f"Risk tier: {c_dict['risk_tier']}"}],
            "associated_accounts": accs,
            "alert_count": alt_cnt,
            "investigation_count": inv_cnt,
            "created_at": c_dict["created_at"]
        }
        
    # 2. Try Account
    cursor.execute("SELECT * FROM accounts WHERE id = ? OR account_number = ?", (entity_id, entity_id))
    acc = cursor.fetchone()
    if acc:
        a_dict = dict(acc)
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE account_id = ?", (a_dict["id"],))
        alt_cnt = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(DISTINCT investigation_id) FROM investigation_alerts ia
            JOIN alerts a ON ia.alert_id = a.id
            WHERE a.account_id = ?
        """, (a_dict["id"],))
        inv_cnt = cursor.fetchone()[0]
        
        signals = []
        if a_dict["is_dormant"]:
            signals.append({"code": "DORMANT", "label": "Account flagged as dormant"})
            
        return {
            "id": a_dict["id"],
            "entity_type": "ACCOUNT",
            "label": f"Account {a_dict['account_number']}",
            "details": {"type": a_dict["account_type"], "balance": a_dict["balance"], "currency": a_dict["currency"], "status": a_dict["status"]},
            "risk_signals": signals,
            "associated_accounts": [a_dict["id"]],
            "alert_count": alt_cnt,
            "investigation_count": inv_cnt,
            "created_at": a_dict["created_at"]
        }
        
    return None
