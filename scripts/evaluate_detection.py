import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.core.database import get_db_connection
from app.services.analytics_service import get_kpi_summary, get_rule_performance
from app.learning.model_registry import get_registry_status

def evaluate_detection_performance():
    print("Evaluating SentinelFlow AI Detection & Learning Performance...")
    with get_db_connection() as conn:
        kpis = get_kpi_summary(conn)
        rules = get_rule_performance(conn)
        models = get_registry_status()

        print("\n--- OPERATIONAL KPIS ---")
        print(f"Transactions Processed: {kpis['transactions_processed']}")
        print(f"Alerts Generated: {kpis['alerts_generated']}")
        print(f"Active Investigations: {kpis['open_investigations']}")
        print(f"Confirmed Fraud Cases: {kpis['confirmed_fraud_count']}")
        print(f"Verified False Positive Rate: {kpis['verified_false_positive_rate']}%")
        print(f"Investigation Completion Rate: {kpis['investigation_completion_rate']}%")

        print("\n--- ACTIVE SCORING ENGINE ---")
        print(f"Model Version: {models['active_version']}")
        print(f"Benchmark Metrics: {models['active_metrics']}")

        print("\n--- DETECTION RULE METRICS ---")
        for r in rules:
            print(f"- {r['rule_code']}: Triggered {r['trigger_count']} times | Confirmed: {r['confirmed_fraud_count']} | Precision: {r['precision']}")

if __name__ == "__main__":
    evaluate_detection_performance()
