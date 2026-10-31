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
    cursor.execute("SELECT COUNT(*) FROM transactions")
    txns_count = cursor.fetchone()[0]
    db_engine = "postgresql" if "Postgres" in type(db).__name__ or hasattr(db, "_conn") else "sqlite"
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": db_ok,
        "database_engine": db_engine,
        "total_transactions_in_db": txns_count,
        "timestamp": utc_now_iso()
    }
