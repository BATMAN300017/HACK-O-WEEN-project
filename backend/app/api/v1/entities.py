from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional
from app.api.dependencies import get_db
from app.repositories.entity_repository import get_entity_profile

router = APIRouter()

@router.get("")
def list_entities(
    query: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 50,
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    entities = []
    
    # Customers
    cursor.execute("SELECT id, customer_ref, full_name, risk_tier FROM customers LIMIT ?", (limit,))
    for r in cursor.fetchall():
        entities.append({
            "id": r["id"],
            "type": "CUSTOMER",
            "identifier": r["customer_ref"],
            "label": r["full_name"],
            "risk_tier": r["risk_tier"]
        })
        
    # Accounts
    cursor.execute("SELECT id, account_number, account_type, is_dormant FROM accounts LIMIT ?", (limit,))
    for r in cursor.fetchall():
        entities.append({
            "id": r["id"],
            "type": "ACCOUNT",
            "identifier": r["account_number"],
            "label": f"Account {r['account_number']}",
            "risk_tier": "HIGH" if r["is_dormant"] else "LOW"
        })
        
    if query:
        q_low = query.lower()
        entities = [e for e in entities if q_low in e["label"].lower() or q_low in e["identifier"].lower()]
        
    return entities

@router.get("/{entity_id}")
def get_entity(entity_id: str, db: sqlite3.Connection = Depends(get_db)):
    prof = get_entity_profile(db, entity_id)
    if not prof:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return prof

@router.get("/{entity_id}/transactions")
def get_entity_transactions(entity_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        WHERE source_account_id = ? OR destination_account_id = ? OR customer_id = ?
        ORDER BY created_at DESC LIMIT 50
    """, (entity_id, entity_id, entity_id))
    return [dict(r) for r in cursor.fetchall()]

@router.get("/{entity_id}/investigations")
def get_entity_investigations(entity_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT i.*
        FROM investigations i
        JOIN investigation_alerts ia ON i.id = ia.investigation_id
        JOIN alerts a ON ia.alert_id = a.id
        WHERE a.account_id = ? OR a.customer_id = ?
        ORDER BY i.created_at DESC
    """, (entity_id, entity_id))
    return [dict(r) for r in cursor.fetchall()]
