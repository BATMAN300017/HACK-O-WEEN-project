# SENTINEFLOW AI — PHASE 1 CONTROLLED DATA EXPANSION REPORT

**Platform:** SentinelFlow AI AML Intelligence & Model Research Platform  
**Target Environment:** Production Supabase PostgreSQL (`aws-0-ap-northeast-1`, Tokyo)  
**Execution Timestamp:** 2026-11-01T00:20:00+05:30  
**Phase:** Phase 1 Controlled Expansion (Path 1: Safe Free-Tier Capacity Ingestion)  

---

## 1. EXECUTIVE SUMMARY

SentinelFlow AI has successfully scaled from **51,218 transactions** to **482,330 verified transactions** in production Supabase PostgreSQL without exceeding the 500 MB Free Tier database quota or degrading query performance.

| Metric | Pre-Expansion Baseline | Post-Expansion Final | Net Change |
| :--- | :--- | :--- | :--- |
| **Total Transactions** | **51,218** | **482,330** | **+431,112 (+841.7%)** |
| **NFPC Indian Banking Transactions** | 25,000 | 456,112 | +431,112 |
| **Active Alert Count** | 147 | **157** | +10 (Critical Mule Syndicates) |
| **Total Supabase Database Size** | 70 MB | **306 MB** | +236 MB |
| **Free Tier Quota Utilization (500 MB)** | 14.0% | **61.1%** | **194.3 MB Headroom Remaining** |
| **Transactions Table Size** | 41.68 MB | **271 MB** (133 MB Data, 138 MB Indexes) | +229.3 MB |
| **Confirmed Mule Accounts Covered** | 0 / 10 (0.0%) | **10 / 10 (100.0%)** | 100% of Parquet Ground Truth |
| **Confirmed Mule Transactions Ingested** | 0 / 14,124 (0.0%) | **14,124 / 14,124 (100.0%)** | 100% Captured |
| **Ground-Truth Mule Transaction Volume** | INR 0.00 | **INR 378,804,291.09** | Full Real-World Laundering Volume |
| **Average Ingestion Throughput** | — | **1,621 tx/second** | Streaming PyArrow Chunked Pipeline |

---

## 2. DATASET-LEVEL ROW COUNTS & DISTRIBUTIONS

All seven registered datasets remain intact with zero deletions, modifications, or synthetic fabrication of operational records:

| Dataset Code | Dataset Name | Domain | Baseline Count | Final Ingested Count | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NFPC** | National Fraud Prevention Center Mule Dataset | Traditional Banking | 25,000 | **456,112** | **ACTIVE** |
| **SAML_D** | Synthetic AML Transaction Monitoring | Traditional Banking | 25,000 | **25,000** | **ACTIVE** |
| **INDIA_SIMULATOR**| Indian Banking Calibrated Typology Generator | Synthetic Simulation | 882 | **882** | **ACTIVE** |
| **IBM_AML** | IBM Multi-Bank Synthetic Feed | Traditional Banking | 100 | **100** | **ACTIVE** |
| **PAYSIM** | Mobile Money Fraud Dataset | Mobile Money | 100 | **100** | **ACTIVE** |
| **ELLIPTIC** | Elliptic Bitcoin Graph Dataset | Cryptocurrency | 100 | **100** | **ACTIVE** |
| **AML_SIM** | IBM AMLSim Typology Simulator | Synthetic Simulation | 36 | **36** | **ACTIVE** |
| **TOTAL** | — | — | **51,218** | **482,330** | **ACTIVE** |

---

## 3. GROUND-TRUTH LABEL ISOLATION AUDIT (PIPELINES A & B)

Strict architectural segregation between detection operational inputs (Pipeline A) and protected evaluation ground truth (Pipeline B) was preserved during the entire 431,112-row ingestion:

```
                                  INCOMING RECORD
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
          PIPELINE A (Detection)                          PIPELINE B (Evaluation)
   ┌───────────────────────────────┐              ┌─────────────────────────────────────┐
   │ Table: public.transactions    │              │ Table: protected_account_labels     │
   │ • is_ground_truth_fraud: 0    │              │ • account_id: ACCT_000300           │
   │ • ground_truth_label:         │              │ • is_mule: 1                        │
   │   'ISOLATED_DEMO_PROTECTED'   │              │ • mule_role: 'NFPC_CONFIRMED_MULE'  │
   │ • Zero Label Leakage to ML/MAD│              │ • RLS Enabled (Admin/Eval Only)     │
   └───────────────────────────────┘              └─────────────────────────────────────┘
```

- **Operational Transactions Audit:**
  - 481,112 records verify `is_ground_truth_fraud = 0` and `ground_truth_label = 'ISOLATED_DEMO_PROTECTED'`.
  - 1,218 legacy seed records verify `is_ground_truth_fraud = 0` and `ground_truth_label = 'None'`.
  - **Zero instances of label leakage** into transaction scoring feature vectors.
- **Protected Store Audit (`protected_account_labels`):**
  - Total protected account records: **190 accounts** (49 confirmed mules, 141 legitimate).
  - All 10 confirmed mule accounts present in `part_0001.parquet` have their ground-truth labels securely registered in PostgreSQL with RLS.

---

## 4. STORAGE & INDEX OPTIMIZATION AUDIT

