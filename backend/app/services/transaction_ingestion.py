import sqlite3
import json
from typing import Dict, Any, Optional
from app.repositories.transaction_repository import create_transaction, get_transaction_by_id
from app.repositories.alert_repository import create_alert
from app.detection.engine import score_transaction
from app.services.intelligence_service import orchestrate_self_directed_investigation
from app.services.audit_service import record_audit_event
from app.utils.ids import generate_alert_id

def ingest_transaction_event(conn: sqlite3.Connection, event_data: Dict[str, Any]) -> Dict[str, Any]:
    event_id = event_data["event_id"]
    
    # 1. Idempotency / Duplicate Check
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE event_id = ?", (event_id,))
    existing = cursor.fetchone()
    if existing:
        return {"status": "DUPLICATE_IGNORED", "transaction_id": existing[0]}
        
    # 2. Score transaction through hybrid detection engine
    detection_result = score_transaction(conn, event_data)
    
    # 3. Persist transaction with evaluated risk score and band
    txn_data = {
        **event_data,
        "risk_score": detection_result["final_risk_score"],
        "risk_band": detection_result["risk_band"]
    }
    persisted_txn = create_transaction(conn, txn_data)
    txn_id = persisted_txn["id"]
    
    # 4. Create Alert if risk exceeds threshold or rules triggered
    alert_created = False
    alert_id = None
    final_score = detection_result["final_risk_score"]
    triggered_rules = detection_result["triggered_rules"]
    
    if final_score >= 50.0 or len(triggered_rules) > 0:
        alert_id = generate_alert_id()
        findings = []
        for r in triggered_rules:
            findings.append({
                "source": "RULE",
                "code": r["rule_code"],
                "description": r["description"],
                "score_contribution": r["score_contribution"],
                "feature_values": r["feature_values"],
                "version": r["version"]
            })
        for s in detection_result["graph_signals"]:
            findings.append({
                "source": "GRAPH",
                "code": s["code"],
                "description": s["description"],
                "score_contribution": s["score"],
                "version": "v1.0"
            })
        if detection_result["behavioral_anomaly"]["anomaly_detected"]:
            findings.append({
                "source": "ANOMALY",
                "code": "MAD_AMOUNT_DEVIATION",
                "description": detection_result["behavioral_anomaly"]["reason"],
                "score_contribution": detection_result["behavioral_anomaly"]["score"],
                "version": "v1.0"
            })
            
        title = f"Suspicious Activity Alert: {detection_result['risk_band']} Priority"
        if triggered_rules:
            title = f"Alert: {triggered_rules[0]['name']}"
            
        alert_dict = {
            "id": alert_id,
            "transaction_id": txn_id,
            "account_id": event_data["source_account_id"],
            "customer_id": event_data["customer_id"],
            "severity": detection_result["recommended_severity"],
            "status": "NEW",
            "risk_score": final_score,
            "title": title,
            "summary": detection_result["narrative_explanation"],
            "findings": findings
        }
        create_alert(conn, alert_dict)
        alert_created = True
        
        # 5. Automatically initiate self-directed investigation if High Risk
        if final_score >= 70.0:
            orchestrate_self_directed_investigation(conn, alert_id)
            
    # 6. Audit Trail
    record_audit_event(
        conn,
        actor_id=None,
        actor_name="INGESTION_PIPELINE",
        action="TRANSACTION_INGESTED",
        resource_type="TRANSACTION",
        resource_id=txn_id,
        metadata={"amount": event_data["amount"], "risk_score": final_score, "alert_created": alert_created}
    )
    
    return {
        "status": "INGESTED",
        "transaction_id": txn_id,
        "risk_score": final_score,
        "risk_band": detection_result["risk_band"],
        "alert_created": alert_created,
        "alert_id": alert_id
    }
