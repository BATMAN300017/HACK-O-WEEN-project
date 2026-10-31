import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'transactions'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    print("Columns in transactions table:")
    for c in cols:
        print(f"  {c['column_name']} ({c['data_type']}, nullable={c['is_nullable']})")
    cur.close()
