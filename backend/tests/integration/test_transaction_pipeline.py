import unittest
import sqlite3
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.core.database import SCHEMA_SQL
from app.services.transaction_ingestion import ingest_transaction_event
from app.detection.rules import ensure_default_rules

class TestTransactionPipeline(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)
        
        # Seed test customer and accounts
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO customers (id, customer_ref, full_name, email, created_at) VALUES ('CUST-1', 'REF-1', 'Alice', 'alice@test.com', '2026-01-01')")
        cursor.execute("INSERT INTO accounts (id, account_number, customer_id, balance, is_dormant, created_at) VALUES ('ACT-1', '4001', 'CUST-1', 10000.0, 0, '2026-01-01')")
        cursor.execute("INSERT INTO accounts (id, account_number, customer_id, balance, is_dormant, created_at) VALUES ('ACT-2', '4002', 'CUST-1', 500.0, 0, '2026-01-01')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_ingestion_creates_persisted_transaction(self):
        evt = {
            "event_id": "EVT-TEST-001",
            "source_account_id": "ACT-1",
            "destination_account_id": "ACT-2",
            "customer_id": "CUST-1",
            "amount": 150.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ONLINE",
            "created_at": "2026-10-27T10:00:00Z"
        }
        res = ingest_transaction_event(self.conn, evt)
        self.assertEqual(res["status"], "INGESTED")
        self.assertIsNotNone(res["transaction_id"])
        
        # Check DB
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE event_id = 'EVT-TEST-001'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["amount"], 150.0)

    def test_idempotent_event_replay_does_not_duplicate(self):
        evt = {
            "event_id": "EVT-TEST-002",
            "source_account_id": "ACT-1",
            "destination_account_id": "ACT-2",
            "customer_id": "CUST-1",
            "amount": 250.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ONLINE",
            "created_at": "2026-10-27T10:05:00Z"
        }
        res1 = ingest_transaction_event(self.conn, evt)
        self.assertEqual(res1["status"], "INGESTED")
        
        # Replay same event
        res2 = ingest_transaction_event(self.conn, evt)
        self.assertEqual(res2["status"], "DUPLICATE_IGNORED")

    def test_suspicious_event_creates_alert(self):
        from app.utils.time import utc_now_iso, minutes_ago_iso
        now_iso = utc_now_iso()
        ten_mins_ago = minutes_ago_iso(5)
        
        # 1. Simulate recent inbound transfer of 10,000
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO transactions (id, event_id, source_account_id, destination_account_id, customer_id, amount, currency, transaction_type, payment_channel, created_at) VALUES ('TXN-IN', 'EVT-IN', 'ACT-2', 'ACT-1', 'CUST-1', 10000.0, 'USD', 'WIRE', 'WIRE', ?)", (ten_mins_ago,))
        self.conn.commit()
        
        # 2. Ingest rapid outbound forwarding of 9,200
        evt = {
            "event_id": "EVT-TEST-003",
            "source_account_id": "ACT-1",
            "destination_account_id": "ACT-2",
            "customer_id": "CUST-1",
            "amount": 9200.0,
            "currency": "USD",
            "transaction_type": "TRANSFER",
            "payment_channel": "ONLINE",
            "created_at": now_iso
        }
        res = ingest_transaction_event(self.conn, evt)
        self.assertTrue(res["alert_created"])
        self.assertIsNotNone(res["alert_id"])
        
        # Verify alert persisted
        cursor.execute("SELECT * FROM alerts WHERE id = ?", (res["alert_id"],))
        alert_row = cursor.fetchone()
        self.assertIsNotNone(alert_row)
        self.assertGreaterEqual(alert_row["risk_score"], 45.0)

if __name__ == "__main__":
    unittest.main()
