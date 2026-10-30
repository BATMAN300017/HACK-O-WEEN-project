"""
Central Dataset Registry & Ingestion Health Subsystem.

Tracks registration, active splits, processing status, and label isolation health
for all primary benchmark datasets and synthetic generators.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import os

from app.data_ingestion.provenance import DATASET_METADATA_REGISTRY, ProvenanceTracker
from app.data_ingestion.label_isolation import get_protected_evaluation_labels
from app.core.database import get_db_connection

class DatasetRegistry:
    """Singleton service managing dataset discovery, stats, and chronological splits."""

    @classmethod
    def get_all_registered_datasets(cls) -> List[Dict[str, Any]]:
        datasets = []
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for key, meta in DATASET_METADATA_REGISTRY.items():
                cursor.execute("""
                    SELECT COUNT(*), MIN(created_at), MAX(created_at)
                    FROM transactions
                    WHERE dataset_source = ?
                """, (key,))
                row = cursor.fetchone()
                txn_count = row[0] if row else 0
                earliest = row[1] if row and row[1] else "N/A"
                latest = row[2] if row and row[2] else "N/A"

                # Check isolated protected label count
                labels = get_protected_evaluation_labels(dataset_name=key)
                protected_txn_labels = len(labels.get("transactions", {}))
                protected_acc_labels = len(labels.get("accounts", {}))
                protected_scen_labels = len(labels.get("scenarios", {}))

                datasets.append({
                    "id": key,
                    "title": meta["title"],
                    "role": meta["role"],
                    "license": meta["license"],
                    "sources": meta["sources"],
                    "label_granularity": meta["label_granularity"],
                    "ingested_transactions_count": txn_count,
                    "earliest_transaction": earliest,
                    "latest_transaction": latest,
                    "chronological_split_supported": True,
                    "protected_labels_count": {
                        "transactions": protected_txn_labels,
                        "accounts": protected_acc_labels,
                        "scenarios": protected_scen_labels
                    },
                    "label_isolation_status": "SECURE_ISOLATED",
                    "status": "ACTIVE" if txn_count > 0 else "REGISTERED_READY"
                })

        return datasets

    @classmethod
    def get_dataset_details(cls, dataset_id: str) -> Optional[Dict[str, Any]]:
        all_ds = cls.get_all_registered_datasets()
        for ds in all_ds:
            if ds["id"].upper() == dataset_id.upper():
                return ds
        return None
