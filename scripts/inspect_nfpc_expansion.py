import sys
import os
import pyarrow.parquet as pq
import pandas as pd
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

def inspect():
    print("=== STEP 1: PARQUET FILE INSPECTION ===")
    
    # 1. part_0001.parquet
    parquet_path = os.path.join('data', 'nfpc', 'part_0001.parquet')
    if not os.path.exists(parquet_path):
        print(f"ERROR: {parquet_path} does not exist!")
        return

    file_size_bytes = os.path.getsize(parquet_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(f"File exists: {parquet_path}")
    print(f"File size: {file_size_bytes} bytes ({file_size_mb:.2f} MB)")

    pf = pq.ParquetFile(parquet_path)
    num_rows = pf.metadata.num_rows
    num_cols = pf.metadata.num_columns
    print(f"Total Rows: {num_rows}")
    print(f"Total Columns: {num_cols}")
    print(f"Row Groups: {pf.num_row_groups}")
    print("\nParquet Schema:")
    for field in pf.schema_arrow:
        print(f"  - {field.name}: {field.type}")

    # Read a sample of 10,000 to analyze types, nulls, distributions quickly, and first 5 rows
    table_sample = pf.read_row_group(0) # or slice
    df_sample = table_sample.slice(0, 10000).to_pandas()
    print("\nSample Columns & Nulls (first 10,000 rows):")
    for col in df_sample.columns:
        null_count = df_sample[col].isnull().sum()
        print(f"  {col}: {df_sample[col].dtype}, nulls={null_count}")

    print("\nFirst 3 rows:")
    print(df_sample.head(3).to_dict(orient='records'))

    # Read column names across full table or read by batches to get exact stats
    # Let's inspect column names
    cols = pf.schema_arrow.names
    print(f"\nColumns: {cols}")

    # Check accounts.parquet
    accounts_path = os.path.join('data', 'nfpc', 'accounts.parquet')
    if os.path.exists(accounts_path):
        pf_acc = pq.ParquetFile(accounts_path)
        print(f"\naccounts.parquet: {pf_acc.metadata.num_rows} rows, {pf_acc.metadata.num_columns} cols, size {os.path.getsize(accounts_path)/(1024*1024):.2f} MB")
        for field in pf_acc.schema_arrow:
            print(f"  - {field.name}: {field.type}")
        df_acc_sample = pf_acc.read_row_group(0).slice(0, 5).to_pandas()
        print("Sample accounts:", df_acc_sample.to_dict(orient='records'))

    # Check train_labels.parquet
    labels_path = os.path.join('data', 'nfpc', 'train_labels.parquet')
    if os.path.exists(labels_path):
        pf_lab = pq.ParquetFile(labels_path)
        print(f"\ntrain_labels.parquet: {pf_lab.metadata.num_rows} rows, {pf_lab.metadata.num_columns} cols, size {os.path.getsize(labels_path)/(1024*1024):.2f} MB")
        for field in pf_lab.schema_arrow:
            print(f"  - {field.name}: {field.type}")
        df_lab = pf_lab.read().to_pandas()
        print("train_labels value counts:")
        for col in df_lab.columns:
            if col != 'account_id':
                print(f"  {col} distribution:\n{df_lab[col].value_counts()}")

    # Compare with existing Supabase records
    print("\n=== STEP 2: CROSS-REFERENCE WITH SUPABASE ===")
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Check existing NFPC transactions
        cur.execute("SELECT count(*) FROM transactions WHERE dataset_source = 'NFPC'")
        nfpc_count = cur.fetchone()[0]
        print(f"Current Supabase NFPC transactions: {nfpc_count}")

        # Check sample of existing NFPC transactions
        cur.execute("""
            SELECT id, event_id, customer_id, source_account_id, target_account_id, 
                   amount, currency, transaction_type, timestamp, dataset_source, original_tx_id
            FROM transactions 
            WHERE dataset_source = 'NFPC' 
            LIMIT 3
        """)
        rows = cur.fetchall()
        print("Sample existing NFPC transactions in Supabase:")
        for r in rows:
            print(r._dict)

        # Check existing NFPC event_id format and range
        cur.execute("""
            SELECT min(event_id), max(event_id), min(timestamp), max(timestamp), min(amount), max(amount)
            FROM transactions
            WHERE dataset_source = 'NFPC'
        """)
        stats = cur.fetchone()
        print(f"Existing NFPC stats: min_event={stats[0]}, max_event={stats[1]}, min_ts={stats[2]}, max_ts={stats[3]}, min_amt={stats[4]}, max_amt={stats[5]}")

        # Check existing accounts and customers count
        cur.execute("SELECT count(*) FROM accounts")
        total_accounts = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM customers")
        total_customers = cur.fetchone()[0]
        print(f"Total existing accounts in Supabase: {total_accounts}")
        print(f"Total existing customers in Supabase: {total_customers}")

        # Check database table sizes
        cur.execute("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_size_pretty(pg_relation_size(relid)) as table_size,
                pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size,
                pg_total_relation_size(relid) as total_bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC
            LIMIT 10;
        """)
        tables = cur.fetchall()
        print("\nTop Supabase Tables by Storage Size:")
        for t in tables:
            print(f"  {t['table_name']}: total={t['total_size']} (table={t['table_size']}, index={t['index_size']}) [{t['total_bytes']} bytes]")

        # Database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database())), pg_database_size(current_database())")
        db_size_str, db_size_bytes = cur.fetchone()
        print(f"\nTotal Supabase Database Size: {db_size_str} ({db_size_bytes} bytes, {db_size_bytes / (1024*1024):.2f} MB)")

        cur.close()

if __name__ == '__main__':
    inspect()
