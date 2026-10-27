import unittest
import sqlite3
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.detection.rules import evaluate_rules, ensure_default_rules
from app.core.database import SCHEMA_SQL

class TestDetectionRules(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        ensure_default_rules(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_high_velocity_rule_triggers_above_threshold(self):
        txn = {"amount": 500.0, "source_account_id": "ACT-1", "id": "TXN-1"}
        features = {"short_window_count": 6} # Threshold is 4
        triggered = evaluate_rules(self.conn, txn, features)
        rule_codes = [r["rule_code"] for r in triggered]
        self.assertIn("HIGH_VELOCITY_TRANSFERS", rule_codes)

    def test_high_velocity_rule_does_not_trigger_below_threshold(self):
        txn = {"amount": 500.0, "source_account_id": "ACT-1", "id": "TXN-1"}
        features = {"short_window_count": 2}
        triggered = evaluate_rules(self.conn, txn, features)
        rule_codes = [r["rule_code"] for r in triggered]
        self.assertNotIn("HIGH_VELOCITY_TRANSFERS", rule_codes)

    def test_rapid_fund_movement_rule(self):
        txn = {"amount": 9500.0, "source_account_id": "ACT-1", "id": "TXN-1"}
        features = {"recent_inbound_sum": 10000.0} # 95% ratio > 80%
        triggered = evaluate_rules(self.conn, txn, features)
        rule_codes = [r["rule_code"] for r in triggered]
        self.assertIn("RAPID_FUND_MOVEMENT", rule_codes)

if __name__ == "__main__":
    unittest.main()
