import sys
import json
from decimal import Decimal
sys.path.insert(0, 'backend')
from app.core.database import get_db_connection

def default_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def run_audit():
    audit_data = {}
    with get_db_connection() as conn:
        cur = conn.cursor()

        # ---------------------------------------------------------
        # 1. Total System Records & 291-transaction breakdown
        # ---------------------------------------------------------
        cur.execute("SELECT COUNT(*) FROM transactions;")
        total_txns = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM alerts;")
        total_alerts = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM protected_transaction_labels;")
        total_prot_txns = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM protected_account_labels;")
        total_prot_accs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM protected_scenario_labels;")
        total_prot_scens = cur.fetchone()[0]

        audit_data["overview"] = {
            "total_transactions": total_txns,
            "total_alerts": total_alerts,
            "protected_transaction_labels": total_prot_txns,
            "protected_account_labels": total_prot_accs,
            "protected_scenario_labels": total_prot_scens
        }

        # ---------------------------------------------------------
        # 2. Per-Dataset Transaction & Account Statistics
        # ---------------------------------------------------------
        cur.execute("""
            SELECT dataset_source,
                   COUNT(*) as txn_count,
                   COUNT(DISTINCT event_id) as distinct_event_ids,
                   COUNT(CASE WHEN risk_score IS NOT NULL AND risk_score > 0 THEN 1 END) as scored_count,
                   COUNT(CASE WHEN risk_band = 'HIGH' THEN 1 END) as high_risk_count,
                   COUNT(CASE WHEN risk_band = 'ELEVATED' THEN 1 END) as elevated_risk_count,
                   COUNT(CASE WHEN risk_band = 'LOW' THEN 1 END) as low_risk_count,
                   COUNT(CASE WHEN risk_band = 'ROUTINE' THEN 1 END) as routine_risk_count,
                   AVG(risk_score) as avg_score,
                   MIN(risk_score) as min_score,
                   MAX(risk_score) as max_score
            FROM transactions
            GROUP BY dataset_source
            ORDER BY txn_count DESC;
        """)
        txn_stats = [dict(r) for r in cur.fetchall()]

        # Unique accounts per dataset
        cur.execute("""
            WITH all_accs AS (
                SELECT dataset_source, source_account_id as acc_id FROM transactions WHERE source_account_id IS NOT NULL
                UNION
                SELECT dataset_source, destination_account_id as acc_id FROM transactions WHERE destination_account_id IS NOT NULL
            )
            SELECT dataset_source, COUNT(DISTINCT acc_id) as total_unique_accounts
            FROM all_accs
            GROUP BY dataset_source;
        """)
        acc_stats = {r["dataset_source"]: r["total_unique_accounts"] for r in cur.fetchall()}

        # Duplicate check per dataset
        cur.execute("""
            SELECT dataset_source, COUNT(*) - COUNT(DISTINCT id) as duplicate_id_count
            FROM transactions
            GROUP BY dataset_source;
        """)
        dup_stats = {r["dataset_source"]: r["duplicate_id_count"] for r in cur.fetchall()}

        # Alerts per dataset
        cur.execute("""
            SELECT t.dataset_source, COUNT(a.id) as alert_count
            FROM alerts a
            JOIN transactions t ON a.transaction_id = t.id
            GROUP BY t.dataset_source;
        """)
        alert_stats = {r["dataset_source"]: r["alert_count"] for r in cur.fetchall()}

        # Protected labels per dataset
        cur.execute("""
            SELECT dataset_name, COUNT(*) as prot_txn_count
            FROM protected_transaction_labels
            GROUP BY dataset_name;
        """)
        prot_txns_by_ds = {r["dataset_name"]: r["prot_txn_count"] for r in cur.fetchall()}

        cur.execute("""
            SELECT dataset_name, COUNT(*) as prot_acc_count
            FROM protected_account_labels
            GROUP BY dataset_name;
        """)
        prot_accs_by_ds = {r["dataset_name"]: r["prot_acc_count"] for r in cur.fetchall()}

        # Datasets registry table metadata
        cur.execute("""
            SELECT id, name, domain, original_record_count, imported_record_count, processed_record_count, status
            FROM datasets
            ORDER BY id;
        """)
        registry_meta = [dict(r) for r in cur.fetchall()]

        audit_data["dataset_completeness"] = {
            "transactions_by_source": txn_stats,
            "accounts_by_source": acc_stats,
            "duplicates_by_source": dup_stats,
            "alerts_by_source": alert_stats,
            "protected_txns_by_dataset": prot_txns_by_ds,
            "protected_accs_by_dataset": prot_accs_by_ds,
            "registry_table": registry_meta
        }

        # ---------------------------------------------------------
        # 3. Investigation of the 147 Active Alerts
        # ---------------------------------------------------------
        cur.execute("""
            SELECT 
                a.id as alert_id,
                a.alert_ref,
                a.transaction_id,
                a.account_id,
                a.customer_id,
                a.severity,
                a.status as alert_status,
                a.risk_score as alert_risk_score,
                a.title,
                a.summary,
                t.dataset_source,
                t.amount,
                t.currency,
                t.risk_score as txn_risk_score,
                t.risk_band as txn_risk_band,
                ptl.is_laundering as ptl_is_laundering,
                ptl.laundering_type as ptl_laundering_type,
                pal.is_mule as pal_is_mule,
                pal.mule_role as pal_mule_role
            FROM alerts a
            LEFT JOIN transactions t ON a.transaction_id = t.id
            LEFT JOIN protected_transaction_labels ptl ON a.transaction_id = ptl.transaction_id
            LEFT JOIN protected_account_labels pal ON a.account_id = pal.account_id
            ORDER BY a.created_at DESC;
        """)
        all_alerts = [dict(r) for r in cur.fetchall()]

        # Also get findings per alert
        cur.execute("""
            SELECT alert_id, source, code as rule_code, description, score_contribution
            FROM alert_findings;
        """)
        findings_by_alert = {}
        for f in cur.fetchall():
            aid = f["alert_id"]
            if aid not in findings_by_alert:
                findings_by_alert[aid] = []
            findings_by_alert[aid].append(dict(f))

        # Categorize alerts into confirmed positive, false positive, unverified
        alert_analysis = []
        status_counts = {"CONFIRMED_POSITIVE": 0, "FALSE_POSITIVE": 0, "UNVERIFIED": 0}
        alerts_by_ds_detailed = {}

        for alt in all_alerts:
            aid = alt["alert_id"]
            alt["findings"] = findings_by_alert.get(aid, [])
            ds = alt["dataset_source"] or "UNKNOWN"

            # Determine ground truth status
            ptl = alt["ptl_is_laundering"]
            pal = alt["pal_is_mule"]

            if ptl == 1 or pal == 1:
                verdict = "CONFIRMED_POSITIVE"
            elif ptl == 0 or pal == 0:
                verdict = "FALSE_POSITIVE"
            else:
                verdict = "UNVERIFIED"

            status_counts[verdict] += 1
            alt["ground_truth_verdict"] = verdict

            if ds not in alerts_by_ds_detailed:
                alerts_by_ds_detailed[ds] = {"total": 0, "CONFIRMED_POSITIVE": 0, "FALSE_POSITIVE": 0, "UNVERIFIED": 0}
            alerts_by_ds_detailed[ds]["total"] += 1
            alerts_by_ds_detailed[ds][verdict] += 1

            alert_analysis.append(alt)

        audit_data["alerts_investigation"] = {
            "total_alerts": len(alert_analysis),
            "verdict_counts": status_counts,
            "dataset_breakdown": alerts_by_ds_detailed,
            "alerts_sample": alert_analysis[:20]  # sample of 20 for JSON display
        }

        # ---------------------------------------------------------
        # 4. Detection Quality Evaluation using IndependentEvaluator
        # ---------------------------------------------------------
        from app.evaluation.evaluator import IndependentEvaluator
        bench = IndependentEvaluator.get_benchmark_comparison_matrix(conn)
        audit_data["benchmark_matrix"] = bench

    with open("backups/audit_phase2_results.json", "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, default=default_json)

    print("Audit data collected and written to backups/audit_phase2_results.json")

if __name__ == "__main__":
    run_audit()
