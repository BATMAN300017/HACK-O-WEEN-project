import numpy as np
from typing import Dict, Any, Optional
from sklearn.linear_model import LogisticRegression

_global_model: Optional[LogisticRegression] = None
_model_version: str = "LOGREG_V1_BASELINE"
_is_trained: bool = False

def predict_supervised_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    global _global_model, _is_trained
    
    # Feature vector: [amount, velocity_count, is_cold_start, is_dormant, is_new_beneficiary, shared_device_count]
    raw_vec = [
        float(features.get("amount", 0.0)) / 10000.0, # normalized
        float(features.get("short_window_count", 1)),
        float(features.get("is_cold_start", 0)),
        float(features.get("is_dormant_account", 0)),
        float(features.get("is_new_beneficiary", 0)),
        float(features.get("shared_device_accounts", 1)),
    ]
    
    if not _is_trained or _global_model is None:
        # Pre-calibrated initial baseline logistic regression weights
        weights = np.array([0.35, 0.40, 0.10, 0.45, 0.30, 0.50])
        bias = -2.2
        logit = np.dot(raw_vec, weights) + bias
        prob = 1.0 / (1.0 + np.exp(-logit))
        score = float(prob * 100.0)
        return {
            "supervised_score": round(score, 1),
            "model_version": f"{_model_version}_COLD_START",
            "confidence": "BASELINE_CALIBRATED",
            "is_trained_on_feedback": False,
            "feature_contributions": {
                "amount_norm": round(raw_vec[0] * weights[0], 2),
                "velocity": round(raw_vec[1] * weights[1], 2),
                "dormancy": round(raw_vec[3] * weights[3], 2),
                "device_sharing": round(raw_vec[5] * weights[5], 2)
            }
        }
        
    prob = _global_model.predict_proba([raw_vec])[0][1]
    return {
        "supervised_score": round(float(prob * 100.0), 1),
        "model_version": _model_version,
        "confidence": "TRAINED_MODEL",
        "is_trained_on_feedback": True
    }

def update_active_model(model: LogisticRegression, version_tag: str):
    global _global_model, _model_version, _is_trained
    _global_model = model
    _model_version = version_tag
    _is_trained = True
