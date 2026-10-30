"""Local Outlier Factor (LOF) detector for transaction-level anomaly scoring.

Uses sklearn's LocalOutlierFactor in *novelty detection* mode to score
individual transactions against a fitted baseline. Designed for unsupervised
operation — NEVER accesses ground-truth labels.

Typical usage:
    detector = LOFDetector()
    detector.fit_baseline(transactions_df)
    result = detector.score_transaction(features_dict)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler

from app.core.logging import logger

__all__ = [
    "LOFDetector",
    "LOFResult",
    "TRANSACTION_FEATURE_KEYS",
]

TRANSACTION_FEATURE_KEYS: List[str] = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "time_since_last_txn_seconds",
    "counterparty_frequency",
]

# Minimum baseline transactions required for meaningful LOF fitting.
_MIN_BASELINE_SIZE: int = 20

# Default score when the model has not been fitted.
_UNFITTED_DEFAULT_SCORE: float = 10.0


@dataclass
class LOFResult:
    """Result of a single transaction's LOF scoring."""

    risk_score: float  # 0-100, higher = more anomalous
    raw_lof_score: float  # sklearn's negative_outlier_factor
    is_outlier: bool
    is_baseline_available: bool
    feature_values: Dict[str, float] = field(default_factory=dict)
    evidence: str = ""


class LOFDetector:
    """Local Outlier Factor novelty detector for transactions.

    Fits on a baseline of historical transaction features and then scores
    new (unseen) transactions. Uses ``novelty=True`` so that
    ``score_samples`` and ``predict`` work on new data.

    Parameters
    ----------
    n_neighbors : int
        Number of neighbors for LOF computation.
    contamination : str | float
        Expected fraction of outliers.  ``'auto'`` lets sklearn decide.
    """

    def __init__(
        self,
        n_neighbors: int = 20,
        contamination: str | float = "auto",
    ) -> None:
        self._n_neighbors = n_neighbors
        self._contamination = contamination

        self._model: Optional[LocalOutlierFactor] = None
        self._scaler: RobustScaler = RobustScaler()
        self._is_fitted: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_baseline(self, transactions_df: List[Dict[str, Any]]) -> None:
        """Fit the LOF model on a baseline set of transaction feature dicts.

        Parameters
        ----------
        transactions_df : list[dict]
            Each dict must contain keys from ``TRANSACTION_FEATURE_KEYS``.

        Raises
        ------
        ValueError
            If fewer than ``_MIN_BASELINE_SIZE`` rows are provided.
        """
        if not transactions_df:
            raise ValueError("Cannot fit LOF baseline on empty transaction data")

        if len(transactions_df) < _MIN_BASELINE_SIZE:
            logger.warning(
                "LOF baseline has only %d transactions (minimum %d). "
                "Model will be fitted but may produce unreliable scores.",
                len(transactions_df),
                _MIN_BASELINE_SIZE,
            )

        X = self._extract_matrix(transactions_df)

        self._scaler = RobustScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Cap n_neighbors to available samples - 1
        effective_neighbors = min(self._n_neighbors, len(transactions_df) - 1)
        effective_neighbors = max(effective_neighbors, 1)

        self._model = LocalOutlierFactor(
            n_neighbors=effective_neighbors,
            contamination=self._contamination,
            novelty=True,
            n_jobs=-1,
        )
        self._model.fit(X_scaled)
        self._is_fitted = True
        logger.info(
            "LOF fitted on %d baseline transactions (n_neighbors=%d)",
            len(transactions_df),
            effective_neighbors,
        )

    def score_transaction(self, features_dict: Dict[str, Any]) -> LOFResult:
        """Score a single new transaction against the fitted baseline.

        Parameters
        ----------
        features_dict : dict
            Must contain keys from ``TRANSACTION_FEATURE_KEYS``.

        Returns
        -------
        LOFResult
        """
        if not self._is_fitted or self._model is None:
            return LOFResult(
                risk_score=_UNFITTED_DEFAULT_SCORE,
                raw_lof_score=0.0,
                is_outlier=False,
                is_baseline_available=False,
                feature_values={
                    k: float(features_dict.get(k, 0.0))
                    for k in TRANSACTION_FEATURE_KEYS
                },
                evidence=(
                    "LOF model has not been fitted. "
                    f"Default score of {_UNFITTED_DEFAULT_SCORE} assigned."
                ),
            )

        x = self._extract_row(features_dict)
        x_scaled = self._scaler.transform(x)

        raw_score = float(self._model.score_samples(x_scaled)[0])
        prediction = int(self._model.predict(x_scaled)[0])
        is_outlier = prediction == -1

        risk_score = self._normalise_score(raw_score)

        feature_values = {
            k: float(features_dict.get(k, 0.0))
            for k in TRANSACTION_FEATURE_KEYS
        }
        evidence = self._build_evidence(risk_score, is_outlier, feature_values)

        return LOFResult(
            risk_score=risk_score,
            raw_lof_score=raw_score,
            is_outlier=is_outlier,
            is_baseline_available=True,
            feature_values=feature_values,
            evidence=evidence,
        )

    def score_transactions_batch(
        self, transactions: List[Dict[str, Any]]
    ) -> List[LOFResult]:
        """Score multiple transactions in batch.

        Parameters
        ----------
        transactions : list[dict]

        Returns
        -------
        list[LOFResult]
        """
        if not transactions:
            return []
        return [self.score_transaction(t) for t in transactions]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_matrix(self, rows: List[Dict[str, Any]]) -> np.ndarray:
        """Build (N, F) matrix from transaction dicts."""
        return np.array(
            [
                [float(row.get(col, 0.0)) for col in TRANSACTION_FEATURE_KEYS]
                for row in rows
            ],
            dtype=np.float64,
        )

    def _extract_row(self, features_dict: Dict[str, Any]) -> np.ndarray:
        """Extract a single (1, F) row."""
        return np.array(
            [[float(features_dict.get(col, 0.0)) for col in TRANSACTION_FEATURE_KEYS]],
            dtype=np.float64,
        )

    @staticmethod
    def _normalise_score(raw_score: float) -> float:
        """Map LOF score_samples output to 0-100 risk scale.

        LOF score_samples returns negative log-likelihood-like values:
        - More negative → more anomalous
        - Close to -1.0 → borderline inlier/outlier
        - Close to 0.0 or slightly negative → strong inlier
        """
        # Shift and scale: raw ≈ -1.0 is the boundary
        risk = max(0.0, min(100.0, (-raw_score - 0.5) * 100.0))
        return round(risk, 1)

    @staticmethod
    def _build_evidence(
        risk_score: float,
        is_outlier: bool,
        feature_values: Dict[str, float],
    ) -> str:
        """Build human-readable evidence string."""
        status = "flagged as outlier" if is_outlier else "within normal range"
        parts = [f"LOF analysis: transaction {status} (score {risk_score}/100)."]

        amt = feature_values.get("amount", 0.0)
        hour = feature_values.get("hour_of_day", -1.0)
        gap = feature_values.get("time_since_last_txn_seconds", 0.0)
        cp_freq = feature_values.get("counterparty_frequency", 0.0)

        if hour >= 0 and (hour < 6 or hour >= 23):
            parts.append(f"Transaction occurred during off-hours (hour={int(hour)}).")
        if gap > 0 and gap < 60:
            parts.append(
                f"Very short interval since last transaction ({gap:.0f}s)."
            )
        if cp_freq <= 1:
            parts.append("Counterparty has been seen ≤1 time previously.")

        return " ".join(parts)
