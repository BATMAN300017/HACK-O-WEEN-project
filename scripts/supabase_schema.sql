-- =========================================================================
-- SentinelFlow AI — Supabase Master PostgreSQL Schema & Storage Initializer
-- Run this script in your Supabase Dashboard: SQL Editor -> New Query -> Run
-- =========================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS & PROFILES (Syncs with Supabase Auth)
CREATE TABLE IF NOT EXISTS public.users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'investigator', -- investigator, senior_investigator, fraud_admin, auditor
    hashed_password TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. CUSTOMERS
CREATE TABLE IF NOT EXISTS public.customers (
    id TEXT PRIMARY KEY,
    customer_ref TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    risk_tier TEXT NOT NULL DEFAULT 'STANDARD', -- LOW, STANDARD, HIGH
    kyc_status TEXT NOT NULL DEFAULT 'VERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. ACCOUNTS
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

-- 4. MERCHANTS
CREATE TABLE IF NOT EXISTS public.merchants (
    id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    category TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. DEVICES
CREATE TABLE IF NOT EXISTS public.devices (
    id TEXT PRIMARY KEY,
    device_fingerprint TEXT UNIQUE NOT NULL,
    device_type TEXT NOT NULL,
    os TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. TRANSACTIONS
CREATE TABLE IF NOT EXISTS public.transactions (
    id TEXT PRIMARY KEY,
    event_id TEXT UNIQUE NOT NULL,
    source_account_id TEXT NOT NULL REFERENCES public.accounts(id),
    destination_account_id TEXT,
    beneficiary_name TEXT,
    customer_id TEXT NOT NULL REFERENCES public.customers(id),
    amount NUMERIC(15, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    transaction_type TEXT NOT NULL,
    payment_channel TEXT NOT NULL,
    merchant_id TEXT,
    device_id TEXT,
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    scenario_id TEXT,
    is_ground_truth_fraud INTEGER DEFAULT 0,
    ground_truth_label TEXT,
    risk_score NUMERIC(5, 2) DEFAULT 0.0,
    risk_band TEXT DEFAULT 'ROUTINE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. ALERTS
CREATE TABLE IF NOT EXISTS public.alerts (
    id TEXT PRIMARY KEY,
    alert_ref TEXT UNIQUE NOT NULL,
    transaction_id TEXT NOT NULL REFERENCES public.transactions(id),
    account_id TEXT NOT NULL REFERENCES public.accounts(id),
    customer_id TEXT NOT NULL REFERENCES public.customers(id),
    severity TEXT NOT NULL DEFAULT 'HIGH', -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'NEW',
    risk_score NUMERIC(5, 2) NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    assigned_to TEXT REFERENCES public.users(id),
    dismissal_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. ALERT FINDINGS
CREATE TABLE IF NOT EXISTS public.alert_findings (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL REFERENCES public.alerts(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    score_contribution NUMERIC(5, 2) NOT NULL,
    feature_values_json JSONB,
    version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. INVESTIGATIONS
CREATE TABLE IF NOT EXISTS public.investigations (
    id TEXT PRIMARY KEY,
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'HIGH',
    status TEXT NOT NULL DEFAULT 'NEW',
    assigned_investigator_id TEXT REFERENCES public.users(id),
    peer_reviewer_id TEXT REFERENCES public.users(id),
    disposition TEXT,
    disposition_rationale TEXT,
    disposition_submitted_at TIMESTAMPTZ,
    peer_review_status TEXT DEFAULT 'NONE',
    peer_review_notes TEXT,
    peer_reviewed_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    evidence_completeness_score NUMERIC(5, 2) DEFAULT 0.0,
    model_version TEXT,
    rule_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. INVESTIGATION ALERTS BRIDGE
CREATE TABLE IF NOT EXISTS public.investigation_alerts (
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    alert_id TEXT NOT NULL REFERENCES public.alerts(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (investigation_id, alert_id)
);

-- 11. EVIDENCE ITEMS (Stores storage attachment links)
CREATE TABLE IF NOT EXISTS public.evidence_items (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    source_record_id TEXT,
    description TEXT NOT NULL,
    observed_facts_json JSONB NOT NULL,
    associated_entities_json JSONB,
    associated_transactions_json JSONB,
    verification_status TEXT NOT NULL DEFAULT 'SUPPORTING',
    collector TEXT NOT NULL,
    integrity_hash TEXT,
    storage_file_path TEXT, -- Link to Supabase Storage file
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. INVESTIGATION TASKS & CHECKLIST
CREATE TABLE IF NOT EXISTS public.investigation_tasks (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_by TEXT,
    completed_at TIMESTAMPTZ,
    evidence_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. INVESTIGATION NOTES
CREATE TABLE IF NOT EXISTS public.investigation_notes (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    author_id TEXT NOT NULL REFERENCES public.users(id),
    content TEXT NOT NULL,
    is_confidential INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. AUDIT EVENTS
CREATE TABLE IF NOT EXISTS public.audit_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_name TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    request_ip TEXT,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS public.notifications (
    id TEXT PRIMARY KEY,
    recipient_user_id TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. DETECTION RULES
CREATE TABLE IF NOT EXISTS public.detection_rules (
    id TEXT PRIMARY KEY,
    rule_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    thresholds_json JSONB NOT NULL,
    lookback_window_minutes INTEGER NOT NULL DEFAULT 60,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================================
-- SUPABASE FILE STORAGE CONFIGURATION
-- =========================================================================

-- Create storage bucket for evidence files & PDF case dossiers
INSERT INTO storage.buckets (id, name, public) 
VALUES ('evidence-files', 'evidence-files', true)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS policy allowing authenticated and service access
CREATE POLICY "Allow public read of evidence files" ON storage.objects
FOR SELECT USING (bucket_id = 'evidence-files');

CREATE POLICY "Allow service uploads to evidence files" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'evidence-files');

-- =========================================================================
-- SEED DEFAULT USERS (Guarantees authentication and foreign keys succeed)
-- =========================================================================
INSERT INTO public.users (id, username, email, full_name, role, is_active)
VALUES 
    ('USR-INV-01', 'sarah_investigator', 'sarah.lin@sentinelflow.bank', 'Sarah Lin', 'investigator', TRUE),
    ('USR-SR-02', 'marcus_senior', 'marcus.vance@sentinelflow.bank', 'Marcus Vance', 'senior_investigator', TRUE),
    ('USR-ADM-03', 'elena_admin', 'elena.rostova@sentinelflow.bank', 'Elena Rostova', 'fraud_admin', TRUE),
    ('USR-AUD-04', 'arthur_auditor', 'arthur.pendelton@sentinelflow.bank', 'Arthur Pendelton', 'auditor', TRUE),
    ('SYSTEM_COPILOT', 'system_copilot', 'copilot@sentinelflow.internal', 'SentinelFlow AI Copilot', 'investigator', TRUE),
    ('USR-SYS-01', 'system_agent', 'agent@sentinelflow.internal', 'Automated Triage Agent', 'investigator', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Index performance optimizations
CREATE INDEX IF NOT EXISTS idx_transactions_src_acc ON public.transactions(source_account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_investigations_status ON public.investigations(status, priority);
