"""DBSCAN clustering-based anomaly detection for account behavioural profiling.

Clusters accounts by behavioural features and flags accounts that fall into
noise points (label -1) or very small clusters as anomalous. Designed for
unsupervised operation — NEVER accesses ground-truth labels.

Typical usage:
    detector = ClusteringDetector()
    detector.fit_clusters(accounts_df)
    anomalies = detector.get_anomalous_accounts()
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import RobustScaler

from app.core.logging import logger

__all__ = [
    "ClusteringDetector",
    "ClusterResult",
    "CLUSTERING_FEATURE_COLUMNS",
]

CLUSTERING_FEATURE_COLUMNS: List[str] = [
    "in_out_ratio",
    "avg_txn_size",
    "txn_frequency",
    "unique_counterparties",
    "cross_border_ratio",
]

# Clusters with this many or fewer members are considered "small" and their
# accounts are flagged as anomalous.
_SMALL_CLUSTER_THRESHOLD: int = 3


@dataclass
class ClusterResult:
    """Result for a single account from clustering analysis."""

    account_id: str
    cluster_label: int  # -1 = noise
    cluster_size: int  # 0 for noise points
    is_anomalous: bool
    risk_score: float  # 0-100
    feature_snapshot: Dict[str, float] = field(default_factory=dict)
    evidence: str = ""


class ClusteringDetector:
    """DBSCAN-based clustering detector for account-level anomaly detection.

    Clusters accounts using DBSCAN on behavioural features. Accounts assigned
    to noise (label -1) or to very small clusters are considered anomalous.

    Parameters
    ----------
    eps : float
        Maximum distance between two samples for them to be considered
        neighbours.
    min_samples : int
        Minimum number of points to form a dense region.
    small_cluster_threshold : int
        Clusters of this size or smaller are treated as anomalous.
    """

    def __init__(
        self,
        eps: float = 0.5,
        min_samples: int = 5,
        small_cluster_threshold: int = _SMALL_CLUSTER_THRESHOLD,
    ) -> None:
        self._eps = eps
        self._min_samples = min_samples
        self._small_cluster_threshold = small_cluster_threshold

        self._scaler: RobustScaler = RobustScaler()
        self._model: Optional[DBSCAN] = None
        self._is_fitted: bool = False

        # Stored after fitting
        self._account_ids: List[str] = []
        self._labels: np.ndarray = np.array([])
        self._features_matrix: np.ndarray = np.array([])
        self._raw_data: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_clusters(self, accounts_df: List[Dict[str, Any]]) -> None:
        """Fit DBSCAN on account-level behavioural features.

        Parameters
        ----------
        accounts_df : list[dict]
            Each dict must contain keys from ``CLUSTERING_FEATURE_COLUMNS``
            plus ``account_id``.

        Raises
        ------
        ValueError
            If *accounts_df* is empty.
        """
        if not accounts_df:
            raise ValueError("Cannot cluster empty account data")

        self._raw_data = list(accounts_df)
        self._account_ids = [
            str(a.get("account_id", f"unknown-{i}"))
            for i, a in enumerate(accounts_df)
        ]

        X = self._extract_matrix(accounts_df)
        self._scaler = RobustScaler()
        X_scaled = self._scaler.fit_transform(X)
        self._features_matrix = X_scaled

        self._model = DBSCAN(
            eps=self._eps,
            min_samples=self._min_samples,
            n_jobs=-1,
        )
        self._labels = self._model.fit_predict(X_scaled)
        self._is_fitted = True

        n_clusters = len(set(self._labels)) - (1 if -1 in self._labels else 0)
        n_noise = int(np.sum(self._labels == -1))
        logger.info(
            "DBSCAN clustering: %d accounts → %d clusters, %d noise points "
            "(eps=%.2f, min_samples=%d)",
            len(accounts_df),
            n_clusters,
            n_noise,
            self._eps,
            self._min_samples,
        )

    def get_anomalous_accounts(self) -> List[ClusterResult]:
        """Return results for all accounts, with anomaly flags.

        Anomalous accounts are those in noise (label -1) or in clusters
        whose size is ≤ ``small_cluster_threshold``.

        Returns
        -------
        list[ClusterResult]
            All accounts' cluster results (anomalous and normal alike).
        """
        if not self._is_fitted:
            logger.warning("get_anomalous_accounts called before fit_clusters")
            return []

        cluster_sizes = self._compute_cluster_sizes()
        results: List[ClusterResult] = []

        for idx, (acct_id, label) in enumerate(
            zip(self._account_ids, self._labels)
        ):
            label_int = int(label)
            is_noise = label_int == -1
            size = cluster_sizes.get(label_int, 0) if not is_noise else 0
            is_small = (not is_noise) and size <= self._small_cluster_threshold
            is_anomalous = is_noise or is_small

            risk_score = self._compute_risk_score(
                is_noise, is_small, size, cluster_sizes
            )

            snapshot = {
                col: float(self._raw_data[idx].get(col, 0.0))
                for col in CLUSTERING_FEATURE_COLUMNS
            }

            evidence = self._build_evidence(
                acct_id, label_int, is_noise, is_small, size, risk_score
            )

            results.append(
                ClusterResult(
                    account_id=acct_id,
                    cluster_label=label_int,
                    cluster_size=size,
                    is_anomalous=is_anomalous,
                    risk_score=risk_score,
                    feature_snapshot=snapshot,
                    evidence=evidence,
                )
            )

        return results

    def get_cluster_summary(self) -> Dict[str, Any]:
        """Return a high-level summary of the clustering result.

        Returns
        -------
        dict
            Keys: ``n_clusters``, ``n_noise``, ``cluster_sizes``,
            ``anomalous_count``, ``total_accounts``.
        """
        if not self._is_fitted:
            return {
                "n_clusters": 0,
                "n_noise": 0,
                "cluster_sizes": {},
                "anomalous_count": 0,
                "total_accounts": 0,
            }

        cluster_sizes = self._compute_cluster_sizes()
        n_noise = int(np.sum(self._labels == -1))
        n_small = sum(
            size
            for label, size in cluster_sizes.items()
            if label != -1 and size <= self._small_cluster_threshold
        )

        return {
            "n_clusters": len(cluster_sizes) - (1 if -1 in cluster_sizes else 0),
            "n_noise": n_noise,
            "cluster_sizes": {
                str(k): v for k, v in cluster_sizes.items() if k != -1
            },
            "anomalous_count": n_noise + n_small,
            "total_accounts": len(self._labels),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_matrix(self, rows: List[Dict[str, Any]]) -> np.ndarray:
        """Build an (N, F) numpy matrix from account dicts."""
        return np.array(
            [
                [float(row.get(col, 0.0)) for col in CLUSTERING_FEATURE_COLUMNS]
                for row in rows
            ],
            dtype=np.float64,
        )

    def _compute_cluster_sizes(self) -> Dict[int, int]:
        """Return {cluster_label: count} mapping."""
        unique, counts = np.unique(self._labels, return_counts=True)
        return dict(zip(unique.tolist(), counts.tolist()))

    @staticmethod
    def _compute_risk_score(
        is_noise: bool,
        is_small: bool,
        cluster_size: int,
        all_sizes: Dict[int, int],
    ) -> float:
        """Compute 0-100 risk score based on cluster assignment.

        - Noise points → high risk (70-85)
        - Small clusters → moderate risk (40-65)
        - Normal clusters → low risk based on inverse size ratio
        """
        if is_noise:
            return 75.0

        if is_small:
            # Smaller cluster → higher score
            return round(max(40.0, 65.0 - cluster_size * 5.0), 1)

        # Normal cluster — risk proportional to inverse cluster size
        max_size = max(all_sizes.values()) if all_sizes else 1
        ratio = 1.0 - (cluster_size / max_size) if max_size > 0 else 0.0
        return round(max(0.0, min(30.0, ratio * 30.0)), 1)

    @staticmethod
    def _build_evidence(
        acct_id: str,
        label: int,
        is_noise: bool,
        is_small: bool,
        size: int,
        risk_score: float,
    ) -> str:
        """Build human-readable evidence string."""
        if is_noise:
            return (
                f"Account {acct_id} is a DBSCAN noise point (no cluster assignment). "
                f"Behavioural features do not match any established cluster. "
                f"Risk score: {risk_score}/100."
            )
        if is_small:
            return (
                f"Account {acct_id} belongs to a small cluster "
                f"(cluster {label}, size {size}). "
                f"Small clusters may indicate atypical behaviour patterns. "
                f"Risk score: {risk_score}/100."
            )
        return (
            f"Account {acct_id} belongs to cluster {label} (size {size}). "
            f"Behavioural profile is consistent with established patterns. "
            f"Risk score: {risk_score}/100."
        )
