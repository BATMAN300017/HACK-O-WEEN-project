import psycopg2
import sys

db_url = "postgresql://postgres:eDHVobOYWA95JG9u@db.dyipyfvbqoqbjwcqlrqy.supabase.co:5432/postgres"

MIGRATION_SQL = """
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. DATASETS
CREATE TABLE IF NOT EXISTS public.datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    description TEXT,
    original_record_count BIGINT DEFAULT 0,
    imported_record_count BIGINT DEFAULT 0,
    processed_record_count BIGINT DEFAULT 0,
    failed_record_count BIGINT DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'REGISTERED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Core Entity Stubs: CUSTOMERS & ACCOUNTS
CREATE TABLE IF NOT EXISTS public.customers (
    id TEXT PRIMARY KEY,
    customer_ref TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    risk_tier TEXT NOT NULL DEFAULT 'STANDARD',
    kyc_status TEXT NOT NULL DEFAULT 'VERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.accounts (
    id TEXT PRIMARY KEY,
    account_number TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    account_type TEXT NOT NULL DEFAULT 'CHECKING',
    currency TEXT NOT NULL DEFAULT 'USD',
    balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    is_dormant BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. TRANSACTIONS: Update with all required columns
CREATE TABLE IF NOT EXISTS public.transactions (
    id TEXT PRIMARY KEY,
    amount NUMERIC(15, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS dataset_id TEXT REFERENCES public.datasets(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS original_transaction_id TEXT,
    ADD COLUMN IF NOT EXISTS transaction_timestamp TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS amount NUMERIC(15, 2) DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD',
    ADD COLUMN IF NOT EXISTS sender_account TEXT,
    ADD COLUMN IF NOT EXISTS receiver_account TEXT,
    ADD COLUMN IF NOT EXISTS transaction_type TEXT DEFAULT 'TRANSFER',
    ADD COLUMN IF NOT EXISTS original_label TEXT,
    ADD COLUMN IF NOT EXISTS normalized_label TEXT,
    ADD COLUMN IF NOT EXISTS raw_data_reference TEXT,
    ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'COMPLETED',
    ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5, 2) DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS risk_band TEXT DEFAULT 'ROUTINE',
    ADD COLUMN IF NOT EXISTS source_account_id TEXT,
    ADD COLUMN IF NOT EXISTS destination_account_id TEXT,
    ADD COLUMN IF NOT EXISTS customer_id TEXT,
    ADD COLUMN IF NOT EXISTS payment_channel TEXT DEFAULT 'TRANSFER',
    ADD COLUMN IF NOT EXISTS dataset_source TEXT,
    ADD COLUMN IF NOT EXISTS event_id TEXT;

-- 3. MODEL VERSIONS
CREATE TABLE IF NOT EXISTS public.model_versions (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    dataset_versions TEXT,
    training_config_json JSONB,
    evaluation_metrics_json JSONB,
    artifact_storage_path TEXT,
    is_active INTEGER DEFAULT 0,
    status TEXT DEFAULT 'REGISTERED',
    promoted_by TEXT,
    promoted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. MODEL PREDICTIONS
CREATE TABLE IF NOT EXISTS public.model_predictions (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES public.transactions(id) ON DELETE CASCADE,
    model_version_id TEXT NOT NULL,
    prediction INTEGER NOT NULL DEFAULT 0,
    risk_score NUMERIC(5, 2) NOT NULL,
    confidence NUMERIC(5, 4),
    detection_reasons JSONB,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. ALERTS
CREATE TABLE IF NOT EXISTS public.alerts (
    id TEXT PRIMARY KEY,
    alert_ref TEXT UNIQUE NOT NULL,
    transaction_id TEXT NOT NULL REFERENCES public.transactions(id) ON DELETE CASCADE,
    account_id TEXT,
    customer_id TEXT,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    alert_type TEXT NOT NULL DEFAULT 'ANOMALOUS_VELOCITY',
    detection_reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW',
    assigned_analyst TEXT,
    risk_score NUMERIC(5, 2) NOT NULL,
    title TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.alerts
    ADD COLUMN IF NOT EXISTS alert_type TEXT DEFAULT 'ANOMALOUS_VELOCITY',
    ADD COLUMN IF NOT EXISTS detection_reason TEXT DEFAULT 'Unusual transaction velocity observed',
    ADD COLUMN IF NOT EXISTS assigned_analyst TEXT;

-- 6. INVESTIGATIONS
CREATE TABLE IF NOT EXISTS public.investigations (
    id TEXT PRIMARY KEY,
    investigation_reference TEXT UNIQUE,
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    priority TEXT NOT NULL DEFAULT 'HIGH',
    status TEXT NOT NULL DEFAULT 'NEW',
    risk_score NUMERIC(5, 2) DEFAULT 0.0,
    assigned_analyst TEXT,
    assigned_investigator_id TEXT,
    disposition TEXT,
    disposition_rationale TEXT,
    findings TEXT,
    evidence_completeness_score NUMERIC(5, 2) DEFAULT 0.0,
    model_version TEXT,
    rule_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.investigations
    ADD COLUMN IF NOT EXISTS investigation_reference TEXT,
    ADD COLUMN IF NOT EXISTS assigned_analyst TEXT,
    ADD COLUMN IF NOT EXISTS findings TEXT;

-- 7. INVESTIGATION TRANSACTIONS (Bridge)
CREATE TABLE IF NOT EXISTS public.investigation_transactions (
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    transaction_id TEXT NOT NULL REFERENCES public.transactions(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (investigation_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS public.investigation_alerts (
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    alert_id TEXT NOT NULL REFERENCES public.alerts(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (investigation_id, alert_id)
);

-- 8. INVESTIGATION EVIDENCE
CREATE TABLE IF NOT EXISTS public.investigation_evidence (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    description TEXT NOT NULL,
    file_path TEXT,
    source TEXT,
    observed_facts_json JSONB,
    verification_status TEXT DEFAULT 'SUPPORTING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. FUND FLOW EDGES
CREATE TABLE IF NOT EXISTS public.fund_flow_edges (
    id TEXT PRIMARY KEY,
    source_account TEXT NOT NULL,
    destination_account TEXT NOT NULL,
    transaction_id TEXT REFERENCES public.transactions(id) ON DELETE CASCADE,
    amount NUMERIC(15, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    timestamp TIMESTAMPTZ NOT NULL,
    edge_type TEXT DEFAULT 'TRANSFER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. ANALYST FEEDBACK
CREATE TABLE IF NOT EXISTS public.analyst_feedback (
    id TEXT PRIMARY KEY,
    transaction_id TEXT,
    investigation_id TEXT,
    model_version_id TEXT,
    original_prediction INTEGER,
    analyst_decision TEXT NOT NULL,
    disposition TEXT,
    feedback_reason TEXT,
    rationale TEXT,
    analyst_id TEXT NOT NULL DEFAULT 'USR-INV-01',
    is_eligible_for_training INTEGER DEFAULT 1,
    training_label INTEGER,
    model_version TEXT,
    evidence_reviewed_count INTEGER DEFAULT 1,
    rule_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. INGESTION JOBS
CREATE TABLE IF NOT EXISTS public.ingestion_jobs (
    id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES public.datasets(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    total_records_discovered BIGINT DEFAULT 0,
    records_processed BIGINT DEFAULT 0,
    records_failed BIGINT DEFAULT 0,
    current_batch INTEGER DEFAULT 0,
    error_details TEXT,
    checkpoint_data JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. REPLAY SESSIONS
CREATE TABLE IF NOT EXISTS public.replay_sessions (
    id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES public.datasets(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'STOPPED',
    processing_speed REAL DEFAULT 1.0,
    current_index BIGINT DEFAULT 0,
    total_records BIGINT DEFAULT 0,
    alerts_generated BIGINT DEFAULT 0,
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_txns_source_acc ON public.transactions(source_account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_txns_dest_acc ON public.transactions(destination_account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_txns_dataset ON public.transactions(dataset_source, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_sev ON public.alerts(severity, status);
CREATE INDEX IF NOT EXISTS idx_edges_src_dest ON public.fund_flow_edges(source_account, destination_account);
CREATE INDEX IF NOT EXISTS idx_feedback_training ON public.analyst_feedback(is_eligible_for_training, training_label);
"""

try:
    print("Connecting to Supabase PostgreSQL to apply production migrations...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(MIGRATION_SQL)
    print("Migrations executed successfully!")
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Total tables in public schema: {len(tables)}")
    for t in tables:
        print(f"  - {t}")
    conn.close()
except Exception as e:
    print("Migration error:", e)
    sys.exit(1)
