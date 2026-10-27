SentinelFlow AI — Automated Test Plan & Matrix
Test Suite Structure
The test suite covers both unit components and end-to-end integration workflows.
Unit Tests (backend/tests/unit/)
test_detection_rules.py:
Rule threshold trigger condition.
Non-trigger condition below threshold.
Rapid fund forwarding percentage logic.
test_anomaly_detection.py:
Account cold-start detection (LOW_HISTORY_CONFIDENCE).
Rolling Median Absolute Deviation (MAD) robust z-score calculation.
Normal amount non-triggering behavior.
test_graph_analysis.py:
Breadth-first shortest path discovery.
Multi-hop traversal.
Degree centrality scoring.
test_feedback_learning.py:
Label policy enforcement (Confirmed Fraud → 1, False Positive → 0, Inconclusive → None).
Model promotion gate refusal when sample size < 20.
test_explainability.py:
Narrative generation with concrete computed facts.
test_permissions.py:
Role-based authorization for Investigator, Senior Investigator, Admin, Auditor.
Integration Tests (backend/tests/integration/)
test_transaction_pipeline.py:
Ingestion creates persisted transaction.
Idempotency check ignores duplicated transaction event IDs.
Suspicious transaction automatically generates an alert.
test_investigation_workflow.py:
Opening investigation dossier.
Attaching typed evidence items with SHA-256 integrity hashes.
Adding case notes and completing tasks.
Submitting final disposition and recording feedback.
test_api.py:
Route handlers for /health, /auth/login, /dashboard, /transactions, /alerts, /investigations, /graph, /rules, /learning.
Executing the Test Suite
python backend/tests/run_tests.py
Expected result: 32 tests passed (100% passing).
