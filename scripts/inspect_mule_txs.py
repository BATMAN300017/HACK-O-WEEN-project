import os
import pyarrow.parquet as pq
import pandas as pd

parquet_path = os.path.join('data', 'nfpc', 'part_0001.parquet')
labels_path = os.path.join('data', 'nfpc', 'train_labels.parquet')

df_labels = pq.read_table(labels_path).to_pandas()
mule_accounts = df_labels[df_labels['is_mule'] == 1]
mule_set = set(mule_accounts['account_id'])

# Read account_id column from part_0001
table = pq.read_table(parquet_path, columns=['account_id', 'counterparty_id', 'amount'])
df = table.to_pandas()

# Check source accounts
src_mule_tx = df[df['account_id'].isin(mule_set)]
print("Transactions where source account is a confirmed mule:", len(src_mule_tx))
mules_found_src = src_mule_tx['account_id'].value_counts()
print("Mule source accounts and tx counts:")
print(mules_found_src)

# Check counterparty accounts
dest_mule_tx = df[df['counterparty_id'].isin(mule_set)]
print("\nTransactions where counterparty is a confirmed mule:", len(dest_mule_tx))
mules_found_dest = dest_mule_tx['counterparty_id'].value_counts()
print("Mule counterparty accounts and tx counts:")
print(mules_found_dest)

# Combine both
all_mule_related_tx = df[df['account_id'].isin(mule_set) | df['counterparty_id'].isin(mule_set)]
print(f"\nTotal transactions where EITHER source or dest is a mule: {len(all_mule_related_tx):,}")
