import sys
import json
sys.path.insert(0, 'backend')
from fastapi.testclient import TestClient
from app.main import app

def run_smoke_tests():
    client = TestClient(app)

    print("=== 1. Testing GET /api/v1/datasets/lab ===")
    r = client.get("/api/v1/datasets/lab")
    assert r.status_code == 200, f"Failed: {r.status_code}"
    lab_data = r.json()
    datasets = lab_data if isinstance(lab_data, list) else lab_data.get("datasets", [])
    print(f"Total datasets in lab: {len(datasets)}")
    for d in datasets:
        print(f" - {d.get('dataset_name')}: domain={d.get('domain')}, txns={d.get('ingested_transactions_count')}, labels={d.get('protected_labels_count')}")

    print("\n=== 2. Testing GET /api/v1/dashboard/summary ===")
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200, f"Failed: {r.status_code}"
    summary = r.json()
    print("Processed transactions:", summary.get("total_transactions_processed"))
    print("Active alerts:", summary.get("total_alerts_active"))
    print("Risk distribution:", summary.get("risk_distribution"))

    print("\n=== 3. Testing GET /api/v1/evaluation/benchmark ===")
    r = client.get("/api/v1/evaluation/benchmark")
    assert r.status_code == 200, f"Failed: {r.status_code}"
    bench = r.json()
    print("Benchmark status:", bench.get("evaluation_status"))
    print("Evaluated benchmarks:", list(bench.get("datasets", {}).keys()))

    print("\n=== 4. Testing GET /api/v1/dashboard/trends ===")
    r = client.get("/api/v1/dashboard/trends")
    assert r.status_code == 200, f"Failed: {r.status_code}"
    trends = r.json()
    print(f"Trends timeline points: {len(trends.get('timeline', []))}")

    print("\nALL SMOKE TESTS PASSED!")

if __name__ == "__main__":
    run_smoke_tests()
