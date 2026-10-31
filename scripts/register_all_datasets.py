import json
from datetime import datetime, timezone
from app.core.database import get_db_connection

DATASETS_TO_REGISTER = [
    {
        "id": "ds-saml-aml",
        "name": "SAML-D: Synthetic AML Transaction Monitoring Dataset",
        "source": "Kaggle / AMLGraphX",
        "dataset_version": "1.0",
        "domain": "traditional_banking",
        "license": "CC BY-SA 4.0 / Open Access Research",
        "description": "Synthetic multi-currency banking dataset with 28 AML typologies and ground-truth laundering labels.",
        "original_record_count": 25000,
        "source_tag": "SAML_D",
        "schema_mapping": {
            "Time": "created_at",
            "Sender_account": "source_account_id",
            "Receiver_account": "destination_account_id",
            "Amount": "amount",
            "Payment_currency": "currency",
            "Payment_type": "transaction_type",
            "Is_laundering": "is_ground_truth_fraud"
        },
        "feature_compatibility": ["traditional_banking_aml", "graph_intelligence", "unsupervised_anomaly"],
        "class_distribution": {"legitimate": 24729, "laundering": 271}
    },
    {
        "id": "ds-nfpc-mule",
        "name": "NFPC Indian Banking Mule Account Dataset",
        "source": "Hugging Face / preetisheoran",
        "dataset_version": "1.0",
        "domain": "traditional_banking",
        "license": "Academic Research License",
        "description": "1,000,000 real Indian banking transactions, 96,091 labeled accounts, and 2,683 confirmed financial mule entities.",
        "original_record_count": 1000000,
        "source_tag": "NFPC",
        "schema_mapping": {
            "transaction_id": "event_id",
            "account_id": "source_account_id",
            "counterparty_id": "destination_account_id",
            "amount": "amount",
            "channel": "payment_channel",
            "transaction_timestamp": "created_at",
            "is_mule": "is_ground_truth_fraud"
        },
        "feature_compatibility": ["traditional_banking_aml", "mule_network_analysis", "feedback_learning"],
        "class_distribution": {"legitimate_accounts": 93408, "mule_accounts": 2683}
    },
    {
        "id": "ds-ibm-aml",
        "name": "IBM AML-Data: Multi-Bank Synthetic Transaction Feed",
        "source": "IBM Research / GitHub / Kaggle",
        "dataset_version": "1.0",
        "domain": "traditional_banking",
        "license": "Apache-2.0 / CDLA-Sharing-1.0",
        "description": "Inter-bank synthetic transaction feed modeling cross-institutional money laundering schemes.",
        "original_record_count": 180000000,
        "source_tag": "IBM_AML",
        "schema_mapping": {
            "Timestamp": "created_at",
            "From Account": "source_account_id",
            "To Account": "destination_account_id",
            "Amount Paid": "amount",
            "Payment Currency": "currency",
            "Payment Format": "payment_channel",
            "Is Laundering": "is_ground_truth_fraud"
        },
        "feature_compatibility": ["traditional_banking_aml", "cross_border_tracing", "graph_intelligence"],
        "class_distribution": {"normal_ratio": 0.999, "laundering_ratio": 0.001}
    },
    {
        "id": "ds-paysim",
        "name": "PaySim: Synthetic Mobile Money Fraud Dataset",
        "source": "Kaggle / NTNU",
        "dataset_version": "1.0",
        "domain": "mobile_money",
        "license": "CC BY 4.0 / Open Access Research",
        "description": "Mobile financial services simulator modeling unauthorized transfers, cash-in/cash-out balance emptying.",
        "original_record_count": 6362620,
        "source_tag": "PAYSIM",
        "schema_mapping": {
            "step": "created_at",
            "type": "transaction_type",
            "amount": "amount",
            "nameOrig": "source_account_id",
            "nameDest": "destination_account_id",
            "isFraud": "is_ground_truth_fraud"
        },
        "feature_compatibility": ["mobile_money_fraud", "velocity_anomaly", "balance_discrepancy"],
        "class_distribution": {"isFraud_1": 8213, "isFraud_0": 6354407}
    },
    {
        "id": "ds-elliptic",
        "name": "Elliptic Bitcoin Transaction Graph Dataset",
        "source": "Kaggle / Elliptic / MIT",
        "dataset_version": "1.0",
        "domain": "cryptocurrency",
        "license": "CC BY-NC-SA 4.0 / Research License",
        "description": "Cryptocurrency graph of 203,769 Bitcoin transaction nodes and 234,355 directed payment edges with licit/illicit classes.",
        "original_record_count": 203769,
        "source_tag": "ELLIPTIC",
        "schema_mapping": {
            "txId": "event_id",
            "class": "is_ground_truth_fraud",
            "time_step": "created_at"
        },
        "feature_compatibility": ["crypto_graph_intelligence", "topological_clustering", "deanonymization"],
        "class_distribution": {"licit": 42019, "illicit": 4545, "unknown": 157205}
    },
    {
        "id": "ds-amlsim",
        "name": "IBM AMLSim: Agent-Based AML Typology Simulator",
        "source": "IBM Research / AMLSim",
        "dataset_version": "1.0",
        "domain": "synthetic_simulation",
        "license": "Apache-2.0 / Open Source Simulation Tool",
        "description": "Agent-based synthetic AML simulator generating parameterized laundering typologies (Cycle, Fan-Out, Fan-In, Scatter-Gather).",
        "original_record_count": 100000,
        "source_tag": "AML_SIM",
        "schema_mapping": {
            "tran_id": "event_id",
            "orig_acct": "source_account_id",
            "bene_acct": "destination_account_id",
            "base_amt": "amount",
            "timestamp": "created_at",
            "is_sar": "is_ground_truth_fraud"
        },
        "feature_compatibility": ["synthetic_stress_testing", "topology_discovery", "cross_dataset_validation"],
        "class_distribution": {"laundering_scenarios": 4, "typologies": ["CYCLE", "FAN_OUT", "FAN_IN", "SCATTER_GATHER"]}
    },
    {
        "id": "ds-india-sim",
        "name": "SentinelFlow Indian Banking Calibrated Synthetic Generator",
        "source": "RBI DBIE & NPCI Product Statistics",
        "dataset_version": "1.0",
        "domain": "synthetic_simulation",
        "license": "Proprietary / Platform Internal Synthetic Generator",
        "description": "Calibrated micro/macro payment simulation aligned with Reserve Bank of India and NPCI aggregate channel statistics.",
        "original_record_count": 50000,
        "source_tag": "INDIA_SIMULATOR",
        "schema_mapping": {
            "event_id": "event_id",
            "source_account_id": "source_account_id",
            "destination_account_id": "destination_account_id",
            "amount": "amount",
            "currency": "currency",
            "created_at": "created_at"
        },
        "feature_compatibility": ["traditional_banking_aml", "rbi_npci_benchmarks", "scenario_testing"],
        "class_distribution": {"macro_calibrated": True, "channels": ["UPI", "IMPS", "RTGS", "NEFT"]}
    }
]

