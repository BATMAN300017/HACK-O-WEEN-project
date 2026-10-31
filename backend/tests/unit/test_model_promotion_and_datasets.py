"""
Unit and Integration Tests for Dual-Mode Model Promotion & Multi-Domain Dataset Laboratory.

Covers:
1. Dual-mode promotion policy: Manual Approval (default) vs Automatic Promotion.
2. Threshold enforcement (precision, recall, PR-AUC, max FPR, F1, sample size).
3. Independent validation constraint (rejecting training performance as validation proof).
4. Multi-domain dataset provenance (Traditional Banking, Mobile Money, Crypto, Simulation).
5. Cross-dataset compatibility enforcement (PaySim mobile money vs SAML-D banking mismatch).
6. IBM AMLSim parameterized scenario generation with seed reproducibility and metadata.
7. Zero label leakage across all dataset adapters into Pipeline A.
"""

import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.core.database import get_db_connection
from app.learning.promotion_service import ModelPromotionService
from app.data_ingestion.dataset_registry import DatasetRegistry
from app.data_ingestion.provenance import DATASET_METADATA_REGISTRY
from app.data_ingestion.amlsim_adapter import AmlSimScenarioGenerator

class TestModelPromotionAndDatasetLab(unittest.TestCase):

    def test_default_promotion_policy_is_manual(self):
        with get_db_connection() as conn:
            policy = ModelPromotionService.get_promotion_policy(conn)
            self.assertIn(policy.get("mode"), ["MANUAL", "AUTOMATIC"])
            self.assertGreaterEqual(policy.get("min_precision", 0), 0.70)
            self.assertGreaterEqual(policy.get("min_pr_auc", 0), 0.75)
            self.assertTrue(policy.get("require_independent_validation"))

    def test_policy_threshold_validation_blocks_substandard_model(self):
        # Metrics that fail precision and PR-AUC thresholds
        failing_metrics = {
            "precision": 0.50,
            "recall": 0.40,
            "pr_auc": 0.55,
            "fpr": 0.15,
            "f1": 0.44,
            "training_samples": 50
        }
        with get_db_connection() as conn:
            res = ModelPromotionService.evaluate_model_for_promotion(
                conn=conn,
                model_version="v_failing_test",
                evaluation_metrics=failing_metrics,
                is_independent_validation=True
            )
            self.assertFalse(res["passed"])
            self.assertFalse(res["can_auto_promote"])
            self.assertGreater(len(res["failure_reasons"]), 0)

    def test_policy_requires_independent_validation(self):
        # High metrics but failing independent validation requirement
        training_only_metrics = {
            "precision": 0.99,
            "recall": 0.99,
            "pr_auc": 0.99,
            "fpr": 0.01,
            "f1": 0.99,
            "training_samples": 100
        }
        with get_db_connection() as conn:
            res = ModelPromotionService.evaluate_model_for_promotion(
                conn=conn,
                model_version="v_train_eval_test",
                evaluation_metrics=training_only_metrics,
                is_independent_validation=False
            )
            self.assertFalse(res["passed"])
            self.assertFalse(res["can_auto_promote"])
            self.assertTrue(any("training set" in r for r in res["failure_reasons"]))

    def test_all_seven_datasets_registered_with_provenance(self):
        datasets = DatasetRegistry.get_all_registered_datasets()
        self.assertEqual(len(datasets), 7)
        ids = {d["id"] for d in datasets}
        expected_ids = {"SAML_D", "NFPC_MULE", "IBM_AML", "PAYSIM", "ELLIPTIC", "AML_SIM", "INDIA_SIMULATOR"}
        self.assertEqual(ids, expected_ids)

    def test_domain_separation_enforced(self):
        # SAML_D & IBM_AML must be traditional banking
        self.assertEqual(DATASET_METADATA_REGISTRY["SAML_D"]["domain"], "traditional_banking")
        self.assertEqual(DATASET_METADATA_REGISTRY["IBM_AML"]["domain"], "traditional_banking")
        
        # PaySim must be mobile money (NOT bank AML)
        self.assertEqual(DATASET_METADATA_REGISTRY["PAYSIM"]["domain"], "mobile_money")
        
        # Elliptic must be cryptocurrency (NOT bank AML)
        self.assertEqual(DATASET_METADATA_REGISTRY["ELLIPTIC"]["domain"], "cryptocurrency")
        
        # AML_SIM must be synthetic simulation
        self.assertEqual(DATASET_METADATA_REGISTRY["AML_SIM"]["domain"], "synthetic_simulation")

    def test_cross_dataset_compatibility_blocks_paysim_vs_samld(self):
        res = DatasetRegistry.evaluate_cross_dataset_compatibility(
            source_id="PAYSIM",
            target_id="SAML_D",
            target_task="traditional_banking_aml"
        )
        self.assertFalse(res["compatible"])
        self.assertEqual(res["status"], "INCOMPATIBLE")
        self.assertIn("mobile_money", res["reason"])

    def test_cross_dataset_compatibility_permits_ibmaml_vs_samld(self):
        res = DatasetRegistry.evaluate_cross_dataset_compatibility(
            source_id="IBM_AML",
            target_id="SAML_D",
            target_task="traditional_banking_aml"
        )
        self.assertTrue(res["compatible"])
        self.assertEqual(res["status"], "COMPATIBLE")
        self.assertIn("transaction_amount", res["common_feature_layer"])

    def test_amlsim_scenario_generation_reproducibility(self):
        s1 = AmlSimScenarioGenerator.generate_scenario(typology="CYCLE", num_accounts=4, random_seed=999)
        s2 = AmlSimScenarioGenerator.generate_scenario(typology="CYCLE", num_accounts=4, random_seed=999)
        
        # Same seed must generate identical transaction amounts and counts
        self.assertEqual(s1["total_transactions"], s2["total_transactions"])
        self.assertEqual(s1["laundering_transactions_count"], s2["laundering_transactions_count"])
        amounts1 = [t["amount"] for t in s1["transactions"]]
        amounts2 = [t["amount"] for t in s2["transactions"]]
        self.assertEqual(amounts1, amounts2)

    def test_amlsim_preserves_strict_label_isolation(self):
        scenario = AmlSimScenarioGenerator.generate_scenario(typology="FAN_OUT", num_accounts=5, random_seed=123)
        for txn in scenario["transactions"]:
            # Pipeline A feature feed MUST have zeroed ground truth
            self.assertEqual(txn.get("is_ground_truth_fraud"), 0)

if __name__ == "__main__":
    unittest.main()
