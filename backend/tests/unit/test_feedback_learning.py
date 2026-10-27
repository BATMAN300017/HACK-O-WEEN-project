import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.learning.label_policy import evaluate_disposition_label
from app.learning.evaluator import evaluate_candidate_model

class TestFeedbackLearning(unittest.TestCase):
    def test_label_policy_confirmed_fraud_eligible(self):
        is_eligible, label_val, reason = evaluate_disposition_label("CONFIRMED_FRAUD")
        self.assertTrue(is_eligible)
        self.assertEqual(label_val, 1)

    def test_label_policy_false_positive_eligible(self):
        is_eligible, label_val, reason = evaluate_disposition_label("LEGITIMATE_ACTIVITY")
        self.assertTrue(is_eligible)
        self.assertEqual(label_val, 0)

    def test_label_policy_inconclusive_excluded(self):
        is_eligible, label_val, reason = evaluate_disposition_label("INCONCLUSIVE")
        self.assertFalse(is_eligible)
        self.assertIsNone(label_val)

    def test_model_promotion_gate_rejects_insufficient_samples(self):
        # 5 samples < 20 required
        y_true = [1, 0, 1, 0, 1]
        y_pred = [1, 0, 1, 0, 1]
        y_scores = [0.9, 0.1, 0.8, 0.2, 0.95]
        res = evaluate_candidate_model(y_true, y_pred, y_scores)
        self.assertFalse(res["passed"])
        self.assertIn("Sample size too small", res["reason"])

if __name__ == "__main__":
    unittest.main()
