from typing import Dict, Any, List
import numpy as np
from sklearn.linear_model import LogisticRegression
from app.learning.evaluator import evaluate_candidate_model, MINIMUM_REQUIRED_SAMPLES

def train_candidate_model(dataset: Dict[str, Any]) -> Dict[str, Any]:
    samples = dataset.get("samples", [])
    if len(samples) < MINIMUM_REQUIRED_SAMPLES:
        return {
            "success": False,
            "candidate_version": None,
            "message": f"Training aborted: dataset contains {len(samples)} samples, which is below the minimum required threshold ({MINIMUM_REQUIRED_SAMPLES}).",
            "eval_report": {
                "passed": False,
                "reason": f"Insufficient training data ({len(samples)}/{MINIMUM_REQUIRED_SAMPLES} samples)",
                "metrics": {}
            }
        }
        
    X = np.array([s["features"] for s in samples])
    y = np.array([s["label"] for s in samples])
    
    # Chronological holdout split: 70% train, 30% test
    split_idx = int(len(samples) * 0.70)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    clf = LogisticRegression(class_weight="balanced")
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    y_scores = clf.predict_proba(X_test)[:, 1]
    
    eval_report = evaluate_candidate_model(list(y_test), list(y_pred), list(y_scores))
    cand_version = f"CANDIDATE_{dataset['dataset_version']}"
    
    return {
        "success": True,
        "candidate_version": cand_version,
        "model": clf,
        "eval_report": eval_report,
        "message": "Candidate model successfully trained and evaluated against chronological holdout."
    }
