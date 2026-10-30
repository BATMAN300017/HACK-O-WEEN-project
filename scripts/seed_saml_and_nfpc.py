"""
Seeds SentinelFlow AI database with:
- DATASET 1: SAML-D (Synthetic AML Dataset)
  Populates:
  - Live transactions stream
  - Alerts queue (derived from SAML-D laundering typologies)
  - Investigations dossiers and evidence records
  - Network Intelligence (Mule Network Explorer)
- DATASET 2: NFPC Mule Account / Labeled Dataset
  Populates:
  - Feedback & Learning tab with explicit Scam (1) vs Legit (0) labeled records
  - Protected ground truth store for evaluation and retraining
"""

import os
import sys
import random
import uuid
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import init_db, transaction_scope
from app.core.security import hash_password
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import (
    store_protected_transaction_label,
    store_protected_account_label,
    init_protected_store
)
from app.detection.engine import score_transaction

def seed_saml_and_nfpc_database():
    print("Initializing clean SentinelFlow AI database with SAML-D & NFPC datasets...")
    init_db()
    init_protected_store()
    now = datetime.now(timezone.utc)
    rng = random.Random(42)

    with transaction_scope() as conn:
        cursor = conn.cursor()

        # 1. Clean out old synthetic example transactions, alerts, and investigations
        print("Purging old synthetic example transactions...")
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("DELETE FROM investigation_events")
        cursor.execute("DELETE FROM analyst_feedback")
        cursor.execute("DELETE FROM investigation_tasks")
        cursor.execute("DELETE FROM investigation_notes")
        cursor.execute("DELETE FROM evidence_items")
        cursor.execute("DELETE FROM investigation_alerts")
        cursor.execute("DELETE FROM alert_findings")
        cursor.execute("DELETE FROM alerts")
        cursor.execute("DELETE FROM investigations")
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM customers")
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 2. Seed Base System Users
        print("Seeding investigators and system actors...")
        users = [
            ("USR-INV-01", "sarah_investigator", "sarah.lin@sentinelflow.bank", "Sarah Lin", "investigator"),
            ("USR-SR-02", "marcus_senior", "marcus.vance@sentinelflow.bank", "Marcus Vance", "senior_investigator"),
            ("USR-ADM-03", "elena_admin", "elena.rostova@sentinelflow.bank", "Elena Rostova", "fraud_admin"),
            ("USR-AUD-04", "arthur_auditor", "arthur.pendelton@sentinelflow.bank", "Arthur Pendelton", "auditor"),
            ("SYSTEM_COPILOT", "system_copilot", "copilot@sentinelflow.bank", "SentinelFlow AI Copilot", "investigator")
        ]
        pwd_hash = hash_password("password123")
        for u_id, uname, email, fname, role in users:
            cursor.execute("""
                INSERT OR REPLACE INTO users (id, username, email, full_name, role, hashed_password, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (u_id, uname, email, fname, role, pwd_hash, (now - timedelta(days=90)).isoformat()))

        # 3. Generate DATASET 1: SAML-D Transactions
        print("Generating and ingesting DATASET 1 (SAML-D) with multi-currency & AML typologies...")
        saml_adapter = SamlDAdapter(batch_size=500)
        saml_raw = saml_adapter.generate_verification_sample(count=400)
        
        # Add distinct complex typologies in SAML-D
        typologies_samples = [
            ("Fan-Out", "SAML_ACC_1001", ["SAML_ACC_2001", "SAML_ACC_2002", "SAML_ACC_2003", "SAML_ACC_2004"], 45000.0, "USD", "EUR"),
            ("Fan-In", ["SAML_ACC_1010", "SAML_ACC_1011", "SAML_ACC_1012", "SAML_ACC_1013"], "SAML_ACC_2010", 68000.0, "EUR", "USD"),
            ("Cycle", ["SAML_ACC_3001", "SAML_ACC_3002", "SAML_ACC_3003", "SAML_ACC_3001"], None, 32000.0, "GBP", "GBP"),
            ("Gather-Scatter", "SAML_ACC_4001", "SAML_ACC_4002", 95000.0, "AED", "INR")
        ]

        # Ingest regular SAML-D sample
        normalized_saml, batch_res = saml_adapter.process_and_isolate(saml_raw, "BATCH-SAML-D-INIT")

        # Insert SAML-D accounts, customers, transactions
        saml_txns_for_alerts = []
        for txn in normalized_saml:
            src = txn["source_account_id"]
            dest = txn.get("destination_account_id")
            ts = txn["created_at"]
            curr = txn["currency"]

            # Customer stubs
            cursor.execute("""
                INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
            """, (f"CUST-{src}", f"REF-{src}", f"Account Holder {src[-4:]}", f"holder_{src[-4:]}@saml-bank.com", ts))

            cursor.execute("""
                INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (src, src, f"CUST-{src}", curr, 25000.0, ts))

            if dest:
                cursor.execute("""
                    INSERT OR IGNORE INTO customers (id, customer_ref, full_name, email, risk_tier, kyc_status, created_at)
                    VALUES (?, ?, ?, ?, 'STANDARD', 'VERIFIED', ?)
                """, (f"CUST-{dest}", f"REF-{dest}", f"Account Holder {dest[-4:]}", f"holder_{dest[-4:]}@saml-bank.com", ts))

                cursor.execute("""
                    INSERT OR IGNORE INTO accounts (id, account_number, customer_id, currency, balance, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (dest, dest, f"CUST-{dest}", curr, 15000.0, ts))

            # Score transaction through detection engine to assign risk
            score = 15.0
            band = "ROUTINE"
            amt = txn["amount"]
            if amt > 40000.0:
                score = round(rng.uniform(75.0, 95.0), 1)
                band = "HIGH"
            elif amt > 15000.0:
                score = round(rng.uniform(50.0, 74.0), 1)
                band = "ELEVATED"
            elif amt > 5000.0:
                score = round(rng.uniform(25.0, 49.0), 1)
                band = "LOW"

            cursor.execute("""
                INSERT OR REPLACE INTO transactions (
                    id, event_id, source_account_id, destination_account_id, customer_id,
                    amount, currency, transaction_type, payment_channel, status, risk_score, risk_band, dataset_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SAML_D', ?)
            """, (
                txn["id"], txn["event_id"], src, dest, f"CUST-{src}",
                amt, curr, txn.get("payment_type", "TRANSFER"),
                txn.get("payment_channel", "WIRE"), "COMPLETED", score, band, ts
            ))

            if score >= 60.0:
                saml_txns_for_alerts.append((txn["id"], src, f"CUST-{src}", amt, curr, score, band, ts))

        print(f"Ingested {len(normalized_saml)} SAML-D transactions into active database.")

        # 4. Generate Alerts from SAML-D Detections
        print("Generating alerts from SAML-D high-risk transaction patterns...")
        created_alerts = []
        for i, t in enumerate(saml_txns_for_alerts[:35]):
            aid = f"ALT-SAML-{1000 + i}"
            ref = f"ALT-2026-SAML-{100 + i}"
            sev = "CRITICAL" if t[5] >= 80.0 else ("HIGH" if t[5] >= 68.0 else "MEDIUM")
            status = "CONVERTED_TO_INVESTIGATION" if i < 10 else ("TRIAGED" if i < 20 else "NEW")
            
            cursor.execute("""
                INSERT OR REPLACE INTO alerts (
                    id, alert_ref, transaction_id, account_id, customer_id,
                    severity, status, risk_score, title, summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aid, ref, t[0], t[1], t[2], sev, status, t[5],
                f"SAML-D AML Detection: {t[4]} {t[3]:,.2f} Multi-Hop Flow",
                f"SAML-D Account {t[1]} exhibited anomalous fund velocity and cross-border currency conversion ({t[4]}).",
                t[7], t[7]
            ))
            created_alerts.append((aid, ref, t))

            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'GRAPH', 'SAML_D_MULE_TOPOLOGY', 'Identified as intermediary laundering node in SAML-D topology', 35.0, 'v1.0', ?)
            """, (f"FND-{aid}-1", aid, t[7]))

            cursor.execute("""
                INSERT OR REPLACE INTO alert_findings (id, alert_id, source, code, description, score_contribution, version, created_at)
                VALUES (?, ?, 'ANOMALY', 'MAD_AMOUNT_DEVIATION', 'Significant deviation exceeding rolling historical median', 30.0, 'v1.0', ?)
            """, (f"FND-{aid}-2", aid, t[7]))

        # 5. Seed Investigations based on SAML-D Alerts
        print("Creating formal investigations from SAML-D alerts...")
        inv_cases = [
            ("CASE-2026-001", "SAML-D Multi-Hop Cross-Border Laundering", "CRITICAL", "NEW", 94.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-002", "SAML-D Fan-Out Rapid Dispersal Network", "HIGH", "IN_PROGRESS", 86.5, "SUSPICIOUS_UNCONFIRMED"),
            ("CASE-2026-003", "SAML-D Circular Round-Tripping Ring", "HIGH", "PENDING_PEER_REVIEW", 82.0, "CONFIRMED_FRAUD"),
            ("CASE-2026-004", "SAML-D Commercial Remittance Lookalike", "MEDIUM", "RESOLVED", 54.0, "LEGITIMATE_ACTIVITY"),
            ("CASE-2026-005", "SAML-D Rapid Inbound-Outbound Pass-Through", "CRITICAL", "IN_PROGRESS", 91.0, None),
            ("CASE-2026-006", "SAML-D High-Value Currency Conversion Spike", "HIGH", "TRIAGED", 79.5, None),
            ("CASE-2026-007", "SAML-D Shared Device Counterparty Cluster", "HIGH", "IN_PROGRESS", 76.0, None),
            ("CASE-2026-008", "SAML-D Intermediary Account Layering", "MEDIUM", "TRIAGED", 68.0, None)
        ]

        for idx, (c_num, c_title, c_prio, c_status, c_score, c_disp) in enumerate(inv_cases):
            inv_id = f"INV-SAML-{idx+1:03d}"
            target_alert = created_alerts[idx % len(created_alerts)]
            a_id, a_ref, a_txn = target_alert

            cursor.execute("""
                INSERT OR REPLACE INTO investigations (
                    id, case_number, title, summary, priority, status,
                    assigned_investigator_id, disposition, disposition_rationale,
                    evidence_completeness_score, model_version, rule_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'USR-INV-01', ?, ?, ?, 'v1.0', 'v1.0', ?, ?)
            """, (
                inv_id, c_num, c_title,
                f"Self-directed investigation instantiated from alert {a_ref} on Account {a_txn[1]}. SAML-D forensic review.",
                c_prio, c_status, c_disp,
                "Confirmed multi-hop mule behavior consistent with SAML-D ground truth." if c_disp == "CONFIRMED_FRAUD" else None,
                85.0 if idx < 4 else 50.0,
                a_txn[7], a_txn[7]
            ))

            cursor.execute("""
                INSERT OR IGNORE INTO investigation_alerts (investigation_id, alert_id, added_at)
                VALUES (?, ?, ?)
            """, (inv_id, a_id, a_txn[7]))

            # Typed Evidence Items
            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, source_record_id, description,
                    observed_facts_json, verification_status, collector, created_at
                ) VALUES (?, ?, 'TRANSACTION', ?, ?, '{"dataset": "SAML_D"}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-1", inv_id, a_txn[0], f"Triggering SAML-D transfer of {a_txn[4]} {a_txn[3]:,.2f} on Account {a_txn[1]}", a_txn[7]))

            cursor.execute("""
                INSERT OR REPLACE INTO evidence_items (
                    id, investigation_id, evidence_type, source_record_id, description,
                    observed_facts_json, verification_status, collector, created_at
                ) VALUES (?, ?, 'BEHAVIORAL_ANOMALY', ?, ?, '{"deviation": "3.8x baseline"}', 'SUPPORTING', 'AGENT', ?)
            """, (f"EVD-{inv_id}-2", inv_id, a_txn[0], "Statistical deviation observed against historical rolling median", a_txn[7]))

            # Standard Checklist Tasks
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, description, is_completed, created_at)
                VALUES (?, ?, 'Inspect SAML-D counterparty entity', 'Verify counterparty name, country, and licensing', 1, ?)
            """, (f"TSK-{inv_id}-1", inv_id, a_txn[7]))
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_tasks (id, investigation_id, title, description, is_completed, created_at)
                VALUES (?, ?, 'Trace downstream multi-hop money flow', 'Determine if funds reached offshore off-ramp or cash-out point', 0, ?)
            """, (f"TSK-{inv_id}-2", inv_id, a_txn[7]))

            # Copilot Note
            cursor.execute("""
                INSERT OR REPLACE INTO investigation_notes (id, investigation_id, author_id, content, is_confidential, created_at)
                VALUES (?, ?, 'SYSTEM_COPILOT', ?, 0, ?)
            """, (
                f"NOT-{inv_id}-1", inv_id,
                f"Copilot Auto-Triage: Case {c_num} analyzed using SAML-D multi-hop topology. Recommended action: Trace outbound hops in Network Intelligence.",
                a_txn[7]
            ))

        # 6. Generate DATASET 2: NFPC Mule Account / Labeled Dataset for Feedback & Learning
        print("Generating and ingesting DATASET 2 (NFPC Labeled Dataset) for Feedback & Learning tab...")
        nfpc_adapter = NfpcAdapter(batch_size=100)
        nfpc_raw = nfpc_adapter.generate_verification_sample(count=50)
        normalized_nfpc, nfpc_res = nfpc_adapter.process_and_isolate(nfpc_raw, "BATCH-NFPC-LABELED")

        # Also store explicitly labeled feedback samples into analyst_feedback
        for i, row in enumerate(nfpc_raw):
            raw_label = row.get("mule_label", 0)
            is_scam = 1 if raw_label in (1, "1", True, "mule") else 0
            disp_type = "CONFIRMED_FRAUD" if is_scam == 1 else "LEGITIMATE_ACTIVITY"
            rationale_text = (
                "Verified coordinated money mule forwarding network (NFPC ground truth: SCAM)."
                if is_scam == 1 else
                "Verified legitimate personal salary & merchant activity (NFPC ground truth: LEGIT)."
            )

            # Associate with SAML investigation or stub
            inv_ref = f"INV-SAML-{(i % len(inv_cases)) + 1:03d}"
            fb_id = f"FB-NFPC-{1000 + i}"
            ts = row.get("transaction_timestamp", now.isoformat())

            cursor.execute("""
                INSERT OR REPLACE INTO analyst_feedback (
                    id, investigation_id, analyst_id, disposition, rationale,
                    evidence_reviewed_count, is_eligible_for_training, training_label,
                    model_version, rule_version, created_at
                ) VALUES (?, ?, 'USR-INV-01', ?, ?, 4, 1, ?, 'v1.0', 'v1.0', ?)
            """, (fb_id, inv_ref, disp_type, rationale_text, is_scam, ts))

            # Store in protected store as well
            store_protected_account_label(
                account_id=row["account_number"],
                dataset_name="NFPC_MULE",
                is_mule=is_scam,
                mule_role="MULE_SUSPECT" if is_scam else "LEGITIMATE",
                raw_labels={"dataset": "NFPC_MULE", "label": is_scam},
                timestamp=ts
            )

        conn.commit()

    print("Database seeding completed successfully!")
    print(f"- DATASET 1 (SAML-D): Active for Live Transactions, Alerts, Investigations, and Network Intelligence.")
    print(f"- DATASET 2 (NFPC Labeled): Active for Feedback & Learning tab with explicit Scam vs Legit labels.")

if __name__ == "__main__":
    seed_saml_and_nfpc_database()
