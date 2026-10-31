import json

with open('backups/audit_phase2_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== 1. OVERVIEW ===')
print(json.dumps(data['overview'], indent=2))

print('\n=== 2. DATASET COMPLETENESS ===')
for ds in data['dataset_completeness']['transactions_by_source']:
    src = ds['dataset_source']
    accs = data['dataset_completeness']['accounts_by_source'].get(src, 0)
    alerts = data['dataset_completeness']['alerts_by_source'].get(src, 0)
    # Check alias for NFPC / NFPC_MULE
    prot_txns = data['dataset_completeness']['protected_txns_by_dataset'].get(src, 0)
    prot_accs = data['dataset_completeness']['protected_accs_by_dataset'].get(src, 0)
    if src == 'NFPC' and prot_accs == 0:
        prot_accs = data['dataset_completeness']['protected_accs_by_dataset'].get('NFPC_MULE', 0)
    dups = data['dataset_completeness']['duplicates_by_source'].get(src, 0)
    print(f"Dataset {src}: txns={ds['txn_count']}, scored={ds['scored_count']}, unique_accs={accs}, alerts={alerts}, prot_txns={prot_txns}, prot_accs={prot_accs}, dups={dups}, avg_score={ds['avg_score']:.2f}")

print('\n=== 3. ALERTS BREAKDOWN ===')
print('Verdict counts:', data['alerts_investigation']['verdict_counts'])
print('Dataset breakdown:', json.dumps(data['alerts_investigation']['dataset_breakdown'], indent=2))

print('\n=== 4. REGISTRY TABLE METADATA ===')
for r in data['dataset_completeness']['registry_table']:
    print(r['id'], '|', r['name'], '| orig:', r['original_record_count'], '| imported:', r['imported_record_count'], '| status:', r['status'])

print('\n=== 5. BENCHMARK COMPARISON MATRIX ===')
bench = data.get('benchmark_matrix', {})
for ds_k, ds_v in bench.get('datasets', {}).items():
    print(f"\nBenchmark for {ds_k}:")
    print(f"  Granularity: {ds_v.get('evaluation_granularity')}")
    print(f"  Total samples: {ds_v.get('total_evaluated_samples') or ds_v.get('total_evaluated_accounts')}")
    print(f"  Confusion matrix: {ds_v.get('confusion_matrix')}")
    print(f"  Metrics: {ds_v.get('metrics')}")
