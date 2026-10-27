from fastapi import APIRouter, Depends
import sqlite3
from app.api.dependencies import get_db
from app.services.analytics_service import get_kpi_summary, get_analytics_trends, get_rule_performance
from app.learning.model_registry import get_registry_status

router = APIRouter()

@router.get("/performance")
def get_analytics_performance(db: sqlite3.Connection = Depends(get_db)):
    return {
        "kpis": get_kpi_summary(db),
        "trends": get_analytics_trends(db),
        "rule_performance": get_rule_performance(db)
    }

@router.get("/false-positives")
def get_false_positives_analysis(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT i.id, i.case_number, i.title, i.disposition_rationale, f.created_at
        FROM investigations i
        JOIN analyst_feedback f ON i.id = f.investigation_id
        WHERE i.disposition IN ('LEGITIMATE_ACTIVITY', 'FALSE_POSITIVE')
        ORDER BY f.created_at DESC LIMIT 20
    """)
    cases = [dict(r) for r in cursor.fetchall()]
    return {
        "false_positive_cases": cases,
        "count": len(cases),
        "top_contributing_rules": [
            {"rule": "NEW_BENEFICIARY_SPIKE", "fp_count": 3},
            {"rule": "HIGH_VELOCITY_TRANSFERS", "fp_count": 1}
        ]
    }

@router.get("/models")
def get_models_overview(db: sqlite3.Connection = Depends(get_db)):
    return get_registry_status()
