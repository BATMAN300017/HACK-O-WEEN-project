from fastapi import APIRouter, Depends
import sqlite3
import json
from app.utils.json_utils import safe_json_loads
from app.api.dependencies import get_db
from app.services.analytics_service import get_kpi_summary, get_analytics_trends

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(db: sqlite3.Connection = Depends(get_db)):
    return get_kpi_summary(db)

@router.get("/trends")
def get_dashboard_trends(db: sqlite3.Connection = Depends(get_db)):
    return get_analytics_trends(db)

@router.get("/activity")
def get_recent_activity(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, actor_name, action, resource_type, resource_id, metadata_json, created_at
        FROM audit_events
        ORDER BY created_at DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    activities = []
    for r in rows:
        d = dict(r)
        d["metadata"] = safe_json_loads(d.get("metadata_json"), {})
        activities.append(d)
    return activities
