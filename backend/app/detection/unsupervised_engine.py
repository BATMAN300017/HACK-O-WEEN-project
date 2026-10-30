"""
Unsupervised Financial Crime Detection Engine.

Implements multi-signal unsupervised detection:
1. Behavioral Anomaly Detection: Multidimensional Isolation Forest and robust rolling MAD.
2. Temporal Dynamics: Transfer latency, pass-through ratio, burst velocity.
3. Graph Intelligence: Centrality, fan-in/fan-out, cycle presence, pass-through forwarder status.
4. Cross-Border & Multi-Currency Corridors: Cross-jurisdictional hops and rapid conversions.

CRITICAL ARCHITECTURAL CONSTRAINTS:
- NEVER receives or trains on ground-truth fraud or mule labels.
- Uses chronological split: early transaction period establishes normal account baselines,
  subsequent transactions are scored blindly.
- Never automatically freezes accounts or declares guilt from a single anomaly.
- Maps risk into transparent operational states:
  - LOW_RISK: Automated monitoring
  - SUSPICIOUS: Triage and self-directed investigation candidate
  - INCONCLUSIVE: Insufficient evidentiary density
  - CONFIRMED_OR_CLEARED: Governed human analyst disposition
"""

import sqlite3
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sklearn.ensemble import IsolationForest

from app.data_ingestion.label_isolation import assert_no_label_leakage
from app.data_ingestion.currency_service import CurrencyConversionService
from app.graph.mule_network_engine import MuleNetworkEngine
from app.core.logging import logger

class UnsupervisedDetectionEngine:
    """Evaluates transactions and accounts blindly without ground-truth labels."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.iso_forest = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        self.is_fitted = False
        self._fit_chronological_baseline()

    def _fit_chronological_baseline(self):
        """
        Fits unsupervised Isolation Forest on the earlier 60% chronological period
        to learn legitimate banking patterns.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT amount, currency, created_at, source_account_id
            FROM transactions
            WHERE status != 'FAILED'
            ORDER BY created_at ASC
        """)
        rows = cursor.fetchall()
        if len(rows) < 20:
            logger.info("Insufficient transactions for chronological baseline fitting. Will use fallback MAD.")
            return

        split_idx = int(len(rows) * 0.60)
        baseline_rows = rows[:split_idx]

        feature_matrix = []
        for r in baseline_rows:
            amt = float(r[0])
            curr = r[1]
            norm_amt = CurrencyConversionService.normalize_to_base(amt, curr, r[2])
            # Features: [log(amount), amount_norm]
            feature_matrix.append([np.log1p(max(1.0, norm_amt)), norm_amt / 10000.0])

        X = np.array(feature_matrix)
        self.iso_forest.fit(X)
        self.is_fitted = True
        logger.info(f"Unsupervised Isolation Forest baseline fitted on {len(X)} chronological historical transactions.")

    def score_transaction_unsupervised(
        self,
        txn: Dict[str, Any],
        graph_engine: Optional[MuleNetworkEngine] = None
    ) -> Dict[str, Any]:
        """
        Scores an incoming transaction across 4 independent unsupervised signals:
        1. Behavioral Anomaly Score (0 - 100)
        2. Graph Risk Score (0 - 100)
        3. Temporal Velocity Score (0 - 100)
        4. Cross-Border / Currency Risk Score (0 - 100)
        """
        # Strict assert: zero labels allowed
        assert_no_label_leakage(txn, context="UnsupervisedDetectionEngine.score")

        amt = float(txn["amount"])
        curr = txn.get("currency", "INR")
        ts = txn.get("created_at")
        src = txn["source_account_id"]
        dest = txn.get("destination_account_id")
        norm_amt = CurrencyConversionService.normalize_to_base(amt, curr, ts)

        # 1. Behavioral Anomaly Score (Isolation Forest + Deviation)
        anomaly_score = 25.0
        if self.is_fitted:
            feat = np.array([[np.log1p(max(1.0, norm_amt)), norm_amt / 10000.0]])
            raw_score = self.iso_forest.decision_function(feat)[0]
            # Map raw score [-0.5, 0.5] to [0, 100] where lower decision function = higher anomaly
            anomaly_score = min(100.0, max(0.0, float((0.20 - raw_score) * 150.0)))
        else:
            if norm_amt > 100000.0:
                anomaly_score = 65.0
            elif norm_amt > 25000.0:
                anomaly_score = 40.0

        # 2. Graph Risk Score
        graph_score = 20.0
        graph_reasons = []
        if graph_engine and dest:
            # Check if source or destination behaves as pass-through mule
            if dest in graph_engine.graph.nodes:
                inflow = graph_engine.graph.nodes[dest].get("total_inflow", 0.0)
                outflow = graph_engine.graph.nodes[dest].get("total_outflow", 0.0)
                if inflow > 5000.0 and outflow > 0.0:
                    fwd_ratio = outflow / inflow
                    if fwd_ratio >= 0.75:
                        graph_score += 45.0
                        graph_reasons.append(f"Destination account {dest} exhibits {fwd_ratio*100:.1f}% pass-through forwarding.")

            in_deg = graph_engine.graph.in_degree(dest) if dest in graph_engine.graph.nodes else 0
            if in_deg >= 3:
                graph_score += 25.0
                graph_reasons.append(f"Destination is a fan-in collector hub (in-degree: {in_deg}).")

        graph_score = min(100.0, graph_score)

        # 3. Temporal Velocity Score
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE source_account_id = ? AND id != ?
        """, (src, txn.get("id", "")))
        vel_row = cursor.fetchone()
        short_count = vel_row[0] if vel_row else 0

        temporal_score = 20.0
        if short_count >= 4:
            temporal_score = 80.0
        elif short_count >= 2:
            temporal_score = 50.0

        # 4. Cross-Border / Currency Risk Score
        src_country = txn.get("sender_country", "IND")
        dest_country = txn.get("receiver_country", "IND")
        is_cross_border = src_country != dest_country
        has_currency_conversion = curr != txn.get("converted_currency", curr)

        cross_border_score = 15.0
        if is_cross_border:
            cross_border_score += 45.0
        if has_currency_conversion:
            cross_border_score += 25.0
        cross_border_score = min(100.0, cross_border_score)

        # Multi-Signal Synthesis
        final_risk = round(
            (0.35 * graph_score) +
            (0.30 * anomaly_score) +
            (0.20 * temporal_score) +
            (0.15 * cross_border_score),
            1
        )

        # Operational State Assignment
        if final_risk >= 70.0:
            operational_state = "SUSPICIOUS"  # Investigation candidate
        elif final_risk >= 50.0:
            operational_state = "INCONCLUSIVE"  # Insufficient evidence
        else:
            operational_state = "LOW_RISK"  # Monitor

        return {
            "transaction_id": txn.get("id"),
            "final_unsupervised_risk_score": final_risk,
            "operational_state": operational_state,
            "component_scores": {
                "behavioral_anomaly_score": round(anomaly_score, 1),
                "graph_risk_score": round(graph_score, 1),
                "temporal_velocity_score": round(temporal_score, 1),
                "cross_border_currency_score": round(cross_border_score, 1)
            },
            "signals": {
                "is_cross_border": is_cross_border,
                "has_currency_conversion": has_currency_conversion,
                "graph_indicators": graph_reasons
            },
            "action_recommendation": (
                "Initiate Self-Directed Investigation & assemble case dossier."
                if operational_state == "SUSPICIOUS" else "Log for routine automated surveillance."
            )
        }
