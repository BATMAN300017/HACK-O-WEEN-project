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
        "version": "1.0",
        "domain": "traditional_banking",
        "sources": [
            "https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml/data",
            "https://huggingface.co/datasets/LordNR/AMLGraphX-SAML-D"
        ],
        "license": "CC BY-SA 4.0 / Open Access Research",
        "description": "Synthetic multi-currency banking dataset with 28 AML typologies and ground-truth laundering labels.",
        "role": "Primary Unsupervised Development & Detection Benchmark",
        "label_granularity": "TRANSACTION_LEVEL",
        "label_definition": "Binary transaction laundering flag (1 = laundering scheme member, 0 = normal)",
        "feature_compatibility": ["traditional_banking_aml", "graph_intelligence", "unsupervised_anomaly"],
        "schema_mapping": {
            "Time": "created_at",
            "Sender_account": "source_account_id",
            "Receiver_account": "destination_account_id",
            "Amount": "amount",
            "Payment_currency": "currency",
            "Payment_type": "transaction_type",
            "Is_laundering": "is_ground_truth_fraud"
        }
    },
    "NFPC_MULE": {
        "title": "NFPC Indian Banking Mule Account Dataset",
        "version": "1.0",
        "domain": "traditional_banking",
        "sources": [
            "https://huggingface.co/datasets/preetisheoran/nfpc-parquet-dataset"
        ],
        "license": "Research and Validation Dataset License",
        "description": "Large-scale Indian banking transactions over a 5-year window with account-level mule labels.",
        "role": "Independent Banking Validation & Scale Testing",
        "label_granularity": "ACCOUNT_LEVEL",
        "label_definition": "Account-level mule disposition (1 = confirmed mule account, 0 = legitimate)",
        "feature_compatibility": ["traditional_banking_aml", "mule_network_analysis", "feedback_learning"],
        "schema_mapping": {
            "transaction_id": "event_id",
            "account_id": "source_account_id",
            "counterparty_id": "destination_account_id",
            "amount": "amount",
            "channel": "payment_channel",
            "transaction_timestamp": "created_at",
            "is_mule": "is_ground_truth_fraud"
        }
    },
    "IBM_AML": {
        "title": "IBM AML-Data: Multi-Bank Synthetic Transaction Feed",
        "version": "1.0",
        "domain": "traditional_banking",
        "sources": [
            "https://github.com/IBM/AML-Data"
        ],
        "license": "Apache-2.0 / Open Access Research",
        "description": "Multi-bank synthetic transaction dataset designed to simulate complex financial crime typologies across institutional boundaries.",
        "role": "Inter-Bank AML Topology & Cross-Institutional Surveillance",
        "label_granularity": "TRANSACTION_LEVEL",
        "label_definition": "Inter-bank laundering indicator (1 = illicit fund flow, 0 = routine transfer)",
        "feature_compatibility": ["traditional_banking_aml", "cross_border_tracing", "graph_intelligence"],
        "schema_mapping": {
            "Timestamp": "created_at",
            "From Account": "source_account_id",
            "To Account": "destination_account_id",
            "Amount Paid": "amount",
            "Payment Currency": "currency",
            "Payment Format": "payment_channel",
            "Is Laundering": "is_ground_truth_fraud"
        }
    },
    "PAYSIM": {
        "title": "PaySim: Synthetic Mobile Money Fraud Dataset",
        "version": "1.0",
        "domain": "mobile_money",
        "sources": [
            "https://www.kaggle.com/datasets/ealaxi/paysim1"
        ],
        "license": "CC BY 4.0 / Open Access Research",
        "description": "Synthetic mobile money simulator based on financial logs from an African mobile financial service, tracking 6.36M transactions.",
        "role": "Mobile Financial Services & Instant Payment Fraud Benchmark",
        "label_granularity": "TRANSACTION_LEVEL",
        "label_definition": "Mobile money payment fraud (isFraud: 1 = unauthorized transfer / cash-out, 0 = legitimate) - NOTE: Mobile money fraud, NOT conventional bank money-laundering",
        "feature_compatibility": ["mobile_money_fraud", "velocity_anomaly", "balance_discrepancy"],
        "schema_mapping": {
            "step": "created_at",
            "type": "transaction_type",
            "amount": "amount",
            "nameOrig": "source_account_id",
            "nameDest": "destination_account_id",
            "isFraud": "is_ground_truth_fraud"
        }
    },
    "ELLIPTIC": {
        "title": "Elliptic Bitcoin Transaction Graph Dataset",
        "version": "1.0",
        "domain": "cryptocurrency",
        "sources": [
            "https://www.kaggle.com/datasets/ellipticco/elliptic-data-set"
        ],
        "license": "CC BY-NC-SA 4.0 / Research License",
        "description": "Graph of 203,769 Bitcoin transactions with 166 anonymized features categorized into licit, illicit (scams, ransomware, darknet), and unknown.",
        "role": "Cryptocurrency On-Chain Forensics & Transaction Graph Intelligence",
        "label_granularity": "TRANSACTION_NODE_LEVEL",
        "label_definition": "On-chain entity classification (class 1 = illicit, class 2 = licit, unknown = unlabelled) - NOTE: Cryptocurrency illicit activity, NOT conventional bank AML",
        "feature_compatibility": ["crypto_graph_intelligence", "topological_clustering", "deanonymization"],
        "schema_mapping": {
            "txId": "event_id",
            "class": "is_ground_truth_fraud",
            "time_step": "created_at"
        }
    },
    "AML_SIM": {
        "title": "IBM AMLSim: Agent-Based AML Typology Simulator",
        "version": "1.0",
        "domain": "synthetic_simulation",
        "sources": [
            "https://github.com/IBM/AMLSim"
        ],
        "license": "Apache-2.0 / Open Source Simulation Tool",
        "description": "Configurable multi-agent simulation framework that generates parameterized laundering topologies (fan-in, fan-out, cycles, scatter-gather).",
        "role": "Dynamic Topology Generation & Controlled Model Stress-Testing",
        "label_granularity": "SCENARIO_AND_TRANSACTION_LEVEL",
        "label_definition": "Synthesized typology membership with scenario metadata, random seed, and execution timestamp",
        "feature_compatibility": ["synthetic_stress_testing", "topology_discovery", "cross_dataset_validation"],
        "schema_mapping": {
            "tran_id": "event_id",
            "orig_acct": "source_account_id",
            "bene_acct": "destination_account_id",
            "base_amt": "amount",
            "timestamp": "created_at",
            "is_sar": "is_ground_truth_fraud"
        }
    },
    "INDIA_SIMULATOR": {
        "title": "SentinelFlow Indian Banking Calibrated Synthetic Generator",
        "version": "1.0",
        "domain": "synthetic_simulation",
        "sources": [
            "https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators",
            "https://www.npci.org.in/product/upi/product-statistics",
            "https://www.npci.org.in/product/imps/product-statistics"
        ],
        "license": "Proprietary / Platform Internal Synthetic Generator",
        "description": "Synthetic transactions calibrated against official RBI & NPCI aggregate volume and value distributions.",
        "role": "Controlled Scenario Testing & Attack Vector Simulation",
        "label_granularity": "SCENARIO_AND_ACCOUNT_LEVEL",
        "label_definition": "Scenario ground truth with attack vector metadata",
        "feature_compatibility": ["traditional_banking_aml", "rbi_npci_benchmarks", "scenario_testing"],
        "schema_mapping": {
            "event_id": "event_id",
            "source_account_id": "source_account_id",
            "destination_account_id": "destination_account_id",
            "amount": "amount",
            "currency": "currency",
            "created_at": "created_at"
        }
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
            "version": meta.get("version", "1.0"),
            "domain": meta.get("domain", "traditional_banking"),
            "sources": meta.get("sources", []),
            "license": meta.get("license", "UNKNOWN"),
            "description": meta.get("description", ""),
            "role": meta.get("role", "VALIDATION"),
            "label_granularity": meta.get("label_granularity", "UNKNOWN"),
            "label_definition": meta.get("label_definition", ""),
            "feature_compatibility": meta.get("feature_compatibility", []),
            "schema_mapping": meta.get("schema_mapping", {}),
            "sha256_hash": file_hash,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
