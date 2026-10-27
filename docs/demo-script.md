SentinelFlow AI — Demonstration Script for Judges
Live Demo Walkthrough (5-Minute Script)
Step 1: Platform Overview & KPIs (1 Minute)
Open the application at http://localhost:8000/.
Observe the Command Center: real-time transaction count, alert velocity, active investigations, and risk calibration tiers (Routine, Low, Elevated, High).
Point out that all data is dynamically generated from real SQLite/PostgreSQL persistence.
Step 2: Trigger Scenario A — Rapid Fund Movement (1 Minute)
In the top navigation bar, click the "Rapid Flow" button (or run python scripts/run_demo_scenario.py --scenario rapid_movement).
Watch the telemetry update: an incoming wire of $16,500 arrives, followed immediately by a $15,200 transfer to an external LLC.
Switch to Alerts Queue: Notice the new Critical alert triggered by both the RAPID_FUND_MOVEMENT rule and the MAD statistical anomaly detector.
Click "Investigate" on the alert.
Step 3: Self-Directed Investigation Workbench (1.5 Minutes)
Examine the Investigation Dossier:
Case summary and priority.
Evidence Items: Click through the typed records. Highlight the SHA-256 integrity hash and verification status (Supporting vs. Contradictory).
Checklist Tasks: Mark the checklist items as completed.
Sub-Graph Network: View the visual money-flow graph connecting the source account to the counterparty.
AI Copilot: Ask "Why was this transaction flagged?" or "What contradicts fraud?" and note how it cites specific evidence IDs.
Step 4: Record Case Disposition & Controlled Learning (1 Minute)
Click "Record Disposition".
Select "Confirmed Fraud" and enter rationale: "Phishing compromise confirmed by account holder; rapid forwarding matches known mule behavior."
Submit the disposition.
Switch to Feedback & Learning:
Point out that the disposition was converted to a positive training label under the Label Policy.
Show how the platform reports sample readiness (e.g. 11/20 samples) and refuses to retrain prematurely, avoiding model degradation.
Step 5: Network Intelligence & What-If Rules (30 Seconds)
Switch to Network Intelligence to show detected fan-in hubs and circular flows.
Switch to Detection Rules to show threshold versioning and the What-If simulation engine.
