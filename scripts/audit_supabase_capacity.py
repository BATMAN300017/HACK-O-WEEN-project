import sys
import json
sys.path.insert(0, 'backend')
from app.core.database import get_db_connection

def run_capacity_audit():
    with get_db_connection() as conn:
        cur = conn.cursor()

        # 1. Database version and size
        cur.execute('SELECT version();')
        pg_version = cur.fetchone()[0]

        cur.execute('SELECT pg_size_pretty(pg_database_size(current_database()));')
        db_size_pretty = cur.fetchone()[0]

        cur.execute('SELECT pg_database_size(current_database());')
        db_size_bytes = cur.fetchone()[0]

        # 2. Table sizes
        cur.execute("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_table_size(c.oid)) as table_size,
                pg_size_pretty(pg_indexes_size(c.oid)) as indexes_size,
                pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
                pg_total_relation_size(c.oid) as total_size_bytes,
                reltuples::bigint as approx_rows
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            ORDER BY pg_total_relation_size(c.oid) DESC;
        """)
        tables = [dict(r) for r in cur.fetchall()]

        # 3. Indexes on transactions
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'transactions';
        """)
        txn_indexes = [dict(r) for r in cur.fetchall()]

        # 4. Constraints on transactions
        cur.execute("""
            SELECT conname, contype, pg_get_constraintdef(c.oid) as def
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'transactions';
        """)
        txn_constraints = [dict(r) for r in cur.fetchall()]

        # 5. Connection limits and activity
        cur.execute('SHOW max_connections;')
        max_conn = cur.fetchone()[0]
        cur.execute('SHOW statement_timeout;')
        stmt_timeout = cur.fetchone()[0]
        cur.execute('SHOW work_mem;')
        work_mem = cur.fetchone()[0]
        cur.execute('SELECT count(*) FROM pg_stat_activity;')
        current_conn = cur.fetchone()[0]

        print('=== SUPABASE DATABASE CAPACITY METRICS ===')
        print('PostgreSQL Version:', pg_version[:80])
        print(f'Total DB Size: {db_size_pretty} ({db_size_bytes:,} bytes)')
        print(f'Max Connections: {max_conn} | Active Connections: {current_conn}')
        print(f'Statement Timeout: {stmt_timeout} | Work Mem: {work_mem}')
        print('\n=== PUBLIC TABLES STORAGE ===')
        for t in tables:
            print(f" - {t['table_name']}: Total={t['total_size']} (Data={t['table_size']}, Indexes={t['indexes_size']}) Approx Rows={t['approx_rows']:,}")

        print('\n=== TRANSACTIONS INDEXES ===')
        for i in txn_indexes:
            print(f" - {i['indexname']}: {i['indexdef']}")

        print('\n=== TRANSACTIONS CONSTRAINTS ===')
        for c in txn_constraints:
            print(f" - {c['conname']} ({c['contype']}): {c['def']}")

        # Average row size of transactions
        cur.execute("SELECT pg_total_relation_size('transactions') / GREATEST(1, COUNT(*)) as avg_bytes_per_row FROM transactions;")
        avg_row_bytes = cur.fetchone()[0]
        print(f"\nAverage storage per transaction record (Data + Indexes): {avg_row_bytes} bytes")

if __name__ == '__main__':
    run_capacity_audit()