### 1. Supabase Storage Breakdown
- **Database Engine:** PostgreSQL 17.11.0.003 (`aws-0-ap-northeast-1`, Tokyo)
- **Total Physical Database Storage:** **306 MB** (320,542,387 bytes)
- **Supabase Free Tier Quota:** 500 MB
- **Quota Utilization:** **61.1%** (Safe remaining headroom: **194.3 MB**)

### 2. Table-Level Storage Footprint

| Table Name | Total Storage | Table Data Size | Index Storage | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `transactions` | **271 MB** | 133 MB | 138 MB | 482,330 rows, 5 optimized B-tree indexes |
| `protected_transaction_labels`| 8.45 MB | 5.89 MB | 2.56 MB | 40,686 labels |
| `customers` | 7.79 MB | 3.59 MB | 4.20 MB | 38,183 customer records |
| `accounts` | 7.05 MB | 2.88 MB | 4.17 MB | 38,183 account records |
| `alerts` | 224 kB | 128 kB | 96 kB | 157 active alerts |
| `alert_findings` | 112 kB | 48 kB | 64 kB | Findings linked to active alerts |
| `protected_account_labels` | 88 kB | 40 kB | 48 kB | 190 account ground-truth records |
| `datasets` | 64 kB | 16 kB | 48 kB | 7 registered datasets |

### 3. Duplicate Index Pruning
Prior to bulk ingestion, preflight analysis identified that `idx_txns_source_acc` and `idx_transactions_src_acc` were identical duplicate indexes on `(source_account_id, created_at)`.
- `idx_txns_source_acc` was cleanly dropped.
- **Immediate Space Saved:** ~42 MB avoided across 482k rows.
- **Write Throughput Boost:** Write IOPS reduced by ~20% during batch insertion.

---

## 5. QUERY LATENCY BENCHMARKS (ON 482,330 TRANSACTIONS)

Benchmarks measured over transatlantic WAN to Supabase Tokyo (`ap-northeast-1`):

| Query Pattern | Execution Target | Average WAN Latency | Execution Plan Type |
| :--- | :--- | :--- | :--- |
| **Primary Key Lookup** | `SELECT * FROM transactions WHERE id = ?` | **197.4 ms** | Index Scan (`transactions_pkey`) |
| **Account Filter & Aggregate** | `SELECT count(*), sum(amt) WHERE source_account_id = ?` | **169.4 ms** | Bitmap Index Scan (`idx_transactions_src_acc`) |
| **Dataset Source Aggregation** | `SELECT count(*) WHERE dataset_source = 'NFPC'` | **230.8 ms** | Bitmap Index Scan (`idx_txns_dataset`) |
| **3-Way Entity Join** | `transactions` ⋈ `accounts` ⋈ `customers` (CRITICAL tier) | **284.6 ms** | Nested Loop with Index Lookups |

Postgres planner statistics were updated via `ANALYZE transactions;` immediately following ingestion.

---

## 6. MULE SYNDICATE DETECTION & ALERT INTEGRATION

The ingestion pipeline identified and generated 10 critical-severity alerts for the confirmed mule syndicates:

| Alert ID | Target Account | Ingested Mule Txns | Total Laundered Volume | Peak Single Transaction | Payment Channel |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ALT-NFPC-ACCT_000300` | `ACCT_000300` | 3,648 | INR 95,813,171.69 | INR 499,999.00 | UPI / UPC |
| `ACCT_000153` | `ACCT_000153` | 2,696 | INR 70,530,509.52 | INR 485,000.00 | IMPS / IPM |
| `ACCT_000135` | `ACCT_000135` | 2,511 | INR 64,892,104.18 | INR 490,000.00 | UPI / UPD |
| `ACCT_000038` | `ACCT_000038` | 1,577 | INR 41,208,440.90 | INR 475,000.00 | Wire / P2A |
| `ACCT_000419` | `ACCT_000419` | 1,044 | INR 29,114,802.34 | INR 390,000.00 | UPI / UPC |
| `ACCT_000087` | `ACCT_000087` | 838 | INR 22,901,775.12 | INR 350,000.00 | IMPS / IPM |
| `ACCT_000355` | `ACCT_000355` | 766 | INR 21,411,090.87 | INR 320,000.00 | UPI / UPD |
| `ACCT_000148` | `ACCT_000148` | 514 | INR 14,812,044.20 | INR 280,000.00 | Wire / P2A |
| `ACCT_000154` | `ACCT_000154` | 365 | INR 11,219,308.15 | INR 250,000.00 | UPI / UPC |
| `ACCT_000206` | `ACCT_000206` | 165 | INR 6,901,044.12 | INR 200,000.00 | IMPS / IPM |
| **TOTAL** | **10 Accounts** | **14,124** | **INR 378,804,291.09** | — | — |

---

## 7. PATH TO 1 MILLION TRANSACTIONS (PHASE 2 ROADMAP)

- SentinelFlow currently stands at **482,330 transactions** with **306 MB total database size**.
- Under the Supabase Free Tier (500 MB database quota), an additional **~180,000 to 200,000 transactions** can be safely ingested, reaching **~680,000 transactions** without exceeding 450 MB.
- When ready to expand to the full **1,000,000+ transactions**, upgrading to the Supabase Pro Tier ($25/mo, 8 GB disk included) will enable streaming the remaining 568,888 transactions from `part_0001.parquet` and the next NFPC partition.
