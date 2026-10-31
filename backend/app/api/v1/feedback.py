from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import sqlite3
from app.api.dependencies import get_db, get_current_user, require_permission
from app.core.permissions import Permission
from app.repositories.feedback_repository import get_feedback_summary, record_feedback
from app.schemas.feedback import FeedbackSubmitRequest
from app.services.learning_service import (
    get_complete_learning_status, execute_candidate_training,
    execute_model_promotion, execute_model_rollback
)
from app.learning.dataset_builder import build_training_dataset
from app.learning.label_policy import evaluate_disposition_label

router = APIRouter()

@router.post("")
def post_submit_feedback(
    req: FeedbackSubmitRequest,
    current_user: dict = Depends(require_permission(Permission.SUBMIT_DISPOSITION)),
    db: sqlite3.Connection = Depends(get_db)
):
    is_eligible, label_val, reason = evaluate_disposition_label(req.disposition)
    fb = record_feedback(db, {
        "investigation_id": req.investigation_id,
        "analyst_id": current_user["id"],
        "disposition": req.disposition,
        "rationale": req.rationale,
        "evidence_reviewed_count": 4,
        "is_eligible_for_training": 1 if is_eligible else 0,
        "training_label": label_val,
        "exclusion_reason": reason
    })
    return fb

@router.get("/summary")
def get_feedback_overview(db: sqlite3.Connection = Depends(get_db)):
    return get_feedback_summary(db)

@router.get("/status")
def get_learning_status(db: sqlite3.Connection = Depends(get_db)):
    return get_complete_learning_status(db)

@router.post("/prepare-dataset")
def post_prepare_dataset(db: sqlite3.Connection = Depends(get_db)):
    return build_training_dataset(db)

@router.post("/train-candidate")
def post_train_candidate(
    current_user: dict = Depends(require_permission(Permission.TRAIN_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    return execute_candidate_training(db, current_user.get("full_name", "Senior Analyst"))

from pydantic import BaseModel
from app.learning.promotion_service import ModelPromotionService

class PolicyUpdateRequest(BaseModel):
    mode: Optional[str] = "MANUAL"
    min_precision: Optional[float] = 0.70
    min_recall: Optional[float] = 0.65
    min_pr_auc: Optional[float] = 0.75
    max_fpr: Optional[float] = 0.05
    min_f1: Optional[float] = 0.70
    require_independent_validation: Optional[bool] = True
    min_evaluation_samples: Optional[int] = 20
    is_active: Optional[bool] = True

class ModelApprovalRequest(BaseModel):
    rationale: Optional[str] = "Approved by authorized analyst after evaluation review"

class ModelRetireRequest(BaseModel):
    reason: Optional[str] = "Model retired from production scoring"

@router.get("/promotion-policy", summary="Get model promotion policy configuration")
def get_promotion_policy(db: sqlite3.Connection = Depends(get_db)):
    return ModelPromotionService.get_promotion_policy(db)

@router.put("/promotion-policy", summary="Update model promotion policy (Manual or Automatic with thresholds)")
def update_promotion_policy(
    req: PolicyUpdateRequest,
    current_user: dict = Depends(require_permission(Permission.PROMOTE_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    actor = current_user.get("full_name") or current_user.get("username", "Admin")
    return ModelPromotionService.update_promotion_policy(db, req.model_dump(), actor)

@router.get("/models", summary="List all models with lifecycle status")
def list_models(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, model_name, version, is_active, status, approval_status,
               approved_by, approved_at, promoted_by, promoted_at,
               evaluation_metrics_json, created_at
        FROM model_versions
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    models = []
    for r in rows:
        d = dict(r) if hasattr(r, "keys") else {
            "id": r[0], "model_name": r[1], "version": r[2], "is_active": bool(r[3]),
            "status": r[4], "approval_status": r[5] if len(r) > 5 else "APPROVED",
            "approved_by": r[6] if len(r) > 6 else None, "approved_at": str(r[7]) if len(r) > 7 and r[7] else None,
            "promoted_by": r[8] if len(r) > 8 else None, "promoted_at": str(r[9]) if len(r) > 9 and r[9] else None,
            "evaluation_metrics": safe_json_loads(r[10], {}) if len(r) > 10 else {}, "created_at": str(r[11]) if len(r) > 11 else ""
        }
        models.append(d)
    return models

@router.post("/models/{model_version}/approve", summary="Manually approve evaluated model")
def approve_model(
    model_version: str,
    req: ModelApprovalRequest = ModelApprovalRequest(),
    current_user: dict = Depends(require_permission(Permission.PROMOTE_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    actor = current_user.get("full_name") or current_user.get("username", "Senior Analyst")
    return ModelPromotionService.approve_model_manually(db, model_version, actor, req.rationale)

@router.post("/models/{model_version}/activate", summary="Activate approved model for operational scoring")
def activate_model(
    model_version: str,
    current_user: dict = Depends(require_permission(Permission.PROMOTE_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    actor = current_user.get("full_name") or current_user.get("username", "Fraud Admin")
    return ModelPromotionService.activate_model(db, model_version, actor)

@router.post("/models/{model_version}/retire", summary="Retire model from production scoring")
def retire_model(
    model_version: str,
    req: ModelRetireRequest = ModelRetireRequest(),
    current_user: dict = Depends(require_permission(Permission.PROMOTE_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    actor = current_user.get("full_name") or current_user.get("username", "Admin")
    return ModelPromotionService.retire_model(db, model_version, actor, req.reason)

@router.get("/promotion-audit", summary="Get model promotion and approval audit history")
def get_promotion_audit(limit: int = Query(50, ge=1, le=200), db: sqlite3.Connection = Depends(get_db)):
    return ModelPromotionService.get_promotion_audit_trail(db, limit)

@router.post("/promote-candidate")
def post_promote_candidate(
    current_user: dict = Depends(require_permission(Permission.PROMOTE_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    return execute_model_promotion(db, current_user.get("full_name", "Fraud Ops Admin"))

@router.post("/rollback")
def post_rollback_model(
    current_user: dict = Depends(require_permission(Permission.ROLLBACK_MODEL)),
    db: sqlite3.Connection = Depends(get_db)
):
    return execute_model_rollback(db, current_user.get("full_name", "Fraud Ops Admin"))


@router.get("/labeled-transactions", summary="Fetch Dataset 2 labeled transactions for feedback learning")
def get_labeled_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    label_filter: Optional[str] = None, # SCAM, LEGIT, or ALL
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    query = """
        SELECT f.id, f.investigation_id, f.disposition, f.rationale,
               f.is_eligible_for_training, f.training_label, f.created_at,
               i.case_number, i.title, i.priority
        FROM analyst_feedback f
        LEFT JOIN investigations i ON f.investigation_id = i.id
        WHERE 1=1
    """
    params = []
    if label_filter == "SCAM":
        query += " AND f.training_label = 1"
    elif label_filter == "LEGIT":
        query += " AND f.training_label = 0"

    cursor = db.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
    total = cursor.fetchone()[0]

    query += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size
    }
