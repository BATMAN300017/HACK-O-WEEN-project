"""Multi-signal risk scorer that combines all detection signals into a unified,
explainable risk assessment.

Takes component scores from behavioural, graph, temporal, rule-based, and
geographic detectors and produces a final risk score with risk tier, component
breakdown, and human-readable explanations.

Key design constraints:
    - NEVER automatically labels an account as "mule"
    - Only assigns risk tiers: LOW_RISK, SUSPICIOUS, INCONCLUSIVE
    - A single high signal alone CANNOT make risk_tier = SUSPICIOUS (needs
      corroboration from at least one other signal)
    - NEVER accesses ground-truth labels

Typical usage:
    scorer = MultiSignalScorer()
    result = scorer.score(
        behavioral_score=72.0,
        graph_score=55.0,
        temporal_score=40.0,
        rule_score=30.0,
        geographic_score=20.0,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import logger

__all__ = [
    "MultiSignalScorer",
    "MultiSignalResult",
    "RiskTier",
    "DEFAULT_WEIGHTS",
]


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DEFAULT_WEIGHTS: Dict[str, float] = {
    "behavioral": 0.25,
    "graph": 0.25,
    "temporal": 0.20,
    "rules": 0.15,
    "geographic": 0.15,
}

# A signal is considered "active" (meaningfully elevated) when its score
# exceeds this threshold.
_SIGNAL_ACTIVE_THRESHOLD: float = 30.0

# Minimum number of *corroborating* active signals required to assign
# SUSPICIOUS tier (prevents single-signal SUSPICIOUS).
_MIN_CORROBORATION_SIGNALS: int = 2

# Score thresholds for tier assignment (applied AFTER corroboration check).
_SUSPICIOUS_THRESHOLD: float = 55.0
_LOW_RISK_CEILING: float = 35.0


class RiskTier:
    """String constants for risk tier classification."""

    LOW_RISK = "LOW_RISK"
    SUSPICIOUS = "SUSPICIOUS"
    INCONCLUSIVE = "INCONCLUSIVE"


# --------------------------------------------------------------------------
# Result data class
# --------------------------------------------------------------------------


@dataclass
class MultiSignalResult:
    """Unified result from the multi-signal scorer."""

    final_risk_score: float  # 0-100
    risk_tier: str  # LOW_RISK | SUSPICIOUS | INCONCLUSIVE
    component_breakdown: Dict[str, float] = field(default_factory=dict)
    weighted_contributions: Dict[str, float] = field(default_factory=dict)
    evidence_items: List[str] = field(default_factory=list)
    missing_signals: List[str] = field(default_factory=list)
    active_signal_count: int = 0
    explanation: str = ""


# --------------------------------------------------------------------------
# Scorer
# --------------------------------------------------------------------------


class MultiSignalScorer:
    """Combines detection signals into a unified explainable risk score.

    Parameters
    ----------
    weights : dict[str, float] | None
        Custom signal weights. Must sum to ≈ 1.0. Defaults to
        ``DEFAULT_WEIGHTS``.
    signal_active_threshold : float
        Score above which a signal is considered "active".
    suspicious_threshold : float
        Weighted score above which SUSPICIOUS tier may be assigned
        (subject to corroboration).
    low_risk_ceiling : float
        Weighted score at or below which LOW_RISK is assigned.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        signal_active_threshold: float = _SIGNAL_ACTIVE_THRESHOLD,
        suspicious_threshold: float = _SUSPICIOUS_THRESHOLD,
        low_risk_ceiling: float = _LOW_RISK_CEILING,
    ) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        self._signal_active_threshold = signal_active_threshold
        self._suspicious_threshold = suspicious_threshold
        self._low_risk_ceiling = low_risk_ceiling

        self._validate_weights()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        behavioral_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        temporal_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        geographic_score: Optional[float] = None,
        evidence_coverage: Optional[Dict[str, List[str]]] = None,
    ) -> MultiSignalResult:
        """Compute the unified risk score.

        Parameters
        ----------
        behavioral_score : float | None
            Score from behavioural/anomaly detectors (0-100).
        graph_score : float | None
            Score from graph-based detectors (0-100).
        temporal_score : float | None
            Score from temporal analysis (0-100).
        rule_score : float | None
            Score from rule-based detection (0-100).
        geographic_score : float | None
            Score from geographic risk assessment (0-100).
        evidence_coverage : dict | None
            Mapping of signal name → list of evidence strings.

        Returns
        -------
        MultiSignalResult
        """
        evidence_coverage = evidence_coverage or {}

        # Build signal map (None = missing)
        signals: Dict[str, Optional[float]] = {
            "behavioral": behavioral_score,
            "graph": graph_score,
            "temporal": temporal_score,
            "rules": rule_score,
            "geographic": geographic_score,
        }

        # Identify present vs missing signals
        present_signals: Dict[str, float] = {}
        missing_signals: List[str] = []

        for name, value in signals.items():
            if value is not None:
                present_signals[name] = max(0.0, min(100.0, value))
            else:
                missing_signals.append(name)

        # Compute weighted score using present signals only
        component_breakdown: Dict[str, float] = {}
        weighted_contributions: Dict[str, float] = {}
        total_weight = 0.0
        raw_weighted_sum = 0.0

        for name, value in present_signals.items():
            w = self._weights.get(name, 0.0)
            contribution = value * w
            component_breakdown[name] = round(value, 1)
            weighted_contributions[name] = round(contribution, 2)
            raw_weighted_sum += contribution
            total_weight += w

        # Normalise for missing signals so the score uses the same 0-100 range
        if total_weight > 0 and total_weight < 1.0:
            final_score = raw_weighted_sum / total_weight
        else:
            final_score = raw_weighted_sum

        final_score = round(max(0.0, min(100.0, final_score)), 1)

        # Count active signals
        active_signals = [
            name
            for name, value in present_signals.items()
            if value >= self._signal_active_threshold
        ]
        active_count = len(active_signals)

        # Determine risk tier with corroboration check
        risk_tier = self._determine_tier(final_score, active_count)

        # Build evidence items
        evidence_items = self._collect_evidence(
            present_signals,
            active_signals,
            evidence_coverage,
            missing_signals,
        )

        # Build explanation
        explanation = self._build_explanation(
            final_score,
            risk_tier,
            component_breakdown,
            active_signals,
            missing_signals,
        )

        return MultiSignalResult(
            final_risk_score=final_score,
            risk_tier=risk_tier,
            component_breakdown=component_breakdown,
            weighted_contributions=weighted_contributions,
            evidence_items=evidence_items,
            missing_signals=missing_signals,
            active_signal_count=active_count,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_weights(self) -> None:
        """Warn if weights don't sum to ~1.0."""
        total = sum(self._weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(
                "MultiSignalScorer weights sum to %.3f (expected ~1.0). "
                "Scores may be scaled unexpectedly.",
                total,
            )

    def _determine_tier(self, score: float, active_count: int) -> str:
        """Determine risk tier with corroboration enforcement.

        Rules:
        1. Score ≤ low_risk_ceiling → LOW_RISK
        2. Score ≥ suspicious_threshold AND ≥ 2 active signals → SUSPICIOUS
        3. Everything else → INCONCLUSIVE
        """
        if score <= self._low_risk_ceiling:
            return RiskTier.LOW_RISK

        if (
            score >= self._suspicious_threshold
            and active_count >= _MIN_CORROBORATION_SIGNALS
        ):
            return RiskTier.SUSPICIOUS

        return RiskTier.INCONCLUSIVE

    def _collect_evidence(
        self,
        present_signals: Dict[str, float],
        active_signals: List[str],
        evidence_coverage: Dict[str, List[str]],
        missing_signals: List[str],
    ) -> List[str]:
        """Collect all evidence items from component detectors."""
        items: List[str] = []

        for name in active_signals:
            score = present_signals[name]
            items.append(
                f"[{name.upper()}] Signal active at {score:.0f}/100."
            )
            # Append any detailed evidence from the coverage map
            for ev in evidence_coverage.get(name, []):
                items.append(f"  → {ev}")

        if missing_signals:
            items.append(
                f"Missing signals ({len(missing_signals)}): "
                f"{', '.join(missing_signals)}. "
                f"Risk assessment is based on {len(present_signals)} of "
                f"{len(present_signals) + len(missing_signals)} signals."
            )

        return items

    @staticmethod
    def _build_explanation(
        score: float,
        tier: str,
        breakdown: Dict[str, float],
        active_signals: List[str],
        missing_signals: List[str],
    ) -> str:
        """Build human-readable explanation string."""
        parts: List[str] = []

        parts.append(f"Composite risk score: {score}/100 — Tier: {tier}.")

        if active_signals:
            parts.append(
                f"Active signals ({len(active_signals)}): "
                f"{', '.join(active_signals)}."
            )
        else:
            parts.append("No signals exceeded the activation threshold.")

        if tier == RiskTier.INCONCLUSIVE:
            if len(active_signals) < _MIN_CORROBORATION_SIGNALS:
                parts.append(
                    "Risk assessment is INCONCLUSIVE because fewer than "
                    f"{_MIN_CORROBORATION_SIGNALS} independent signals are "
                    f"active. Additional evidence is needed for a definitive "
                    f"classification."
                )
            else:
                parts.append(
                    "Score falls in the inconclusive range between "
                    "low-risk and suspicious thresholds."
                )

        if missing_signals:
            parts.append(
                f"Note: {len(missing_signals)} signal(s) unavailable "
                f"({', '.join(missing_signals)}), which limits assessment "
                f"confidence."
            )

        # Component summary
        if breakdown:
            comp_str = ", ".join(
                f"{name}={val:.0f}" for name, val in breakdown.items()
            )
            parts.append(f"Component scores: {comp_str}.")

        return " ".join(parts)
