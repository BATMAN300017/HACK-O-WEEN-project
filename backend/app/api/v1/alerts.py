from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional
from app.api.dependencies import get_db, get_current_user, require_permission
from app.core.permissions import Permission
from app.repositories.alert_repository import list_alerts, get_alert_by_id
from app.schemas.alert import AlertAssignRequest, AlertTriageRequest, AlertDismissRequest, AlertInvestigateRequest
from app.services.alert_service import assign_alert, triage_alert, dismiss_alert, convert_alert_to_investigation

router = APIRouter()

@router.get("")
def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    items, total = list_alerts(db, limit=page_size, offset=offset, severity=severity, status=status)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }

@router.get("/{alert_id}")
def get_alert(alert_id: str, db: sqlite3.Connection = Depends(get_db)):
    alt = get_alert_by_id(db, alert_id)
    if not alt:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alt

@router.post("/{alert_id}/assign")
def post_assign_alert(
    alert_id: str,
    req: AlertAssignRequest,
    current_user: dict = Depends(require_permission(Permission.TRIAGE_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return assign_alert(db, alert_id, req.user_id, current_user.get("full_name", "Investigator"))

@router.post("/{alert_id}/triage")
def post_triage_alert(
    alert_id: str,
    req: AlertTriageRequest,
    current_user: dict = Depends(require_permission(Permission.TRIAGE_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return triage_alert(db, alert_id, req.severity, req.notes, current_user.get("full_name", "Investigator"))

@router.post("/{alert_id}/dismiss")
def post_dismiss_alert(
    alert_id: str,
    req: AlertDismissRequest,
    current_user: dict = Depends(require_permission(Permission.DISMISS_ALERT)),
    db: sqlite3.Connection = Depends(get_db)
):
    return dismiss_alert(db, alert_id, req.reason, current_user.get("full_name", "Investigator"))

from app.services.route_map_service import get_scam_and_route_dossier

@router.get("/{alert_id}/scam-dossier")
def get_alert_scam_dossier(alert_id: str, db: sqlite3.Connection = Depends(get_db)):
    dossier = get_scam_and_route_dossier(db, alert_id=alert_id)
    if "error" in dossier:
        raise HTTPException(status_code=404, detail=dossier["error"])
    return dossier

@router.post("/{alert_id}/investigate")
def post_convert_investigation(
    alert_id: str,
    current_user: dict = Depends(require_permission(Permission.CREATE_INVESTIGATION)),
    db: sqlite3.Connection = Depends(get_db)
):
    res = convert_alert_to_investigation(db, alert_id, current_user.get("full_name", "Investigator"))
    # Attach rich scam dossier and interactive transaction route map
    dossier = get_scam_and_route_dossier(db, investigation_id=res.get("investigation_id"), alert_id=alert_id)
    return {**res, "scam_dossier": dossier}