def register_datasets():
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        for ds in DATASETS_TO_REGISTER:
            ds_id = ds["id"]
            tag = ds["source_tag"]

            # Query real count in transactions
            cur.execute("SELECT COUNT(*) FROM transactions WHERE dataset_source = ? OR (dataset_source = 'NFPC' AND ? = 'NFPC');", (tag, tag))
            r = cur.fetchone()
            count = r['count'] if isinstance(r, dict) else (r[0] if r else 0)

            cur.execute("""
                INSERT INTO datasets (
                    id, name, source, dataset_version, description,
                    original_record_count, imported_record_count, processed_record_count, failed_record_count,
                    status, domain, license,
                    schema_mapping_json, class_distribution_json, feature_compatibility_json, data_quality_json,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, 0,
                    'ACTIVE', ?, ?,
                    ?, ?, ?, '{}',
                    ?, ?
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    source = EXCLUDED.source,
                    dataset_version = EXCLUDED.dataset_version,
                    description = EXCLUDED.description,
                    original_record_count = EXCLUDED.original_record_count,
                    imported_record_count = EXCLUDED.imported_record_count,
                    processed_record_count = EXCLUDED.processed_record_count,
                    status = 'ACTIVE',
                    domain = EXCLUDED.domain,
                    license = EXCLUDED.license,
                    schema_mapping_json = EXCLUDED.schema_mapping_json,
                    class_distribution_json = EXCLUDED.class_distribution_json,
                    feature_compatibility_json = EXCLUDED.feature_compatibility_json,
                    updated_at = EXCLUDED.updated_at;
            """, (
                ds_id, ds["name"], ds["source"], ds["dataset_version"], ds["description"],
                ds["original_record_count"], count, count,
                ds["domain"], ds["license"],
                json.dumps(ds["schema_mapping"]), json.dumps(ds["class_distribution"]), json.dumps(ds["feature_compatibility"]),
                now, now
            ))
            print(f"Registered {ds_id} ({ds['name']}) -> {count} imported transactions.")

        conn.commit()
        
        # Verify total registered datasets
        cur.execute("SELECT id, name, domain, imported_record_count, status FROM datasets ORDER BY id;")
        rows = cur.fetchall()
        print(f"\nTotal registered datasets in Supabase: {len(rows)}")
        for row in rows:
            print(" -", dict(row) if hasattr(row, 'keys') else row)

if __name__ == "__main__":
    register_datasets()
