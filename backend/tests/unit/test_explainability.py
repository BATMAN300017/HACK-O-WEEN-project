import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.detection.explainability import generate_risk_explanation

class TestExplainability(unittest.TestCase):
    def test_narrative_explanation_includes_computed_data(self):
        txn = {"amount": 7500.0, "source_account_id": "ACT-1042", "destination_account_id": "ACT-9999", "transaction_type": "transfer"}
        features = {"short_window_count": 4, "short_window_sum": 12000.0}
        rules = [{"name": "Rapid Consecutive Transfers"}]
        anomaly = {"anomaly_detected": True, "reason": "Amount deviates from median"}
        graph = {"signals": [{"description": "Shared device detected"}]}
        supervised = {"supervised_score": 68.0}
        final_score = 72.5
        
        explanation = generate_risk_explanation(txn, features, rules, anomaly, graph, supervised, final_score)
        self.assertIn("ACT-1042", explanation)
        self.assertIn("$7,500.00", explanation)
        self.assertIn("Rapid Consecutive Transfers", explanation)
        self.assertIn("72.5/100", explanation)

if __name__ == "__main__":
    unittest.main()
