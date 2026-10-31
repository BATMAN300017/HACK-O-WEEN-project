# SentinelFlow AI — Comprehensive Architectural Blueprint & Implementation Plan

**Author:** SentinelFlow Core Engineering  
**Version:** 2.0.0-PROD  
**Target Environment:** Local Antigravity Agent Mode, Render Cloud (Web Service + Worker), Supabase (PostgreSQL + Object Storage)

---

## 1. Executive Summary & Repository Inspection

### 1.1 Existing Architecture
- **Backend Framework:** FastAPI (`0.158.1`) with Pydantic v2 and Uvicorn.
- **Frontend Architecture:** Single Page Application (SPA) served via FastAPI static mount (`backend/app/static/index.html`) using Tailwind CSS and SVG graph canvas. Scaffolding in `frontend/` contains Next.js types but is largely placeholder files.
- **Database / Storage:** Hybrid SQLite3 (`sentinelflow.db`) and PostgreSQL support (`backend/app/core/database.py`).
- **Detection Engine:** 4-way hybrid scoring ensemble:
  1. Deterministic Rule Engine (`rules.py`): 30% weight
  2. MAD Anomaly Detection (`anomaly.py`): 25% weight
  3. Supervised Classification (`supervised.py`): 25% weight
  4. Graph Intelligence (`graph_signals.py`): 20% weight
- **Evaluation Isolation:** Pipeline A (Unsupervised detection store) vs Pipeline B (Protected ground-truth store in `data/protected_labels/protected_ground_truth.db`).

---

## 2. Diagnosis: Why the Website Showed Only 400 Active Records

Our deep code inspection isolated the exact root cause:
1. **Hardcoded Sample Seeding:** In `scripts/seed_saml_and_nfpc.py` (line 82), the ingestion logic called:
   ```python
   saml_raw = saml_adapter.generate_verification_sample(count=400)
   ```
   This fabricated exactly 400 sample records rather than streaming from disk or remote datasets.
2. **Database Fallback:** The live Render container ran with default `DATABASE_URL=sqlite:///./sentinelflow.db` rather than Supabase PostgreSQL. On fresh boot, `backend/app/main.py` detected 0 records and auto-executed `seed_saml_and_nfpc.py` with the 400-record sample.
3. **Unpopulated Supabase Instance:** Querying Supabase PostgreSQL confirmed that while users were seeded, `transactions`, `alerts`, `investigations`, and `accounts` had 0 rows.

**Resolution:**
- Build real streaming batch ingestion pipelines using **Polars** and **PyArrow** for both the **NFPC** dataset and the **Synthetic AML (SAML-D)** dataset.
- Migrate Supabase PostgreSQL schema to full production specification.
- Remove all synthetic 400-record generators from startup routines.
- Ingest real datasets with verified counts into Supabase and local storage.

---

## 3. Proposed Platform Architecture

```
+-----------------------------------------------------------------------------------+
|                                 DATA INGESTION                                    |
|   +-----------------------+                    +------------------------------+   |
|   | NFPC (Parquet Batches)|                    | Synthetic AML (SAML-D CSV)   |   |
|   | 1M+ Transactions      |                    | 25k - 9.5M Transactions      |   |
|   +-----------+-----------+                    +--------------+---------------+   |
+---------------|-----------------------------------------------|-------------------+
                v                                               v
+-----------------------------------------------------------------------------------+
|                        SUPABASE STORAGE (Private Buckets)                         |
|   - sentinelflow-datasets/   (Original raw parquet & CSV tranches)                |
|   - sentinelflow-processed/  (Normalized Parquet partitions & feature exports)    |
|   - sentinelflow-models/     (Trained XGBoost, Random Forest, Isolation Forest)   |
+---------------------------------------+-------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                           ETL & NORMALIZATION ENGINE                              |
|   - Streaming Chunk Loading via Polars / PyArrow                                  |
|   - ISO 4217 Multi-Currency Normalization (16 currencies mapped to INR base)      |
|   - Strict Ground Truth Label Stripping -> Pipeline B (Protected Evaluation Store)|
|   - Database Bulk Insertion into Supabase PostgreSQL                              |
+---------------------------------------+-------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                       SUPABASE POSTGRESQL (12 Tables)                             |
|   - datasets                 - transactions             - model_predictions       |
|   - alerts                   - investigations           - investigation_txns      |
|   - investigation_evidence   - fund_flow_edges          - analyst_feedback        |
|   - model_versions           - ingestion_jobs           - replay_sessions         |
+---------------------------------------+-------------------------------------------+
                                        |
                    +-------------------+-------------------+
                    v                                       v
+---------------------------------------+   +---------------------------------------+
|          ML & ANALYTICS WORKER        |   |         FASTAPI WEB SERVICE           |
|   - Supervised (XGBoost / LogReg)     |   |   - REST API Endpoints                |
|   - Unsupervised Isolation Forest     |   |   - Authenticated User Sessions       |
|   - Robust MAD Statistical Baselines  |   |   - Interactive Command Center SPA    |
|   - Graph Intelligence & Mule Network |   |   - Real-time Replay SSE Telemetry    |
|   - Human-in-the-Loop Feedback Loop   |   |   - Supabase Signed Storage URLs      |
+---------------------------------------+   +---------------------------------------+
```

