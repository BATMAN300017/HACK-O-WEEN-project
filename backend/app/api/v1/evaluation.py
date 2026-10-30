"""
Independent Ground-Truth Evaluation API Router (Pipeline B).

Provides:
- Independent validation metrics (Precision, Recall, F1, FPR, PR-AUC).
- Typology-specific recall breakdowns.
- Benchmark matrix comparing SAML-D, NFPC, and India Simulator.
- Automated security audit proving complete label isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional

from app.api.dependencies import get_db
from app.evaluation.evaluator import IndependentEvaluator
from app.evaluation.leakage_guard import LabelLeakageGuard
from app.graph.mule_network_engine import MuleNetworkEngine

router = APIRouter()

@router.get("/benchmark", summary="Get side-by-side benchmark evaluation matrix")
def get_benchmark_matrix(conn=Depends(get_db)):
    """
    Evaluates predictions produced by the unsupervised detection engine
    against protected ground truth stored in Pipeline B.
    """
    return IndependentEvaluator.get_benchmark_comparison_matrix(conn)

@router.get("/audit-isolation", summary="Run automated security audit proving zero label leakage")
def audit_label_isolation(conn=Depends(get_db)):
    """
    Scans detection tables, schemas, and memory to prove that NO ground-truth labels
    are accessible by Pipeline A.
    """
    return LabelLeakageGuard.audit_database_schema(conn)

@router.get("/dataset/{dataset_name}", summary="Evaluate specific dataset performance")
def evaluate_specific_dataset(
    dataset_name: str,
    threshold: float = Query(70.0, description="Risk score threshold for positive prediction"),
    conn=Depends(get_db)
):
    d_upper = dataset_name.upper()
    if d_upper == "NFPC_MULE" or d_upper == "NFPC":
        # Account-level mule evaluation
        graph_engine = MuleNetworkEngine(conn)
        discovered_mules = [m["account_id"] for m in graph_engine.discover_mule_accounts()]
        return IndependentEvaluator.evaluate_account_level(
            conn, dataset_name="NFPC_MULE", discovered_mule_account_ids=discovered_mules
        )
    else:
        # Transaction-level evaluation
        return IndependentEvaluator.evaluate_transaction_level(
            conn, dataset_name=d_upper, risk_threshold=threshold
        )
