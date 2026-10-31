import sys
import os
import json

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app

def test_live_endpoints():
    client = TestClient(app)
    
    endpoints = [
        ("/health", "Health Check"),
        ("/api/v1/dashboard/summary", "Dashboard KPI Summary"),
        ("/api/v1/dashboard/trends", "Dashboard Trends"),
        ("/api/v1/datasets", "Registered Datasets"),
        ("/api/v1/transactions?limit=10", "Live Transactions"),
        ("/api/v1/alerts?page_size=10", "Alerts Queue"),
        ("/api/v1/investigations?page_size=10", "Investigations Dossiers"),
        ("/api/v1/graph", "Network Intelligence Graph"),
        ("/api/v1/learning/status", "ML Feedback & Learning Status"),
        ("/api/v1/rules", "Detection Rules")
    ]
    
    print("=" * 60)
    print("Verifying FastAPI Endpoints with Supabase PostgreSQL Backend")
    print("=" * 60)
    
    all_ok = True
    for ep, desc in endpoints:
        try:
            res = client.get(ep)
            if res.status_code == 200:
                data = res.json()
                sample_info = ""
                if isinstance(data, dict):
                    if "transactions_processed" in data:
                        sample_info = f"-> txns_processed: {data['transactions_processed']:,}, alerts: {data.get('alerts_generated')}"
                    elif "risk_score_distribution" in data:
                        sample_info = f"-> risk buckets: {len(data['risk_score_distribution'])}"
                    elif "nodes" in data:
                        sample_info = f"-> graph nodes: {len(data['nodes'])}, edges: {len(data.get('edges', []))}"
                    elif "active_model" in data:
                        sample_info = f"-> active model: {data.get('active_model', {}).get('version_tag', 'N/A')}"
                elif isinstance(data, list):
                    sample_info = f"-> items returned: {len(data)}"
                print(f"  [PASS] {desc:<32} ({ep}) {sample_info}")
            else:
                print(f"  [FAIL] {desc:<32} ({ep}) Status: {res.status_code} - {res.text[:100]}")
                all_ok = False
        except Exception as e:
            print(f"  [ERROR] {desc:<32} ({ep}): {e}")
            all_ok = False
            
    print("=" * 60)
    if all_ok:
        print("ALL FASTAPI ENDPOINTS VERIFIED AND OPERATIONAL!")
    else:
        print("SOME ENDPOINTS FAILED!")
    print("=" * 60)

if __name__ == "__main__":
    test_live_endpoints()
