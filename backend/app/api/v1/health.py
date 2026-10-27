from fastapi import APIRouter, Depends
import sqlite3
from app.api.dependencies import get_db
from app.core.config import settings
from app.utils.time import utc_now_iso

router = APIRouter()

@router.get("/health")
def health_check(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT 1")
    db_ok = cursor.fetchone()[0] == 1
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": db_ok,
        "timestamp": utc_now_iso()
    }
