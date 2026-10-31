import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("--- Foreign Keys on transactions ---")
    cur.execute("""
        SELECT
            tc.table_schema, 
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND tc.table_name = 'transactions';
    """)
    for r in cur.fetchall():
        print(f"  {r['column_name']} -> {r['foreign_table_name']}({r['foreign_column_name']}) [{r['constraint_name']}]")

    print("\n--- Unique Constraints & Primary Keys on transactions ---")
    cur.execute("""
        SELECT tc.constraint_type, tc.constraint_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'transactions';
    """)
    for r in cur.fetchall():
        print(f"  {r['constraint_type']}: {r['column_name']} [{r['constraint_name']}]")

    print("\n--- Indexes on transactions ---")
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'transactions';
    """)
    for r in cur.fetchall():
        print(f"  {r['indexname']}: {r['indexdef']}")

    print("\n--- Columns in accounts ---")
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'accounts'
        ORDER BY ordinal_position;
    """)
    for r in cur.fetchall():
        print(f"  {r['column_name']} ({r['data_type']}, nullable={r['is_nullable']})")

    print("\n--- Columns in customers ---")
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'customers'
        ORDER BY ordinal_position;
    """)
    for r in cur.fetchall():
        print(f"  {r['column_name']} ({r['data_type']}, nullable={r['is_nullable']})")

    cur.close()
