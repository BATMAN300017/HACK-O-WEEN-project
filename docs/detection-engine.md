SentinelFlow AI — Detection Engine Architecture
Multi-Modal Hybrid Risk Ensemble
Unlike black-box classifiers that output an opaque fraud probability, SentinelFlow AI evaluates each transaction across four independent detector modalities:
$$\text{Composite Score} = 0.30 \cdot S_{\text{rules}} + 0.25 \cdot S_{\text{anomaly}} + 0.25 \cdot S_{\text{supervised}} + 0.20 \cdot S_{\text{graph}}$$
1. Explainable Rule Engine (30% Weight)
Configurable and versioned rules evaluate operational thresholds:
Velocity: >4 transactions from the same account within a 10-minute window.
Rapid Fund Movement: Account receives >$5,000 inbound and immediately forwards >80% to an external counterparty within 30 minutes.
Dormant Reactivation: Account inactive >180 days suddenly executes transfers exceeding $2,000.
Shared Device Multi-Account: Device fingerprint associated with 3 or more distinct accounts.
New Beneficiary Spike: Transfer >$5,000 to a first-time counterparty.
Repeated Reversals: Multiple reversed transfers followed by an outbound transaction.
2. Behavioral Anomaly Detection (25% Weight)
Uses robust account-specific statistical baselines:
Rolling median and Median Absolute Deviation (MAD): $$\text{Robust } Z = \frac{0.6745 \cdot (\text{Amount} - \text{Median})}{\text{MAD}}$$
Cold-Start Indicator: Accounts with fewer than 5 transactions are flagged as LOW_HISTORY_CONFIDENCE, preventing unfair penalization of newly opened accounts.
3. Supervised Machine Learning (25% Weight)
Calibrated Logistic Regression baseline trained strictly on information available at scoring time.
Class imbalance handled through balanced sample weighting.
Chronological train/test splits preventing future target leakage.
4. Graph Structural Signals (20% Weight)
Degree centrality: in-degree fan-in collection hubs and out-degree distribution nodes.
Intermediary forwarders: accounts that receive and forward funds with near-zero retained balance.
Circular transfer cycles: reciprocal funds movement between counterparties.
Triage Bands & Calibration
0–24 (Routine): Automated clear and routine surveillance.
25–49 (Low): Low-priority audit sampling.
50–74 (Elevated): Analyst review alert queue.
75–100 (High): Automated conversion to self-directed investigation case.
