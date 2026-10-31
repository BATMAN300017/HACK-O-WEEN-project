import sqlite3
import os
import threading
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
from app.core.config import settings
from app.core.logging import logger

_db_lock = threading.Lock()

class AdaptiveRow:
    """Provides dual access by column name (dict-like) and index (tuple-like), matching sqlite3.Row exactly."""
    def __init__(self, data_dict):
        self._dict = dict(data_dict) if isinstance(data_dict, dict) else {}
        self._tuple = tuple(data_dict.values()) if isinstance(data_dict, dict) else tuple(data_dict or ())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._tuple[key]
        return self._dict[key]

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __iter__(self):
        return iter(self._tuple)

    def __len__(self):
        return len(self._dict)

    def __contains__(self, key):
        return key in self._dict

    def __repr__(self):
        return repr(self._dict)

class PostgresCursorWrapper:
    """Wraps psycopg2 cursor to automatically translate '?' placeholders, handle PRAGMAs, and return AdaptiveRow."""
    def __init__(self, cursor):
        self._cur = cursor

    def __getattr__(self, name):
        return getattr(self._cur, name)

    def _transform_query(self, query: str) -> str:
        clean = query.strip()
        if clean.upper().startswith("INSERT OR IGNORE INTO"):
            query = "INSERT INTO" + clean[len("INSERT OR IGNORE INTO"):]
            if "ON CONFLICT" not in query.upper():
                query = query.rstrip("; \n\t") + " ON CONFLICT DO NOTHING"
        elif clean.upper().startswith("INSERT OR REPLACE INTO"):
            query = "INSERT INTO" + clean[len("INSERT OR REPLACE INTO"):]
            if "ON CONFLICT" not in query.upper():
                query = query.rstrip("; \n\t") + " ON CONFLICT DO NOTHING"
        if "?" in query:
            query = query.replace("?", "%s")
        return query

    def execute(self, query, params=None):
        if query.strip().upper().startswith("PRAGMA"):
            return None
        query = self._transform_query(query)
        if params is None:
            return self._cur.execute(query)
        return self._cur.execute(query, params)

    def executemany(self, query, seq_of_params):
        if query.strip().upper().startswith("PRAGMA"):
            return None
        query = self._transform_query(query)
        return self._cur.executemany(query, seq_of_params)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return AdaptiveRow(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        return [AdaptiveRow(r) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()
        return [AdaptiveRow(r) for r in rows]

class PostgresConnectionWrapper:
    """Wraps psycopg2 connection to return wrapped cursors for SQLite parameter compatibility."""
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def cursor(self, *args, **kwargs):
        cur = self._conn.cursor(*args, **kwargs)
        return PostgresCursorWrapper(cur)

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
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=15)
            wrapped = PostgresConnectionWrapper(conn)
            try:
                yield wrapped
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
def transaction_scope() -> Generator[Any, None, None]:
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
    created_at TEXT NOT NULL
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
    device_type TEXT NOT NULL,
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
    transaction_type TEXT NOT NULL,
    payment_channel TEXT NOT NULL,
    merchant_id TEXT,
    device_id TEXT,
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    scenario_id TEXT,
    dataset_source TEXT DEFAULT 'SAML_D',
    is_ground_truth_fraud INTEGER DEFAULT 0,
    ground_truth_label TEXT,
    risk_score REAL DEFAULT 0.0,
    risk_band TEXT DEFAULT 'ROUTINE',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    alert_ref TEXT UNIQUE NOT NULL,
    transaction_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    severity TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'NEW',
    risk_score REAL NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    assigned_to TEXT,
    dismissal_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    priority TEXT NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    status TEXT NOT NULL DEFAULT 'NEW',
    assigned_investigator_id TEXT,
    peer_reviewer_id TEXT,
    disposition TEXT,
    disposition_rationale TEXT,
    disposition_submitted_at TEXT,
    peer_review_status TEXT DEFAULT 'NONE',
    peer_review_notes TEXT,
    peer_reviewed_at TEXT,
    due_date TEXT,
    evidence_completeness_score REAL DEFAULT 0.0,
    model_version TEXT,
    rule_version TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_alerts (
    investigation_id TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (investigation_id, alert_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    source_record_id TEXT,
    description TEXT NOT NULL,
    observed_facts_json TEXT NOT NULL,
    associated_entities_json TEXT,
    associated_transactions_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'SUPPORTING',
    collector TEXT NOT NULL,
    integrity_hash TEXT,
    storage_file_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_tasks (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_by TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_notes (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    content TEXT NOT NULL,
    is_confidential INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyst_feedback (
    id TEXT PRIMARY KEY,
    investigation_id TEXT,
    transaction_id TEXT,
    analyst_id TEXT NOT NULL,
    disposition TEXT NOT NULL,
    rationale TEXT,
    evidence_reviewed_count INTEGER DEFAULT 1,
    is_eligible_for_training INTEGER DEFAULT 1,
    training_label INTEGER,
    exclusion_reason TEXT,
    model_version TEXT,
    rule_version TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detection_rules (
    id TEXT PRIMARY KEY,
    rule_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    thresholds_json TEXT NOT NULL,
    lookback_window_minutes INTEGER NOT NULL DEFAULT 60,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    version_tag TEXT NOT NULL,
    model_type TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    evaluation_metrics_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    promoted_by TEXT,
    promoted_at TEXT,
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
"""

def init_db():
    logger.info("Initializing SentinelFlow database schema...")
    with get_db_connection() as conn:
        if hasattr(conn, "executescript"):
            conn.executescript(SCHEMA_SQL)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(transactions)")
            txn_cols = [c[1] for c in cursor.fetchall()]
            if "dataset_source" not in txn_cols:
                cursor.execute("ALTER TABLE transactions ADD COLUMN dataset_source TEXT DEFAULT 'INDIA_SIMULATOR'")
            conn.commit()
        else:
            logger.info("Connected to Supabase PostgreSQL database. Schema managed via migrations.")
    logger.info("Database schema initialized successfully.")
