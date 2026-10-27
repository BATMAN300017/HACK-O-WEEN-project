from fastapi import APIRouter, Depends, HTTPException
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
