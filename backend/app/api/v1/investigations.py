from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional
from app.api.dependencies import get_db, get_current_user, require_permission
from app.core.permissions import Permission
from app.repositories.investigation_repository import list_investigations, get_investigation_by_id, create_investigation
from app.repositories.evidence_repository import list_evidence_for_case, create_evidence
from app.schemas.investigation import (
    InvestigationCreate, InvestigationUpdate, InvestigationNoteCreate,
    InvestigationTaskCreate, InvestigationTaskUpdate, DispositionSubmitRequest,
    PeerReviewRequest
)
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate
from app.services.investigation_service import (
    add_investigation_note, complete_investigation_task, submit_case_disposition,
    process_peer_review
)
from app.services.intelligence_service import orchestrate_self_directed_investigation
from app.utils.time import utc_now_iso

router = APIRouter()

@router.get("")
def get_all_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    items, total = list_investigations(db, limit=page_size, offset=offset, status=status, priority=priority)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }

@router.post("")
def post_create_investigation(
    req: InvestigationCreate,
    current_user: dict = Depends(require_permission(Permission.CREATE_INVESTIGATION)),
    db: sqlite3.Connection = Depends(get_db)
):
    inv = create_investigation(db, {
        "title": req.title,
        "summary": req.summary,
        "priority": req.priority,
        "alert_ids": req.alert_ids or [],
        "assigned_investigator_id": current_user["id"]
    })
    return inv

@router.get("/{investigation_id}")
def get_investigation(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    inv = get_investigation_by_id(db, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")
    return inv

@router.patch("/{investigation_id}")
def patch_investigation(
    investigation_id: str,
    req: InvestigationUpdate,
    current_user: dict = Depends(require_permission(Permission.EDIT_INVESTIGATION)),
    db: sqlite3.Connection = Depends(get_db)
):
    fields = []
    params = []
    if req.title:
        fields.append("title = ?")
        params.append(req.title)
    if req.summary:
        fields.append("summary = ?")
        params.append(req.summary)
    if req.priority:
        fields.append("priority = ?")
        params.append(req.priority)
    if req.assigned_investigator_id:
        fields.append("assigned_investigator_id = ?")
        params.append(req.assigned_investigator_id)
    if req.peer_reviewer_id:
        fields.append("peer_reviewer_id = ?")
        params.append(req.peer_reviewer_id)
        
    if not fields:
        return {"message": "No updates specified"}
        
    now = utc_now_iso()
    fields.append("updated_at = ?")
    params.append(now)
    params.append(investigation_id)
    
    cursor = db.cursor()
    cursor.execute(f"UPDATE investigations SET {', '.join(fields)} WHERE id = ?", params)
    return {"success": True, "updated_at": now}

@router.get("/{investigation_id}/evidence")
def get_case_evidence(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    return list_evidence_for_case(db, investigation_id)

@router.post("/{investigation_id}/evidence")
def post_case_evidence(
    investigation_id: str,
    req: EvidenceCreate,
    current_user: dict = Depends(require_permission(Permission.ADD_EVIDENCE)),
    db: sqlite3.Connection = Depends(get_db)
):
    ev = create_evidence(db, {
        "investigation_id": investigation_id,
        "evidence_type": req.evidence_type,
        "source_record_id": req.source_record_id,
        "description": req.description,
        "observed_facts": req.observed_facts,
        "associated_entities": req.associated_entities or [],
        "associated_transactions": req.associated_transactions or [],
        "verification_status": req.verification_status,
        "collector": current_user.get("full_name", "ANALYST")
    })
    return ev

@router.post("/{investigation_id}/notes")
def post_case_note(
    investigation_id: str,
    req: InvestigationNoteCreate,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    return add_investigation_note(db, investigation_id, current_user["id"], req.content, req.is_confidential)

@router.get("/{investigation_id}/notes")
def get_case_notes(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT n.*, u.full_name as author_name
        FROM investigation_notes n
        LEFT JOIN users u ON n.author_id = u.id
        WHERE n.investigation_id = ?
        ORDER BY n.created_at ASC
    """, (investigation_id,))
    return [dict(r) for r in cursor.fetchall()]

@router.get("/{investigation_id}/tasks")
def get_case_tasks(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM investigation_tasks WHERE investigation_id = ? ORDER BY created_at ASC", (investigation_id,))
    return [dict(r) for r in cursor.fetchall()]

@router.patch("/{investigation_id}/tasks/{task_id}")
def patch_case_task(
    investigation_id: str,
    task_id: str,
    req: InvestigationTaskUpdate,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    return complete_investigation_task(db, task_id, current_user.get("full_name", "Investigator"), req.evidence_id)

@router.post("/{investigation_id}/run-analysis")
def post_run_analysis(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    # Trigger self-directed orchestration
    cursor = db.cursor()
    cursor.execute("SELECT alert_id FROM investigation_alerts WHERE investigation_id = ? LIMIT 1", (investigation_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="No associated alert found to trigger analysis")
    return orchestrate_self_directed_investigation(db, row[0])

@router.post("/{investigation_id}/disposition")
def post_case_disposition(
    investigation_id: str,
    req: DispositionSubmitRequest,
    current_user: dict = Depends(require_permission(Permission.SUBMIT_DISPOSITION)),
    db: sqlite3.Connection = Depends(get_db)
):
    return submit_case_disposition(
        db, investigation_id, current_user["id"], current_user.get("full_name", "Investigator"),
        req.disposition, req.rationale, req.requires_peer_review
    )

@router.post("/{investigation_id}/review")
def post_case_peer_review(
    investigation_id: str,
    req: PeerReviewRequest,
    current_user: dict = Depends(require_permission(Permission.APPROVE_DISPOSITION)),
    db: sqlite3.Connection = Depends(get_db)
):
    return process_peer_review(
        db, investigation_id, current_user["id"], current_user.get("full_name", "Senior Investigator"),
        req.action, req.notes
    )

@router.post("/{investigation_id}/reopen")
def post_reopen_case(
    investigation_id: str,
    current_user: dict = Depends(require_permission(Permission.REOPEN_INVESTIGATION)),
    db: sqlite3.Connection = Depends(get_db)
):
    now = utc_now_iso()
    cursor = db.cursor()
    cursor.execute("UPDATE investigations SET status = 'REOPENED', updated_at = ? WHERE id = ?", (now, investigation_id))
    return {"success": True, "status": "REOPENED"}

@router.get("/{investigation_id}/timeline")
def get_case_timeline(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT e.*, u.full_name as actor_name
        FROM investigation_events e
        LEFT JOIN users u ON e.actor_id = u.id
        WHERE e.investigation_id = ?
        ORDER BY e.created_at ASC
    """, (investigation_id,))
    return [dict(r) for r in cursor.fetchall()]
