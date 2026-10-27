import sqlite3
from typing import Dict, Any, List
from app.detection.features import extract_transaction_features
from app.detection.rules import evaluate_rules
from app.detection.anomaly import calculate_mad_anomaly
from app.detection.graph_signals import evaluate_graph_signals
from app.detection.supervised import predict_supervised_risk
from app.detection.ensemble import compute_ensemble_risk
from app.detection.explainability import generate_risk_explanation

def score_transaction(conn: sqlite3.Connection, txn: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Feature extraction
    features = extract_transaction_features(conn, txn)
    
    # 2. Rule evaluation
    triggered_rules = evaluate_rules(conn, txn, features)
    rule_score = min(100.0, sum(r["score_contribution"] for r in triggered_rules))
    
    # 3. Behavioral Anomaly
    historical_amounts = features.get("historical_amounts", [])
    is_cold = bool(features.get("is_cold_start", 0))
    anomaly_res = calculate_mad_anomaly(float(txn["amount"]), historical_amounts, is_cold)
    anomaly_score = anomaly_res["score"]
    
    # 4. Graph Signals
    graph_res = evaluate_graph_signals(conn, txn)
    graph_score = graph_res["graph_score"]
    
    # 5. Supervised Model
    sup_res = predict_supervised_risk(features)
    supervised_score = sup_res["supervised_score"]
    
    # 6. Ensemble Risk
    ensemble = compute_ensemble_risk(rule_score, anomaly_score, supervised_score, graph_score)
    final_score = ensemble["final_risk_score"]
    
    # 7. Narrative Explanation
    explanation = generate_risk_explanation(
        txn, features, triggered_rules, anomaly_res, graph_res, sup_res, final_score
    )
    
    return {
        "final_risk_score": final_score,
        "risk_band": ensemble["risk_band"],
        "recommended_severity": ensemble["recommended_severity"],
        "component_scores": ensemble["component_scores"],
        "ensemble_weights": ensemble["weights"],
        "triggered_rules": triggered_rules,
        "behavioral_anomaly": anomaly_res,
        "graph_signals": graph_res["signals"],
        "supervised_prediction": sup_res,
        "narrative_explanation": explanation,
        "features": features
    }
