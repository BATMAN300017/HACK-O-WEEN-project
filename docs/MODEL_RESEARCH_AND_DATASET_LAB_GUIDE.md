# SentinelFlow AI — Model Research & Dataset Laboratory Guide

## 1. Dual-Mode Model Promotion Engine

SentinelFlow enforces a strict AI safety and model governance architecture supporting two operational promotion paradigms:

### A. Manual Approval Mode (Default)
In default operational installations, experimental machine learning models are strictly gated by human oversight:
- **Lifecycle Pipeline**:
  $$\text{Trained} \longrightarrow \text{Evaluated} \longrightarrow \text{Awaiting Approval} \longrightarrow \text{Approved} \longrightarrow \text{Active} \longrightarrow \text{Retired}$$
- **Operational Rule**: An experimental or candidate model is **strictly forbidden** from scoring operational records or generating live alerts before receiving formal administrative approval.
- **Audit Logging**: Every promotion action records:
  - Authorized Approver / Actor ID
  - Precise Timestamp (ISO-8601 UTC)
  - Model Version & Checkpoint Hash
  - Independent Evaluation Metrics Snapshot (Precision, Recall, PR-AUC, F1, Sample Count)
  - Approval Decision & Investigative Rationale

### B. Automatic Promotion Mode (Optional, Administrator-Governed)
When enabled by an authorized administrator (`fraud_admin` role), candidate models can be promoted automatically if, and only if, they meet rigorous, non-negotiable evaluation thresholds:
- **Configurable Minimum Evaluation Thresholds**:
  - Minimum Precision $\ge 0.70$ (configurable)
  - Minimum Recall $\ge 0.65$ (configurable)
  - Minimum Precision-Recall AUC (PR-AUC) $\ge 0.75$ (configurable)
  - Maximum False Positive Rate (FPR) $\le 0.05$ (configurable)
  - Minimum F1 Score $\ge 0.70$ (configurable)
  - Minimum Evaluation Sample Count $\ge 20$ (configurable)
- **Independent Validation Mandate**:
  - The evaluation run **must** execute against the independent, held-out evaluation vault (`protected_ground_truth.db`).
  - Evaluating against training-set performance as validation proof is strictly blocked and rejected.
- **Immediate Administrative Kill-Switch**:
  - An administrator can toggle the platform back to `MANUAL` approval mode instantly via `PUT /api/v1/learning/promotion-policy`, revoking automatic promotion across all pipelines.

---

## 2. Multi-Domain Dataset Laboratory (7 Registered Sources)

SentinelFlow maintains strict methodological and domain separation across 7 registered research datasets:

| Dataset ID | Full Title | Domain | License | Primary Analytical Role |
| :--- | :--- | :--- | :--- | :--- |
| **`SAML_D`** | Synthetic AML Monitoring Dataset | `traditional_banking` | Open Data Commons (ODC-By) | Unsupervised baseline, multi-currency conversion, cross-border flows |
| **`NFPC_MULE`** | National Fraud Prevention Council Mule Dataset | `traditional_banking` | Academic Research | Account-level mule network detection, 5-year Indian banking window |
| **`IBM_AML`** | Multi-Bank Synthetic AML Transactions | `traditional_banking` | Apache 2.0 | Cross-institutional money laundering topologies |
| **`PAYSIM`** | PaySim Synthetic Financial Dataset | `mobile_money` | CC BY-SA 4.0 | Mobile money unauthorized balance transfers (**NOT** bank AML) |
| **`ELLIPTIC`** | Elliptic Bitcoin Forensic Graph | `cryptocurrency` | CC BY 4.0 | On-chain Bitcoin graph node classification (**NOT** bank AML) |
| **`AML_SIM`** | IBM AMLSim Parameterized Typologies | `synthetic_simulation` | Apache 2.0 | Configurable AML typologies (`CYCLE`, `FAN_OUT`, `FAN_IN`, `SCATTER_GATHER`) |
| **`INDIA_SIMULATOR`** | Calibrated Indian Banking Ecosystem | `synthetic_simulation` | Proprietary Platform | Micro/macro calibrated against official RBI & NPCI aggregate benchmarks |

---

## 3. Strict Domain Separation & Research Generalization

### Critical Regulatory Distinctions
1. **Mobile Money vs. Traditional Banking**:
   - **PaySim** represents synthetic mobile-money account manipulation (unauthorized `CASH_OUT`, `TRANSFER` balance emptying). It **must not** be conflated with or cross-evaluated against traditional commercial banking AML (SWIFT/Wire/NEFT layering).
2. **Cryptocurrency vs. Traditional Banking**:
   - **Elliptic** represents Bitcoin blockchain unspent transaction output (UTXO) graphs. Evaluating cryptocurrency graph node embeddings against fiat banking accounts without explicit domain adaptation produces severe distributional drift.

### Cross-Dataset Compatibility Matrix
The SentinelFlow Research Compatibility Engine (`POST /api/v1/datasets/evaluate-compatibility`) strictly verifies domain and feature alignment:
- `SAML_D` $\leftrightarrow$ `IBM_AML`: **COMPATIBLE** (Shares fiat multi-bank flow topologies, amounts, and channels).
- `PAYSIM` $\rightarrow$ `SAML_D`: **INCOMPATIBLE** (Blocked: mobile money fraud cannot be used as bank AML benchmark).
- `ELLIPTIC` $\rightarrow$ `SAML_D`: **INCOMPATIBLE** (Blocked: Bitcoin UTXO graph cannot cross-validate fiat accounts).

---

## 4. Zero Label Leakage Architecture

1. **Pipeline Separation**:
   - **Pipeline A (Detection Engine)** receives strictly normalized, label-free transactions (`is_ground_truth_fraud = 0`).
   - **Pipeline B (Protected Evaluation Vault)** routes all ground-truth labels directly to `data/protected_labels/protected_ground_truth.db`.
2. **Audit Verification**:
   - The database enforces `SELECT COUNT(*) FROM transactions WHERE is_ground_truth_fraud != 0 = 0`.
   - Feature engineering, graph centrality metrics, and unsupervised models operate in total isolation from ground truth.
