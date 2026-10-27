import sqlite3
import json
from typing import Dict, Any, Optional
from app.utils.time import utc_now_iso

_active_model_version = "LOGREG_V1_BASELINE"
_active_metrics = {
    "precision": 0.82,
    "recall": 0.76,
    "f1": 0.79,
    "pr_auc": 0.84,
    "evaluated_on": "Synthetic Historical Benchmark v1"
}

_candidate_model: Optional[Any] = None
_candidate_version: Optional[str] = None
_candidate_metrics: Optional[Dict[str, Any]] = None

def get_registry_status() -> Dict[str, Any]:
    return {
        "active_version": _active_model_version,
        "active_metrics": _active_metrics,
        "candidate_available": _candidate_version is not None,
        "candidate_version": _candidate_version,
        "candidate_metrics": _candidate_metrics
    }

def register_candidate(version: str, model_obj: Any, metrics: Dict[str, Any]):
    global _candidate_model, _candidate_version, _candidate_metrics
    _candidate_version = version
    _candidate_model = model_obj
    _candidate_metrics = metrics

def promote_candidate(conn: sqlite3.Connection, actor_name: str) -> Dict[str, Any]:
    global _active_model_version, _active_metrics, _candidate_model, _candidate_version, _candidate_metrics
    if not _candidate_version or not _candidate_model:
        return {"success": False, "message": "No candidate model available to promote"}
        
    old_version = _active_model_version
    _active_model_version = _candidate_version
    _active_metrics = _candidate_metrics or {}
    
    # Update supervised module
    from app.detection.supervised import update_active_model
    update_active_model(_candidate_model, _active_model_version)
    
    # Record in DB model_versions
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO model_versions (id, version_tag, model_type, is_active, evaluation_metrics_json, parameters_json, promoted_by, promoted_at, created_at)
        VALUES (?, ?, 'LogisticRegression', 1, ?, '{}', ?, ?, ?)
    """, (f"MOD-{_active_model_version}", _active_model_version, json.dumps(_active_metrics), actor_name, now, now))
    conn.commit()
    
    _candidate_model = None
    _candidate_version = None
    _candidate_metrics = None
    
    return {
        "success": True,
        "message": f"Successfully promoted candidate model {_active_model_version} to active scoring engine.",
        "previous_version": old_version,
        "new_version": _active_model_version
    }

def rollback_model(conn: sqlite3.Connection, actor_name: str) -> Dict[str, Any]:
    global _active_model_version, _active_metrics
    previous = "LOGREG_V1_BASELINE"
    _active_model_version = previous
    _active_metrics = {
        "precision": 0.82,
        "recall": 0.76,
        "f1": 0.79,
        "pr_auc": 0.84,
        "evaluated_on": "Synthetic Historical Benchmark v1"
    }
    return {
        "success": True,
        "message": f"Scoring engine rolled back to baseline {previous} by {actor_name}."
    }
