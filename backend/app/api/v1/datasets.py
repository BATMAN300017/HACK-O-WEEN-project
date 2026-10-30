"""
Dataset Management API Router.

Endpoints for:
- Listing registered datasets (SAML-D, NFPC, India Simulator).
- Triggering batch ingestion with automatic label isolation.
- Generating calibrated Indian banking transactions using RBI/NPCI aggregate statistics.
- Inspecting raw dataset schemas and testing label isolation.
- Viewing public aggregate payment benchmarks.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.data_ingestion.dataset_registry import DatasetRegistry
from app.data_ingestion.provenance import ProvenanceTracker
from app.data_ingestion.rbi_npci_statistics import get_channel_benchmarks
from app.data_ingestion.schema_inspector import SchemaInspector
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.batch_loader import BatchLoader
from app.data_ingestion.india_simulator import IndiaBankingSimulator
from app.core.logging import logger

router = APIRouter()

class IngestionRequest(BaseModel):
    dataset_name: str  # SAML_D, NFPC_MULE, or INDIA_SIMULATOR
    source_path: Optional[str] = None
    max_records: Optional[int] = 500

class IndiaSimulationRequest(BaseModel):
    num_customers: int = 50
    num_accounts: int = 80
    num_normal_txns: int = 250
    include_scenarios: bool = True

class SchemaInspectRequest(BaseModel):
    file_path: str
    sample_rows: int = 100

@router.get("", summary="List all registered datasets and their status")
def list_datasets():
    """Returns registration metadata, transaction counts, and label isolation health."""
    return DatasetRegistry.get_all_registered_datasets()

@router.get("/rbi-npci-benchmarks", summary="Retrieve official RBI & NPCI aggregate payment indicators")
def get_rbi_npci_benchmarks():
    """Returns official calibrated macro payment benchmarks used to parameterize Indian simulations."""
    return {
        "status": "CALIBRATED_BENCHMARKS_ACTIVE",
        "description": "Macro payment indicators from RBI Database on Indian Economy & NPCI product statistics.",
        "benchmarks": get_channel_benchmarks()
    }

@router.get("/{dataset_id}", summary="Get detailed provenance and schema for a dataset")
def get_dataset(dataset_id: str):
    details = DatasetRegistry.get_dataset_details(dataset_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    lineage = ProvenanceTracker.get_lineage_record(dataset_id)
    return {**details, "lineage": lineage}

@router.post("/inspect-schema", summary="Deep inspect raw file schema and label isolation")
def inspect_dataset_schema(req: SchemaInspectRequest):
    return SchemaInspector.inspect_file(req.file_path, req.sample_rows)

@router.post("/ingest", summary="Stream and ingest dataset with strict label isolation")
def ingest_dataset_batch(req: IngestionRequest):
    """
    Ingests records in chunked batches:
    - Strips all ground-truth labels and stores them in protected store.
    - Persists label-free normalized records to detection database.
    """
    d_name = req.dataset_name.upper()
    if d_name == "SAML_D":
        adapter = SamlDAdapter(batch_size=req.max_records or 500)
        source = req.source_path or "data/saml_d/saml_d_sample.csv"
    elif d_name in ("NFPC", "NFPC_MULE"):
        adapter = NfpcAdapter(batch_size=req.max_records or 500)
        source = req.source_path or "data/nfpc/nfpc_sample.parquet"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported dataset adapter: {req.dataset_name}")

    loader = BatchLoader(adapter=adapter, batch_size=req.max_records or 500)
    result = loader.ingest_from_source(source_path=source, max_records=req.max_records)
    return result

@router.post("/simulate-india", summary="Generate calibrated Indian banking transactions and scenarios")
def simulate_india_ecosystem(req: IndiaSimulationRequest, conn=Depends(get_db)):
    """
    Generates realistic Indian transactions calibrated with RBI/NPCI distributions:
    - Normal banking flows (salary, utilities, merchant UPI, ATM).
    - 5 complex coordinated scenarios (Mule chain, International layering, Circular cycle, Lookalikes).
    - Writes ground truth strictly to protected store.
    """
    simulator = IndiaBankingSimulator()
    ecosystem = simulator.generate_synthetic_ecosystem(
        num_customers=req.num_customers,
        num_accounts=req.num_accounts,
        num_normal_txns=req.num_normal_txns,
        include_scenarios=req.include_scenarios
    )

    # Persist accounts and transactions into database
    cursor = conn.cursor()
    for cust in ecosystem["customers"]:
        cursor.execute("""
            INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cust["id"], cust["customer_ref"], cust["full_name"], cust.get("email", f"{cust['id']}@bank.in"), cust["risk_tier"], cust["kyc_status"], cust["created_at"]))

    for acc in ecosystem["accounts"]:
        cursor.execute("""
            INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, is_dormant, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (acc["id"], acc["account_number"], acc["customer_id"], acc["currency"], acc["balance"], acc["is_dormant"], acc["created_at"]))

    for txn in ecosystem["transactions"]:
        cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                id, event_id, source_account_id, destination_account_id, customer_id,
                amount, currency, transaction_type, payment_channel, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn["id"], txn["event_id"], txn["source_account_id"],
            txn.get("destination_account_id"), f"CUST-{txn['source_account_id']}",
            txn["amount"], txn["currency"], txn.get("payment_type", "TRANSFER"),
            txn.get("payment_channel", "TRANSFER"), txn.get("status", "COMPLETED"),
            txn["created_at"]
        ))
    conn.commit()

    return {
        "status": "SIMULATION_GENERATED_AND_PERSISTED",
        "dataset_name": "INDIA_SIMULATOR",
        "total_transactions_generated": len(ecosystem["transactions"]),
        "total_accounts_created": len(ecosystem["accounts"]),
        "total_customers_created": len(ecosystem["customers"]),
        "scenarios_injected": ecosystem["scenarios_injected"],
        "isolation_status": "PROTECTED_GROUND_TRUTH_STORED_IN_PIPELINE_B"
    }
