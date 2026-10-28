# HACK-O-WEEN-project

# SentinelFlow AI — The Self-Directed Fraud Investigation Platform

[![CI Pipeline](https://github.com/BATMAN300017/HACK-O-WEEN-project/actions/workflows/ci.yml/badge.svg)](https://github.com/BATMAN300017/HACK-O-WEEN-project/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4+-orange.svg)](https://scikit-learn.org/)

> **SentinelFlow AI** is a production-inspired financial crime surveillance and self-directed fraud investigation command center. It bridges the gap between raw anomaly detection and final authorized case disposition.

---

## 1. Product Vision & Core Architecture

In modern financial crime and anti-money laundering (AML) operations, over 90% of alerts are false positives. Existing tools either act as opaque binary classifiers or dump raw tables onto overworked analysts.

SentinelFlow AI transforms the investigative process through four foundational pillars:

```mermaid
flowchart TD
    subgraph Surveillance["1. Continuous Surveillance"]
        T[Transaction Ingestion] --> IDEM[Idempotency Check]
        IDEM --> DB[(Persistent Store)]
    end

    subgraph Detection["2. Hybrid Multi-Signal Engine"]
        DB --> RULES[Explainable Rules (30%)]
        DB --> ANOM[Account Rolling MAD Baseline (25%)]
        DB --> ML[Supervised Logistic Regression (25%)]
        DB --> GRAPH[Graph Topology Signals (20%)]
        RULES & ANOM & ML & GRAPH --> ENS[Calibrated Risk Ensemble (0-100)]
    end

    subgraph Agent["3. Self-Directed Investigation Agent"]
        ENS -->|Risk >= 70| ORCH[13-Step Automated Orchestrator]
        ORCH --> EVD[Typed Evidence Generation (SHA-256 Hash)]
        ORCH --> SUBG[Multi-Hop Counterparty Sub-Graph]
        ORCH --> CHK[Procedural Playbook Checklist]
        ORCH --> COPILOT[Evidence-Grounded AI Copilot]
    end

    subgraph Governance["4. Human-In-The-Loop Learning"]
        CHK & EVD --> CASE[Analyst Workbench]
        CASE --> DISP[Audited Disposition]
        DISP --> PEER[Senior Peer Review Gate]
        PEER --> POLICY[Controlled Label Policy]
        POLICY --> CAND[Candidate Model Training & Holdout Gate]
        CAND --> PROMO[Admin Promotion]
    end
```

---

## 2. Differentiators

- **Investigation System, Not Just a Classifier**: Alerts automatically construct a formal case dossier with verified supporting and contradictory evidence.
- **Account-Specific MAD Anomaly Baselines**: Uses Median Absolute Deviation (MAD) robust z-scores rather than naive static amount cutoffs.
- **Topological Graph Intelligence**: Detects fan-in collection hubs, circular flow cycles, and rapid multi-hop mule forwarding.
- **Controlled Continuous Learning**: Enforces a strict label policy—only human-reviewed confirmed fraud and verified false positives enter the training pipeline. Inconclusive and unconfirmed cases are excluded to prevent feedback poisoning.
- **Zero Paid Dependencies**: Runs 100% locally with deterministic synthetic data, offline model training, and built-in interactive dashboard.

---

## 3. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, Scikit-learn, NumPy, Pandas, SciPy, and SQLite. PostgreSQL is not currently implemented.
- **Security**: PBKDF2-SHA256 password hashing, HMAC bearer tokens, sensitive-field redaction in structured JSON logs.
- **Frontend / UI**: Responsive Next.js / TypeScript dashboard with Tailwind CSS, SVG money-flow graphs, and real-time SSE telemetry in `frontend/`.
- **Testing**: Backend pytest tests and frontend Vitest tests run in GitHub Actions. Additional detection and workflow coverage remains to be added.

---

## 4. Quick Start & Launch

### Prerequisites
- Python 3.11+, Node.js 20+, and npm
- A virtual environment is recommended

### Run locally
In PowerShell, from the repository root:
```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install backend and frontend dependencies
python -m pip install -e ".[dev]"
npm ci

# Create local configuration and seed demo data
Copy-Item .env.example .env
python scripts/seed_demo_data.py
```

Start the backend in one terminal:
```powershell
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Start the Next.js dashboard from the repository root in a second terminal:
```powershell
npm run dev
```

Open the dashboard at **[http://localhost:3000/](http://localhost:3000/)**.

Interactive Swagger API documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 5. Development Credentials for Local Demo

| Username | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| `sarah_investigator` | `password123` | **Investigator** | View alerts, triage, add evidence, submit dispositions |
| `marcus_senior` | `password123` | **Senior Investigator** | All investigator permissions + peer review approval |
| `elena_admin` | `password123` | **Fraud Ops Admin** | Rule configuration, simulation control, model promotion |
| `arthur_auditor` | `password123` | **Auditor** | Read-only compliance access to cases and audit trail |

---

## 6. Deterministic Demo Scenarios

SentinelFlow includes 4 reproducible demo scenarios accessible via the UI or CLI:

### Scenario A: Rapid Fund Movement
```bash
python scripts/run_demo_scenario.py --scenario rapid_movement
```
- Injects a $16,500 inbound wire followed immediately by a $15,200 transfer to an external LLC.
- Triggers velocity and rapid-forwarding rules; automatically generates a Critical Alert and opens an investigation case.

### Scenario B: Connected Account Network (Mule Ring)
```bash
python scripts/run_demo_scenario.py --scenario connected_network
```
- Multiple source accounts funnel funds into a single collection hub while sharing a common device fingerprint (`DEV-CLUSTER-987`).
- Detected in Network Intelligence as a **Fan-In Collection Hub**.

### Scenario C: Legitimate Unusual Activity (False Positive Reduction)
```bash
python scripts/run_demo_scenario.py --scenario legitimate_unusual
```
- High-value luxury travel purchase on an established account.
- Flagged with low anomaly confidence, allowing the analyst to verify and close as `LEGITIMATE_ACTIVITY`, contributing to false-positive reduction.

---

## 7. Running Automated Tests

Run the implemented automated tests from the repository root:
```bash
npm test
python -m pytest
```

---

## 8. Repository Layout

```
sentinelflow-ai/
├── README.md                           # Master platform guide & architecture
├── LICENSE                             # MIT Open Source License
├── .env.example                        # Environment variables template
├── docker-compose.yml                  # Container orchestration
├── Makefile                            # Standard developer workflows
├── pyproject.toml                      # Python build configuration
├── package.json                        # Monorepo NPM workspace configuration
├── docs/                               # 12 detailed engineering documentation files
│   ├── architecture.md                 # System components & Mermaid sequence
│   ├── api-reference.md                # Comprehensive REST API contracts
│   ├── database-schema.md              # 27 relational tables & constraints
│   ├── detection-engine.md             # Hybrid risk scoring & calibration
│   ├── graph-intelligence.md           # Money-flow network topology
│   ├── learning-feedback.md            # Label policy & model promotion gates
│   ├── security.md                     # RBAC & log sanitization
│   ├── threat-model.md                 # Prompt injection & adversarial defense
│   ├── demo-script.md                  # 5-minute judge demonstration walkthrough
│   ├── judging-pitch.md                # Executive value proposition
│   └── test-plan.md                    # Verification matrix
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint
│   │   ├── core/                       # Database, security, permissions, logging
│   │   ├── api/v1/                     # REST API version 1 endpoint routers
│   │   ├── detection/                  # Multi-signal rules, MAD anomaly, ML, ensemble
│   │   ├── graph/                      # Breadth-first traversal, shortest paths, hubs
│   │   ├── learning/                   # Dataset builder, label policy, trainer, evaluator
│   │   ├── services/                   # Business logic, orchestration, simulator
│   │   └── static/index.html           # Full interactive investigation command center SPA
│   └── tests/                          # 32 automated unit and integration tests
├── frontend/                           # Next.js 14 App Router TypeScript workspace
└── scripts/                            # CLI seeding, scenario runners, benchmarks
```

---

## 9. Responsible AI & Legal Safeguards

- **Human-in-the-Loop Requirement**: SentinelFlow AI assists and prepares evidence for investigators; it **never automatically freezes accounts, accuses individuals, or blocks legitimate customers**.
- **Synthetic Data Notice**: All customers, accounts, device fingerprints, and financial transactions generated and seeded in this application are completely fictional and intended solely for research, demonstration, and hackathon evaluation.
- **Production Pre-Requisites**: Deployment to live banking environments requires institutional compliance review, formal model risk validation (SR 11-7), and access-control certification.
