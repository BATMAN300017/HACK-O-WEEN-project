from typing import Dict, Any, List
from app.core.config import settings
from app.detection.calibration import assign_triage_band, assign_alert_severity

def compute_ensemble_risk(
    rule_score: float,
    anomaly_score: float,
    supervised_score: float,
    graph_score: float
) -> Dict[str, Any]:
    w_rules = settings.RULE_ENGINE_WEIGHT
    w_anom = settings.BEHAVIORAL_ANOMALY_WEIGHT
    w_sup = settings.SUPERVISED_MODEL_WEIGHT
    w_graph = settings.GRAPH_INTELLIGENCE_WEIGHT
    
    # Composite calculation
    composite = (
        (rule_score * w_rules) +
        (anomaly_score * w_anom) +
        (supervised_score * w_sup) +
        (graph_score * w_graph)
    )
    
    final_score = round(min(100.0, max(0.0, composite)), 1)
    band = assign_triage_band(final_score)
    severity = assign_alert_severity(final_score)
    
    return {
        "final_risk_score": final_score,
        "risk_band": band,
        "recommended_severity": severity,
        "component_scores": {
            "rules": round(rule_score, 1),
            "anomaly": round(anomaly_score, 1),
            "supervised": round(supervised_score, 1),
            "graph": round(graph_score, 1)
        },
        "weights": {
            "rules": w_rules,
            "anomaly": w_anom,
            "supervised": w_sup,
            "graph": w_graph
        }
    }
