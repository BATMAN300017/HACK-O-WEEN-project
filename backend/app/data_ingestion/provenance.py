"""
Dataset Provenance and Lineage Subsystem.

Records exact origin, licensing, cryptographic hashes, and transformation history
for all ingested datasets, ensuring auditability and reproducibility.
"""

import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

DATASET_METADATA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "SAML_D": {
        "title": "SAML-D: Synthetic AML Transaction Monitoring Dataset",
        "sources": [
            "https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml/data",
            "https://huggingface.co/datasets/LordNR/AMLGraphX-SAML-D"
        ],
        "license": "CC BY-SA 4.0 / Open Access Research",
        "description": "Synthetic multi-currency banking dataset with 28 AML typologies and ground-truth laundering labels.",
        "role": "Primary Unsupervised Development & Detection Benchmark",
        "label_granularity": "TRANSACTION_LEVEL"
    },
    "NFPC_MULE": {
        "title": "NFPC Indian Banking Mule Account Dataset",
        "sources": [
            "https://huggingface.co/datasets/preetisheoran/nfpc-parquet-dataset"
        ],
        "license": "Research and Validation Dataset License",
        "description": "Large-scale Indian banking transactions over a 5-year window with account-level mule labels.",
        "role": "Independent Banking Validation & Scale Testing",
        "label_granularity": "ACCOUNT_LEVEL"
    },
    "INDIA_SIMULATOR": {
        "title": "SentinelFlow Indian Banking Calibrated Synthetic Generator",
        "sources": [
            "https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators",
            "https://www.npci.org.in/product/upi/product-statistics",
            "https://www.npci.org.in/product/imps/product-statistics"
        ],
        "license": "Proprietary / Platform Internal Synthetic Generator",
        "description": "Synthetic transactions calibrated against official RBI & NPCI aggregate volume and value distributions.",
        "role": "Controlled Scenario Testing & Attack Vector Simulation",
        "label_granularity": "SCENARIO_AND_ACCOUNT_LEVEL"
    }
}

class ProvenanceTracker:
    """Manages file hashes and ingestion lineage manifests."""

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculates SHA-256 hash of a file for cryptographic reproducibility."""
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"

        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    @classmethod
    def get_lineage_record(cls, dataset_name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Returns the complete provenance profile for a dataset."""
        meta = DATASET_METADATA_REGISTRY.get(dataset_name.upper(), {})
        file_hash = cls.calculate_file_hash(file_path) if file_path else "SYNTHETIC_IN_MEMORY"

        return {
            "dataset_name": dataset_name,
            "title": meta.get("title", dataset_name),
            "sources": meta.get("sources", []),
            "license": meta.get("license", "UNKNOWN"),
            "description": meta.get("description", ""),
            "role": meta.get("role", "VALIDATION"),
            "label_granularity": meta.get("label_granularity", "UNKNOWN"),
            "sha256_hash": file_hash,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
