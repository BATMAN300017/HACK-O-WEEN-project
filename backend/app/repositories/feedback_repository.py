import sqlite3
from typing import Dict, Any, List, Optional
from app.utils.ids import generate_id
from app.utils.time import utc_now_iso

def record_feedback(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    f_id = generate_id("FDB")
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analyst_feedback (
            id, investigation_id, analyst_id, disposition, rationale,
            evidence_reviewed_count, is_eligible_for_training, training_label,
            exclusion_reason, model_version, rule_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f_id, data["investigation_id"], data["analyst_id"], data["disposition"],
        data["rationale"], data.get("evidence_reviewed_count", 0),
        data["is_eligible_for_training"], data.get("training_label"),
        data.get("exclusion_reason"), data.get("model_version", "v1.0"),
        data.get("rule_version", "v1.0"), now
    ))
    return {**data, "id": f_id, "created_at": now}

def get_feedback_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'CONFIRMED_FRAUD'")
    fraud_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition IN ('LEGITIMATE_ACTIVITY', 'FALSE_POSITIVE')")
    fp_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'INCONCLUSIVE'")
    inconclusive_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE disposition = 'SUSPICIOUS_UNCONFIRMED'")
    suspicious_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE is_eligible_for_training = 1")
    eligible_cnt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE training_label = 1")
    pos_lbls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyst_feedback WHERE training_label = 0")
    neg_lbls = cursor.fetchone()[0]
    
    cursor.execute("SELECT created_at FROM analyst_feedback ORDER BY created_at DESC LIMIT 1")
    last_row = cursor.fetchone()
    last_fb = last_row[0] if last_row else None
    
    return {
        "total_feedback_count": total,
        "confirmed_fraud_count": fraud_cnt,
        "false_positive_count": fp_cnt,
        "inconclusive_count": inconclusive_cnt,
        "suspicious_unconfirmed_count": suspicious_cnt,
        "eligible_for_training_count": eligible_cnt,
        "positive_labels": pos_lbls,
        "negative_labels": neg_lbls,
        "last_feedback_at": last_fb
    }
