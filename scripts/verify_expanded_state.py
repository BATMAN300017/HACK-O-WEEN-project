import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

def verify():
    with get_db_connection() as conn:
        cur = conn.cursor()

        print("=== COMPREHENSIVE LATENCY BENCHMARKS ===")
        # 1. Primary key lookup
        times = []
        for _ in range(5):
            t0 = time.time()
            cur.execute("SELECT * FROM transactions WHERE id = 'TXN_0000200000';")
            cur.fetchone()
            times.append((time.time() - t0) * 1000)
        avg_pk = sum(times) / len(times)
        print(f"1. Primary Key Lookup (id = 'TXN_0000200000'): {avg_pk:.2f} ms")

        # 2. Source account index lookup
        times = []
        for _ in range(5):
            t0 = time.time()
            cur.execute("SELECT count(*), sum(amount) FROM transactions WHERE source_account_id = 'ACCT_000153';")
            res = cur.fetchone()
            times.append((time.time() - t0) * 1000)
        avg_acc = sum(times) / len(times)
        print(f"2. Account Index Lookup (ACCT_000153, {res[0]} txns, INR {res[1]:,.2f}): {avg_acc:.2f} ms")

        # 3. Dataset source aggregation
        times = []
        for _ in range(3):
            t0 = time.time()
            cur.execute("SELECT count(*) FROM transactions WHERE dataset_source = 'NFPC';")
            res_ds = cur.fetchone()
            times.append((time.time() - t0) * 1000)
        avg_ds = sum(times) / len(times)
        print(f"3. Dataset Filter Count (NFPC, {res_ds[0]} rows): {avg_ds:.2f} ms")

        # 4. Critical risk transactions join
        t0 = time.time()
        cur.execute("""
            SELECT t.id, t.amount, a.account_number, c.full_name, t.risk_score
            FROM transactions t
            JOIN accounts a ON t.source_account_id = a.id
            JOIN customers c ON t.customer_id = c.id
            WHERE t.dataset_source = 'NFPC' AND t.risk_band = 'CRITICAL'
            LIMIT 5;
        """)
        join_rows = cur.fetchall()
        lat_join = (time.time() - t0) * 1000
        print(f"4. 3-Way Entity Join (5 rows): {lat_join:.2f} ms")
        for r in join_rows:
            print(f"   Sample: Tx={r['id']}, Amt={r['amount']}, Acc={r['account_number']}, Cust={r['full_name']}, Score={r['risk_score']}")

        # 5. Check dataset registry
        print("\n=== DATASETS REGISTRY ===")
        cur.execute("SELECT id, name, domain, original_record_count, imported_record_count, status FROM datasets;")
        for d in cur.fetchall():
            print(f"  {d['id']}: {d['name']} ({d['domain']}) -> Imported: {d['imported_record_count']:,} / Original: {d['original_record_count']:,} [{d['status']}]")

        # 6. Check ground-truth label isolation
        print("\n=== GROUND-TRUTH LABEL ISOLATION AUDIT ===")
        cur.execute("SELECT count(*), is_ground_truth_fraud, ground_truth_label FROM transactions GROUP BY is_ground_truth_fraud, ground_truth_label;")
        iso_rows = cur.fetchall()
        for r in iso_rows:
            print(f"  transactions table: count={r[0]:,}, is_ground_truth_fraud={r[1]}, ground_truth_label='{r[2]}'")
            
        cur.execute("SELECT dataset_name, count(*), sum(case when is_mule = 1 then 1 else 0 end) as mules FROM protected_account_labels GROUP BY dataset_name;")
        print("  protected_account_labels (Pipeline B):", [dict(r._dict) for r in cur.fetchall()])

        cur.close()

if __name__ == '__main__':
    verify()
