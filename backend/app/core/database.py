import sqlite3
import os
import threading
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
from app.core.config import settings
from app.core.logging import logger

_db_lock = threading.Lock()

def get_db_path() -> str:
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        if path.startswith("./"):
            # Resolve relative to backend root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, path[2:])
        return os.path.abspath(path)
    return os.path.abspath("sentinelflow.db")

@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    url = settings.DATABASE_URL
    # Supabase PostgreSQL Direct Connection Support
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return
        except ImportError:
            logger.warning("psycopg2 driver not installed in current environment; using SQLite for local queries while Supabase Auth & Storage remain active.")
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}. Falling back to SQLite.")

    # Local SQLite Connection
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def transaction_scope() -> Generator[sqlite3.Connection, None, None]:
    with _db_lock:
        with get_db_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back due to error: {e}")
                raise

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL, -- investigator, senior_investigator, fraud_admin, auditor
    hashed_password TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    customer_ref TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    risk_tier TEXT NOT NULL DEFAULT 'STANDARD', -- LOW, STANDARD, HIGH
    kyc_status TEXT NOT NULL DEFAULT 'VERIFIED',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_number TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL,
    account_type TEXT NOT NULL DEFAULT 'CHECKING', -- CHECKING, SAVINGS, BUSINESS
    currency TEXT NOT NULL DEFAULT 'USD',
    balance REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, CLOSED
    is_dormant INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS merchants (
    id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    category TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    device_fingerprint TEXT UNIQUE NOT NULL,
    device_type TEXT NOT NULL, -- MOBILE, DESKTOP, TABLET
    os TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    event_id TEXT UNIQUE NOT NULL,
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT,
    beneficiary_name TEXT,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    transaction_type TEXT NOT NULL, -- TRANSFER, CARD_PAYMENT, ATM_WITHDRAWAL, MERCHANT_PAYMENT, REFUND
    payment_channel TEXT NOT NULL, -- ONLINE, MOBILE_APP, ATM, POS, WIRE
    merchant_id TEXT,
    device_id TEXT,
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED', -- COMPLETED, PENDING, FAILED, REVERSED
    scenario_id TEXT,
    is_ground_truth_fraud INTEGER DEFAULT 0, -- STRICTLY SEPARATE DEMO TRUTH
    ground_truth_label TEXT,
    risk_score REAL DEFAULT 0.0,
    risk_band TEXT DEFAULT 'ROUTINE', -- ROUTINE, LOW, ELEVATED, HIGH
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    alert_ref TEXT UNIQUE NOT NULL,
    transaction_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    severity TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'NEW', -- NEW, TRIAGED, IN_REVIEW, DISMISSED, CONVERTED_TO_INVESTIGATION
    risk_score REAL NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    assigned_to TEXT,
    dismissal_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alert_findings (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL,
    source TEXT NOT NULL, -- RULE, ANOMALY, GRAPH, SUPERVISED
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    score_contribution REAL NOT NULL,
    feature_values_json TEXT,
    version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    priority TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'NEW', -- NEW, TRIAGED, IN_PROGRESS, PENDING_INFO, PENDING_PEER_REVIEW, RESOLVED, REOPENED
    assigned_investigator_id TEXT,
    peer_reviewer_id TEXT,
    disposition TEXT, -- CONFIRMED_FRAUD, SUSPICIOUS_UNCONFIRMED, LEGITIMATE_ACTIVITY, INCONCLUSIVE, DUPLICATE_CASE, ESCALATED
    disposition_rationale TEXT,
    disposition_submitted_at TEXT,
    peer_review_status TEXT, -- NONE, REQUESTED, APPROVED, REJECTED
    peer_review_notes TEXT,
    peer_reviewed_at TEXT,
    due_date TEXT,
    evidence_completeness_score REAL DEFAULT 0.0,
    model_version TEXT,
    rule_version TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (assigned_investigator_id) REFERENCES users(id),
    FOREIGN KEY (peer_reviewer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS investigation_alerts (
    investigation_id TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (investigation_id, alert_id),
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE,
    FOREIGN KEY (alert_id) REFERENCES alerts(id)
);

CREATE TABLE IF NOT EXISTS investigation_entities (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    entity_type TEXT NOT NULL, -- CUSTOMER, ACCOUNT, MERCHANT, DEVICE, IP
    entity_id TEXT NOT NULL,
    role_in_case TEXT NOT NULL, -- PRIMARY_SUBJECT, COUNTERPARTY, INTERMEDIARY, BENEFICIARY, SHARED_DEVICE
    added_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investigation_notes (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    content TEXT NOT NULL,
    is_confidential INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS investigation_tasks (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_by TEXT,
    completed_at TEXT,
    evidence_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL, -- TRANSACTION, BEHAVIORAL_ANOMALY, RULE_MATCH, RELATIONSHIP, FUND_FLOW, ACCOUNT_HISTORY, TIMELINE_EVENT, NOTE, CONTRADICTORY
    source_record_id TEXT,
    description TEXT NOT NULL,
    observed_facts_json TEXT NOT NULL,
    associated_entities_json TEXT,
    associated_transactions_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'SUPPORTING', -- SUPPORTING, CONTRADICTORY, UNVERIFIED, NOT_RELEVANT
    collector TEXT NOT NULL, -- AGENT, ANALYST
    integrity_hash TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id TEXT PRIMARY KEY,
    source_entity_type TEXT NOT NULL,
    source_entity_id TEXT NOT NULL,
    target_entity_type TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- OWNS, TRANSFERS_TO, USES_DEVICE, PAYS_MERCHANT, SHARES_BENEFICIARY, SHARES_IP
    weight REAL DEFAULT 1.0,
    metadata_json TEXT,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_events (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    actor_id TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analyst_feedback (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    disposition TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_reviewed_count INTEGER NOT NULL,
    is_eligible_for_training INTEGER NOT NULL, -- Controlled label policy check
    training_label INTEGER, -- 1 for fraud, 0 for false positive, NULL for excluded
    exclusion_reason TEXT,
    model_version TEXT,
    rule_version TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id),
    FOREIGN KEY (analyst_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS detection_rules (
    id TEXT PRIMARY KEY,
    rule_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL, -- VELOCITY, AMOUNT, NETWORK, DEVICE, TEMPORAL
    severity TEXT NOT NULL DEFAULT 'HIGH',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    thresholds_json TEXT NOT NULL,
    lookback_window_minutes INTEGER NOT NULL DEFAULT 60,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detection_rule_versions (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    thresholds_json TEXT NOT NULL,
    modified_by TEXT NOT NULL,
    change_reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES detection_rules(id)
);

CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    version_tag TEXT UNIQUE NOT NULL,
    model_type TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    evaluation_metrics_json TEXT,
    parameters_json TEXT,
    promoted_by TEXT,
    promoted_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_evaluations (
    id TEXT PRIMARY KEY,
    candidate_version TEXT NOT NULL,
    active_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    precision_val REAL,
    recall_val REAL,
    f1_val REAL,
    pr_auc REAL,
    status TEXT NOT NULL, -- PASSED, REJECTED
    reason TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_dataset_versions (
    id TEXT PRIMARY KEY,
    version_tag TEXT UNIQUE NOT NULL,
    sample_count INTEGER NOT NULL,
    positive_count INTEGER NOT NULL,
    negative_count INTEGER NOT NULL,
    features_list_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_name TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    request_ip TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    recipient_user_id TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    scenario_type TEXT NOT NULL, -- RAPID_MOVEMENT, CONNECTED_NETWORK, LEGITIMATE_UNUSUAL, INVESTIGATION_FEEDBACK
    description TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    scenario_id TEXT,
    status TEXT NOT NULL DEFAULT 'IDLE', -- RUNNING, PAUSED, COMPLETED, STOPPED
    events_emitted INTEGER DEFAULT 0,
    alerts_triggered INTEGER DEFAULT 0,
    started_at TEXT,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Essential Performance & Query Indexes
CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(source_account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_txn_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_txn_risk ON transactions(risk_score, risk_band);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_inv_status ON investigations(status, priority);
CREATE INDEX IF NOT EXISTS idx_inv_assignee ON investigations(assigned_investigator_id);
CREATE INDEX IF NOT EXISTS idx_evidence_inv ON evidence_items(investigation_id);
CREATE INDEX IF NOT EXISTS idx_rel_source ON entity_relationships(source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON entity_relationships(target_entity_type, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(created_at);
"""

def init_db():
    logger.info("Initializing SentinelFlow database schema...")
    with get_db_connection() as conn:
        if hasattr(conn, "executescript"):
            conn.executescript(SCHEMA_SQL)
            cursor = conn.cursor()
            # Ensure system users exist for copilot and automated agents
            cursor.execute("SELECT id FROM users WHERE id = 'SYSTEM_COPILOT'")
            if not cursor.fetchone():
                now = "2026-01-01T00:00:00Z"
                cursor.execute("""
                    INSERT OR IGNORE INTO users (id, username, email, full_name, role, hashed_password, is_active, created_at)
                    VALUES 
                    ('SYSTEM_COPILOT', 'system_copilot', 'copilot@sentinelflow.bank', 'SentinelFlow AI Copilot', 'investigator', 'pbkdf2_sha256$29000$demo', 1, ?),
                    ('USR-SYS-01', 'system_agent', 'agent@sentinelflow.bank', 'Automated Triage Agent', 'investigator', 'pbkdf2_sha256$29000$demo', 1, ?),
                    ('USR-INV-01', 'sarah_investigator', 'sarah.lin@sentinelflow.bank', 'Sarah Lin', 'investigator', 'pbkdf2_sha256$29000$demo', 1, ?)
                """, (now, now, now))
            conn.commit()
        else:
            logger.info("Connected to Supabase PostgreSQL database. Schema managed via scripts/supabase_schema.sql.")
    logger.info("Database schema initialized successfully.")
