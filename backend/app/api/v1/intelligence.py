from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
from app.api.dependencies import get_db
from app.services.intelligence_service import run_investigation_copilot_query, orchestrate_self_directed_investigation

router = APIRouter()

class CopilotQueryRequest(BaseModel):
    investigation_id: str
    query: str

class AnalysisTriggerRequest(BaseModel):
    alert_id: str

@router.post("/copilot")
def post_copilot_query(req: CopilotQueryRequest, db: sqlite3.Connection = Depends(get_db)):
    return run_investigation_copilot_query(db, req.investigation_id, req.query)

@router.post("/analyze")
def post_trigger_analysis(req: AnalysisTriggerRequest, db: sqlite3.Connection = Depends(get_db)):
    return orchestrate_self_directed_investigation(db, req.alert_id)

@router.post("/recommendations")
def post_get_recommendations(req: CopilotQueryRequest, db: sqlite3.Connection = Depends(get_db)):
    return run_investigation_copilot_query(db, req.investigation_id, "What should I investigate next?")
