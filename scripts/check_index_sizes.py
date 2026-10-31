import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) as idx_size, pg_relation_size(indexrelid) as idx_bytes
        FROM pg_stat_all_indexes
        WHERE relname = 'transactions'
        ORDER BY pg_relation_size(indexrelid) DESC;
    """)
    for r in cur.fetchall():
        print(f"  {r['indexrelname']}: {r['idx_size']} ({r['idx_bytes']:,} bytes)")
    cur.close()
