from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3
from typing import Optional
from app.api.dependencies import get_db
from app.repositories.transaction_repository import list_transactions, get_transaction_by_id
from app.detection.engine import score_transaction
from app.graph.builder import build_investigation_subgraph

router = APIRouter()

@router.get("")
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_band: Optional[str] = None,
    account_id: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * page_size
    items, total = list_transactions(db, limit=page_size, offset=offset, risk_band=risk_band, account_id=account_id)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1
    }

@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return txn

@router.get("/{transaction_id}/risk")
def get_transaction_risk_analysis(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    res = score_transaction(db, txn)
    return {
        "transaction_id": txn["id"],
        **res
    }

@router.get("/{transaction_id}/relationships")
def get_transaction_relationships(transaction_id: str, db: sqlite3.Connection = Depends(get_db)):
    txn = get_transaction_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    accounts = [txn["source_account_id"]]
    if txn.get("destination_account_id"):
        accounts.append(txn["destination_account_id"])
    return build_investigation_subgraph(db, accounts, max_hops=1)