---

## 4. Supabase Database Design (12 Production Tables)

1. `datasets`: Metadata, source lineage, total discovered, imported, processed, failed record counts.
2. `transactions`: Normalized transactions (`id`, `dataset_id`, `original_transaction_id`, `transaction_timestamp`, `amount`, `currency`, `sender_account`, `receiver_account`, `transaction_type`, `original_label`, `normalized_label`, `raw_data_reference`, `processing_status`).
3. `model_predictions`: Predictions, risk scores, confidence, detection reasons per model version.
4. `alerts`: Model-triggered and rule-triggered alerts (`severity`, `alert_type`, `detection_reason`, `status`, `assigned_analyst`).
5. `investigations`: Formal case dossiers (`case_number`, `status`, `risk_score`, `assigned_analyst`, `findings`).
6. `investigation_transactions`: Many-to-many bridge linking transactions to investigation dossiers.
7. `investigation_evidence`: Verified exhibits, transaction extracts, and Supabase Storage file links.
8. `fund_flow_edges`: Money-flow relationships between accounts (`source_account`, `destination_account`, `amount`, `currency`, `timestamp`, `edge_type`).
9. `analyst_feedback`: Human-in-the-loop decisions (`CONFIRMED_FRAUD`, `LEGITIMATE_ACTIVITY`, `INCONCLUSIVE`) for model retraining.
10. `model_versions`: Model registry (`model_name`, `version`, `dataset_versions`, `eval_metrics_json`, `artifact_storage_path`).
11. `ingestion_jobs`: Real-time tracking of bulk imports, checkpointing, progress, and failure diagnostics.
12. `replay_sessions`: Historical transaction replay state machine (`current_index`, `processing_speed`, `alerts_generated`).

---

## 5. Machine Learning Architecture

1. **Supervised Learning**:
   - **XGBoost & Logistic Regression**: Trained on 6-dimensional normalized transactional and behavioral features:
     - `amount_normalized`
     - `velocity_count` (short window)
     - `is_cold_start`
     - `is_dormant_account`
     - `is_new_beneficiary`
     - `shared_device_accounts`
   - Evaluation Metrics: Precision, Recall, F1, PR-AUC, Confusion Matrix.
   - Promotion Gate: Precision $\ge 0.70$, F1 $\ge 0.60$.
2. **Unsupervised Anomaly Detection**:
   - **Isolation Forest**: Multi-dimensional outlier scoring on high-velocity transactions.
   - **MAD Robust Baseline**: Median Absolute Deviation robust z-score calculation avoiding skew from extreme laundering outliers.
3. **Graph Intelligence**:
   - Multi-hop traversal (NetworkX): Fan-in collection hubs, Fan-out dispersal, Circular flow cycles, and shortest-path attribution.

---

## 6. Frontend Command Center (8 Functional Sections)

1. **Overview (Dashboard)**: Real-time KPIs calculated from actual database records, dataset filter, risk distribution.
2. **Data Management**: Ingestion triggers, record counts discovered vs imported, batch retry, Supabase Storage manifest.
3. **Live Transactions**: Searchable, filterable real-time transaction table with model predictions and risk scores.
4. **Alerts Queue**: Triage, escalation, dismissal with reason, and one-click case conversion.
5. **Investigations**: Case dossiers with evidence items, tasks checklist, Copilot AI notes, and disposition submission.
6. **Fund Flow Tracing**: Interactive multi-hop path visualizer between source, intermediate hops, and cash-out points.
7. **Network Intelligence**: SVG topological graph showing mule rings, collection hubs, and shared device clusters.
8. **Feedback & Learning**: Analyst feedback triage, model version registry, candidate retraining, and promotion gates.

---

## 7. Render Deployment Strategy

- **Service A (Web Service)**: Deployed from Dockerfile, running FastAPI + Uvicorn on `$PORT`, connected to Supabase PostgreSQL via connection pooling.
- **Service B (Background Worker)**: Shares the same Docker image, executing dataset ingestion, replay orchestration, and background model evaluation jobs.
- **Environment Parity**: Zero hardcoded credentials. All configuration driven via Render and Supabase environment variables.
