import sys
import os
import pyarrow.parquet as pq
import pyarrow.compute as pc
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

def run_deep_inspection():
    print("=== DEEP INSPECTION OF NFPC DATA & SUPABASE STATE ===")
    
    # 1. Inspect existing Supabase NFPC transactions
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, event_id, customer_id, source_account_id, destination_account_id,
                   amount, currency, transaction_type, payment_channel, status,
                   dataset_source, dataset_id, original_transaction_id, transaction_timestamp,
                   is_ground_truth_fraud, ground_truth_label
            FROM transactions 
            WHERE dataset_source = 'NFPC' 
            ORDER BY created_at ASC
            LIMIT 5;
        """)
        sample_existing = cur.fetchall()
        print("\n--- Existing Supabase NFPC Transactions (First 5) ---")
        for r in sample_existing:
            print(r._dict)

        # Get existing NFPC original_transaction_ids or event_ids
        cur.execute("""
            SELECT count(*) as cnt, 
                   min(original_transaction_id) as min_orig, 
                   max(original_transaction_id) as max_orig,
                   min(event_id) as min_evt, 
                   max(event_id) as max_evt,
                   min(id) as min_id,
                   max(id) as max_id
            FROM transactions
            WHERE dataset_source = 'NFPC';
        """)
        db_nfpc_stats = cur.fetchone()
        print(f"\nExisting DB NFPC Count: {db_nfpc_stats['cnt']}")
        print(f"Original TX ID Range: {db_nfpc_stats['min_orig']} to {db_nfpc_stats['max_orig']}")
        print(f"Event ID Range: {db_nfpc_stats['min_evt']} to {db_nfpc_stats['max_evt']}")
        print(f"ID Range: {db_nfpc_stats['min_id']} to {db_nfpc_stats['max_id']}")

        # Check existing NFPC account IDs
        cur.execute("""
            SELECT count(DISTINCT source_account_id) as src_cnt, 
                   count(DISTINCT destination_account_id) as dest_cnt, 
                   count(DISTINCT customer_id) as cust_cnt
            FROM transactions
            WHERE dataset_source = 'NFPC';
        """)
        acc_stats = cur.fetchone()
        print(f"Unique source accounts in DB (NFPC): {acc_stats['src_cnt']}")
        print(f"Unique destination accounts in DB (NFPC): {acc_stats['dest_cnt']}")
        print(f"Unique customers in DB (NFPC): {acc_stats['cust_cnt']}")

        # Check dataset registry entry for NFPC
        cur.execute("SELECT id, name, source, domain, original_record_count, imported_record_count, status FROM datasets WHERE id = 'NFPC' OR name ILIKE '%nfpc%';")
        dataset_row = cur.fetchone()
        print(f"\nDataset registry row for NFPC: {dataset_row._dict if dataset_row else 'None'}")
        dataset_id = dataset_row['id'] if dataset_row else None

        # Check table sizes
        cur.execute("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_size_pretty(pg_relation_size(relid)) as table_size,
                pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size,
                pg_total_relation_size(relid) as total_bytes,
                pg_relation_size(relid) as table_bytes,
                (pg_total_relation_size(relid) - pg_relation_size(relid)) as index_bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC;
        """)
        all_tables = cur.fetchall()
        print("\n--- Supabase User Tables Storage ---")
        for t in all_tables:
            print(f"  {t['table_name']}: Total={t['total_size']}, Data={t['table_size']}, Index={t['index_size']} ({t['total_bytes']:,} B)")

        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database())), pg_database_size(current_database())")
        db_size_str, db_size_bytes = cur.fetchone()
        print(f"\nTotal Database Size: {db_size_str} ({db_size_bytes:,} bytes, {db_size_bytes/(1024*1024):.2f} MB)")

        cur.close()

    # 2. Inspect Parquet part_0001.parquet in full
    print("\n--- Parquet part_0001.parquet In-Depth Stats ---")
    parquet_path = os.path.join('data', 'nfpc', 'part_0001.parquet')
    table = pq.read_table(parquet_path)
    total_parquet_rows = len(table)
    print(f"Parquet Total Rows: {total_parquet_rows:,}")

    # Convert columns to pandas / pyarrow to analyze
    tx_ids = table.column('transaction_id').to_pandas()
    acct_ids = table.column('account_id').to_pandas()
    cp_ids = table.column('counterparty_id').to_pandas()
    amounts = table.column('amount').to_pandas()
    timestamps = table.column('transaction_timestamp').to_pandas()
    channels = table.column('channel').to_pandas()
    txn_types = table.column('txn_type').to_pandas()
    mcc_codes = table.column('mcc_code').to_pandas()

    num_unique_tx = tx_ids.nunique()
    num_unique_accts = acct_ids.nunique()
    num_unique_cps = cp_ids.nunique()
    print(f"Unique transaction_ids: {num_unique_tx:,} (Duplicates: {total_parquet_rows - num_unique_tx})")
    print(f"Unique account_ids: {num_unique_accts:,}")
    print(f"Unique counterparty_ids: {num_unique_cps:,}")
    print(f"Min tx_id: {tx_ids.min()}, Max tx_id: {tx_ids.max()}")
    print(f"Min timestamp: {timestamps.min()}, Max timestamp: {timestamps.max()}")
    print(f"Min amount: {amounts.min():.2f}, Max amount: {amounts.max():.2f}, Mean amount: {amounts.mean():.2f}, Median: {amounts.median():.2f}")
    print(f"Amount <= 0 count: {(amounts <= 0).sum()}")
    print(f"Channel distribution:\n{channels.value_counts()}")
    print(f"Txn Type distribution:\n{txn_types.value_counts()}")
    print(f"MCC code unique: {mcc_codes.nunique()}, min: {mcc_codes.min()}, max: {mcc_codes.max()}")

    # Null checks across all columns
    print("\nParquet Null Counts:")
    for col in table.column_names:
        null_cnt = table.column(col).null_count
        print(f"  {col}: {null_cnt} nulls ({null_cnt/total_parquet_rows*100:.2f}%)")

    # Check the first 25,000 rows vs existing Supabase records
    first_25k_tx_ids = set(tx_ids.iloc[:25000])
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, event_id FROM transactions WHERE dataset_source = 'NFPC';")
        db_rows = cur.fetchall()
        existing_tx_ids = set(r['id'] for r in db_rows if r['id'])
        existing_event_ids = set(r['event_id'] for r in db_rows if r['event_id'])
        cur.close()

    overlap_25k = len(first_25k_tx_ids.intersection(existing_tx_ids))
    print(f"\nOverlap between first 25,000 parquet rows and existing DB tx ids: {overlap_25k} / 25,000")

    # Check total overlap of full 1,000,000 with existing DB
    all_parquet_tx_ids = set(tx_ids)
    total_overlap = len(all_parquet_tx_ids.intersection(existing_tx_ids))
    print(f"Total overlap between parquet (1M) and existing DB tx ids: {total_overlap} / {len(existing_tx_ids)}")
    new_unique_transactions = total_parquet_rows - total_overlap
    print(f"Net NEW unique transactions in part_0001.parquet: {new_unique_transactions:,}")

    # 3. Cross-reference with accounts.parquet and train_labels.parquet
    print("\n--- Cross-Reference with accounts.parquet and train_labels.parquet ---")
    acc_table = pq.read_table(os.path.join('data', 'nfpc', 'accounts.parquet'))
    all_known_accounts = set(acc_table.column('account_id').to_pylist())
    print(f"Total accounts in accounts.parquet: {len(all_known_accounts):,}")

    parquet_accts_set = set(acct_ids.unique())
    missing_accts_in_accounts_parquet = parquet_accts_set - all_known_accounts
    print(f"Unique accounts in part_0001.parquet: {len(parquet_accts_set):,}")
    print(f"Accounts in part_0001.parquet missing from accounts.parquet: {len(missing_accts_in_accounts_parquet)}")

    labels_df = pq.read_table(os.path.join('data', 'nfpc', 'train_labels.parquet')).to_pandas()
    mule_accounts = set(labels_df[labels_df['is_mule'] == 1]['account_id'])
    legit_accounts = set(labels_df[labels_df['is_mule'] == 0]['account_id'])
    print(f"Total mule accounts in train_labels: {len(mule_accounts):,}")
    print(f"Total legit accounts in train_labels: {len(legit_accounts):,}")

    mules_in_part1 = parquet_accts_set.intersection(mule_accounts)
    legit_in_part1 = parquet_accts_set.intersection(legit_accounts)
    unlabeled_in_part1 = parquet_accts_set - mule_accounts - legit_accounts
    print(f"Mule accounts present in part_0001.parquet: {len(mules_in_part1):,} / {len(mule_accounts):,}")
    print(f"Legit accounts present in part_0001.parquet: {len(legit_in_part1):,} / {len(legit_accounts):,}")
    print(f"Unlabeled accounts present in part_0001.parquet: {len(unlabeled_in_part1):,}")

    # Count transactions associated with mule accounts
    is_mule_mask = acct_ids.isin(mule_accounts)
    mule_tx_count = is_mule_mask.sum()
    print(f"Total transactions in part_0001.parquet associated with known mule accounts: {mule_tx_count:,} ({mule_tx_count/total_parquet_rows*100:.2f}%)")

if __name__ == '__main__':
    run_deep_inspection()
