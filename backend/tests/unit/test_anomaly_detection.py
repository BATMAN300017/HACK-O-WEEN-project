import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.detection.anomaly import calculate_mad_anomaly

class TestAnomalyDetection(unittest.TestCase):
    def test_cold_start_reports_low_history_confidence(self):
        res = calculate_mad_anomaly(5000.0, [5000.0], is_cold_start=True)
        self.assertEqual(res["confidence"], "LOW_HISTORY_CONFIDENCE")
        self.assertFalse(res["anomaly_detected"])

    def test_significant_amount_deviation_detected(self):
        history = [100.0, 105.0, 95.0, 110.0, 100.0, 98.0, 102.0]
        res = calculate_mad_anomaly(5000.0, history, is_cold_start=False)
        self.assertTrue(res["anomaly_detected"])
        self.assertGreater(res["score"], 50.0)

    def test_normal_amount_not_flagged(self):
        history = [100.0, 105.0, 95.0, 110.0, 100.0, 98.0, 102.0]
        res = calculate_mad_anomaly(104.0, history, is_cold_start=False)
        self.assertFalse(res["anomaly_detected"])
        self.assertEqual(res["score"], 0.0)

if __name__ == "__main__":
    unittest.main()
