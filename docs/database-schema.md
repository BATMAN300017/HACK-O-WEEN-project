# SentinelFlow AI — Database Schema & Data Integrity

## Design Principles
1. **Relational Integrity**: Strict foreign key constraints across all transactional and investigative entities.
2. **Deterministic Monetary Precision**: Amounts are stored using floating/numeric values formatted to 2 decimals.
3. **UTC Timestamps**: All timestamps are formatted in ISO 8601 UTC.
4. **Append-Only Auditing**: Every modification, disposition, rule change, and model promotion produces an immutable record in `audit_events`.
5. **Strict Ground-Truth Isolation**: `is_ground_truth_fraud` is stored strictly as a test-only attribute in transactions and is never exposed to investigator APIs.

## Schema Overview

### Core Entities
- `users`: Authenticated analysts and roles (`investigator`, `senior_investigator`, `fraud_admin`, `auditor`).
- `customers`: Customer profiles with KYC status and risk tier.
- `accounts`: Bank accounts linked to customers with balance, currency, dormancy status.
- `merchants`: Merchant profiles and risk levels.
- `devices`: Device fingerprints and operating environments.

### Transactions & Detection
- `transactions`: Core transaction events with payment channel, amount, counterparty, device, risk score, and triage band.
- `alerts`: Elevated risk triggers requiring review.
- `alert_findings`: Atomic findings from rules, behavioral anomalies, supervised ML, and graph signals.
- `detection_rules`: Configurable rules with versioning, lookback windows, and JSON thresholds.
- `detection_rule_versions`: Historical rule snapshots preserving threshold configurations.

### Case Management & Evidence
- `investigations`: Formal case dossiers with priority, status, assigned investigator, peer reviewer, and disposition.
- `investigation_alerts`: Many-to-many relationship linking alerts into cases.
- `evidence_items`: Typed records (Transaction, Behavioral Anomaly, Rule Match, Relationship, Contradictory) with SHA-256 integrity hash.
- `investigation_tasks`: Procedural playbook checklists.
- `investigation_notes`: Analyst commentary and auto-triage recommendations.
- `investigation_events`: Timeline events for case reconstruction.

### Controlled Learning & Governance
- `analyst_feedback`: Human investigator dispositions with rationale and training eligibility flag.
- `model_versions`: Registry of baseline, candidate, and promoted scoring models.
- `model_evaluations`: Validation reports comparing candidate vs. active model performance.
- `training_dataset_versions`: Versioned datasets generated from eligible feedback labels.
- `audit_events`: Append-only compliance log.
