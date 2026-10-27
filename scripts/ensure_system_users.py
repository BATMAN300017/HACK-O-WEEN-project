import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "sentinelflow.db")
db_path = os.path.abspath(db_path)
print(f"Connecting to database at {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ensure SYSTEM_COPILOT exists
cursor.execute("""
INSERT OR IGNORE INTO users (id, username, email, full_name, role, hashed_password, is_active, created_at)
VALUES 
('SYSTEM_COPILOT', 'system_copilot', 'copilot@sentinelflow.bank', 'SentinelFlow AI Copilot', 'investigator', 'pbkdf2_sha256$29000$demo', 1, '2026-01-01T00:00:00Z'),
('USR-SYS-01', 'system_agent', 'agent@sentinelflow.bank', 'Automated Triage Agent', 'investigator', 'pbkdf2_sha256$29000$demo', 1, '2026-01-01T00:00:00Z'),
('USR-INVESTIGATOR-01', 'sarah_investigator_fallback', 'sarah.fallback@sentinelflow.bank', 'Sarah Lin', 'investigator', 'pbkdf2_sha256$29000$demo', 1, '2026-01-01T00:00:00Z')
""")
conn.commit()

cursor.execute("SELECT id, username, role FROM users")
rows = cursor.fetchall()
print("Current users:")
for r in rows:
    print(f" - {r[0]}: {r[1]} ({r[2]})")
conn.close()
