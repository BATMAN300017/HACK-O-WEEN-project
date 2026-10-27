SentinelFlow AI — Architecture Specification
Executive Overview
SentinelFlow AI is a self-directed financial fraud investigation platform engineered as a modular monolith. It monitors incoming transactions in real time, applies a 4-part hybrid detection engine, builds an explainable evidentiary case dossier, orchestrates automated graph relationship expansion, provides an evidence-grounded AI copilot, and feeds human-validated dispositions into a controlled continuous learning pipeline.
```mermaid
flowchart TD
    subgraph Ingestion["1. Event Ingestion & Simulation"]
        TXN[Transaction Event] --> VAL[Schema Validation & Sanitization]
        VAL --> IDEM[Idempotency Check]
        IDEM --> DB[(Persistent Database)]
    end


    subgraph Detection["2. Hybrid Multi-Signal Detection Engine"]
        DB --> FEAT[Feature Extractor]
        FEAT --> RUL[Explainable Rules Engine (30%)]
        FEAT --> ANOM[Account Rolling MAD Anomaly (25%)]
        FEAT --> ML[Supervised Baseline Model (25%)]
        FEAT --> GRP[Graph Topology Signals (20%)]
        RUL & ANOM & ML & GRP --> ENS[Calibrated 0-100 Risk Ensemble]
        ENS --> EXP[Narrative Explanation Generator]
    end


    subgraph Investigation["3. Self-Directed Investigation Agent"]
        ENS -->|Risk Score >= 70| AGENT[Investigation Orchestrator]
        AGENT --> EVD[Typed Evidence Builder]
        AGENT --> SUBG[Multi-Hop Sub-Graph Traversal]
        AGENT --> CHK[Procedural Task Checklist]
        AGENT --> COPILOT[Evidence-Grounded AI Copilot]
    end


    subgraph Governance["4. Human-In-The-Loop & Learning"]
        CHK & EVD --> ANALYST[Investigator Workbench]
        ANALYST --> DISP[Audit-Backed Disposition]
        DISP --> PEER[Senior Peer Review Gate]
        PEER --> POLICY[Controlled Label Policy]
        POLICY --> TRAIN[Candidate Model Trainer & Holdout Evaluator]
        TRAIN --> PROMO[Admin Promotion Gate]
    end
```

Architectural Layers
Ingestion & Data Persistence: Relational schema handling 27 tables with strict foreign keys, monetary Decimal precision, and append-only audit logging.
Hybrid Detection Engine: Combines deterministic explainable rules, median absolute deviation (MAD) statistical baselines, graph structural indicators, and calibrated logistic regression models.
Investigation Orchestration: 13-step bounded agent workflow that gathers multi-hop counterparties, shared devices, and counter-evidence.
Controlled Learning & Governance: Enforces label policy (only human-verified fraud becomes label 1, false positives become label 0, inconclusive/suspicious excluded), preventing feedback poisoning.
