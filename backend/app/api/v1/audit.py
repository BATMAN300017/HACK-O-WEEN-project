from fastapi import APIRouter, Depends, Query
import sqlite3
import json
from typing import Optional
from app.api.dependencies import get_db, require_permission
from app.core.permissions import Permission

router = APIRouter()

@router.get("")
def get_audit_trail(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT)),
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    cursor = db.cursor()
    query = "SELECT * FROM audit_events WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM audit_events WHERE 1=1"
    params = []
    
    if action:
        query += " AND action = ?"
        count_query += " AND action = ?"
        params.append(action)
    if resource_type:
        query += " AND resource_type = ?"
        count_query += " AND resource_type = ?"
        params.append(resource_type)
        
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    cursor.execute(query, params)
    events = []
    for r in cursor.fetchall():
        d = dict(r)
        d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        events.append(d)
        
    return {
        "items": events,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }
