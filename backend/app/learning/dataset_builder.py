import sqlite3
import json
from typing import Dict, Any, List, Tuple
from app.utils.time import utc_now_iso

def build_training_dataset(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.investigation_id, f.training_label, f.training_label as label,
               i.case_number
        FROM analyst_feedback f
        JOIN investigations i ON f.investigation_id = i.id
        WHERE f.is_eligible_for_training = 1 AND f.training_label IS NOT NULL
        ORDER BY f.created_at ASC
    """)
    rows = cursor.fetchall()
    
    samples = []
    pos_count = 0
    neg_count = 0
    
    for r in rows:
        inv_id = r["investigation_id"]
        label = int(r["training_label"])
        if label == 1:
            pos_count += 1
        else:
            neg_count += 1
            
        # Get associated transaction features for this case
        cursor.execute("""
            SELECT t.amount, t.risk_score
            FROM investigation_alerts ia
            JOIN alerts a ON ia.alert_id = a.id
            JOIN transactions t ON a.transaction_id = t.id
            WHERE ia.investigation_id = ? LIMIT 1
        """, (inv_id,))
        t_row = cursor.fetchone()
        amount = t_row["amount"] if t_row else 1000.0
        score = t_row["risk_score"] if t_row else 50.0
        
        # Synthetic feature vector: [amount_norm, score_norm]
        features = [amount / 10000.0, score / 100.0]
        samples.append({
            "investigation_id": inv_id,
            "features": features,
            "label": label
        })
        
    version_tag = f"DS_V{len(samples)}_{utc_now_iso()[:10]}"
    return {
        "dataset_version": version_tag,
        "sample_count": len(samples),
        "positive_count": pos_count,
        "negative_count": neg_count,
        "samples": samples
    }
