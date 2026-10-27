from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

MINIMUM_REQUIRED_SAMPLES = 20
MINIMUM_CLASS_COUNT = 5

def evaluate_candidate_model(y_true: List[int], y_pred: List[int], y_scores: List[float]) -> Dict[str, Any]:
    if len(y_true) < MINIMUM_REQUIRED_SAMPLES:
        return {
            "passed": False,
            "reason": f"Sample size too small ({len(y_true)}/{MINIMUM_REQUIRED_SAMPLES} required). Platform refuses to promote unqualified model on insufficient data.",
            "metrics": {}
        }
        
    pos_count = sum(y_true)
    neg_count = len(y_true) - pos_count
    if pos_count < MINIMUM_CLASS_COUNT or neg_count < MINIMUM_CLASS_COUNT:
        return {
            "passed": False,
            "reason": f"Severe class imbalance: {pos_count} positives, {neg_count} negatives. Minimum {MINIMUM_CLASS_COUNT} per class required.",
            "metrics": {}
        }
        
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_scores)
    except Exception:
        auc = 0.5
        
    metrics = {
        "precision": round(float(prec), 3),
        "recall": round(float(rec), 3),
        "f1": round(float(f1), 3),
        "pr_auc": round(float(auc), 3)
    }
    
    # Promotion Gate: Precision must exceed 0.70 and F1 > 0.60
    if prec >= 0.70 and f1 >= 0.60:
        return {
            "passed": True,
            "reason": f"Candidate model passed promotion gate (Precision: {prec:.2f}, F1: {f1:.2f})",
            "metrics": metrics
        }
    else:
        return {
            "passed": False,
            "reason": f"Candidate failed performance thresholds (Precision: {prec:.2f} < 0.70 or F1: {f1:.2f} < 0.60)",
            "metrics": metrics
        }
