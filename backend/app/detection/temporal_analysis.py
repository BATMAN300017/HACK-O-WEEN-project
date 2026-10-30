"""Time-series pattern detection for individual account transaction streams.

Provides multiple temporal analysis functions that detect suspicious patterns
in transaction timing and amounts — pass-through behaviour, burst patterns,
fund redistribution, dormant reactivation, and repeated sequences.

Designed for unsupervised operation — NEVER accesses ground-truth labels.
All functions take transaction dicts with:
    id, amount, timestamp, sender_id, receiver_id, currency, direction (IN/OUT)

Typical usage:
    score, evidence = calculate_pass_through_score("ACC-123", transactions)
    score, evidence = detect_burst_patterns("ACC-123", transactions)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.logging import logger

__all__ = [
    "TemporalResult",
    "calculate_pass_through_score",
    "detect_burst_patterns",
    "calculate_redistribution_ratio",
    "detect_dormant_reactivation",
    "detect_repeated_sequences",
]

# --------------------------------------------------------------------------
# Shared result container
# --------------------------------------------------------------------------


@dataclass
class TemporalResult:
    """Result container for all temporal analysis functions."""

    score: float  # 0-100
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _parse_timestamp(ts: Any) -> datetime:
    """Parse a timestamp value into a timezone-aware datetime.

    Supports ISO-8601 strings and epoch floats/ints.  Naive datetimes are
    assumed to be UTC.
    """
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        # Handle common ISO formats, including trailing 'Z'.
        cleaned = ts.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"Cannot parse timestamp: {ts!r}")


def _sort_by_time(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a shallow copy of transactions sorted by timestamp ascending."""
    return sorted(transactions, key=lambda t: _parse_timestamp(t["timestamp"]))


def _split_directions(
    transactions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split transactions into (incoming, outgoing) lists."""
    incoming: List[Dict[str, Any]] = []
    outgoing: List[Dict[str, Any]] = []
    for txn in transactions:
        direction = str(txn.get("direction", "")).upper()
        if direction == "IN":
            incoming.append(txn)
        elif direction == "OUT":
            outgoing.append(txn)
    return incoming, outgoing


# --------------------------------------------------------------------------
# 1. Pass-Through Score
# --------------------------------------------------------------------------


def calculate_pass_through_score(
    account_id: str,
    transactions: List[Dict[str, Any]],
    max_gap_seconds: float = 3600.0,
) -> TemporalResult:
    """Measure how quickly incoming funds are forwarded out.

    A pass-through account receives money and forwards most of it within
    a short window.  This function measures the average time delta between
    incoming and subsequent outgoing transactions, weighted by overlap amount.

    Parameters
    ----------
    account_id : str
        The account under investigation.
    transactions : list[dict]
        Transaction records with ``timestamp``, ``amount``, ``direction``.
    max_gap_seconds : float
        Maximum time gap (seconds) between an IN and a subsequent OUT to
        be considered "pass-through".

    Returns
    -------
    TemporalResult
    """
    if not transactions:
        return TemporalResult(
            score=0.0,
            evidence=[f"No transactions for account {account_id}."],
        )

    sorted_txns = _sort_by_time(transactions)
    incoming, outgoing = _split_directions(sorted_txns)

    if not incoming or not outgoing:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id} has only "
                f"{'incoming' if incoming else 'outgoing'} transactions; "
                f"pass-through analysis requires both directions."
            ],
        )

    matched_deltas: List[float] = []
    matched_volume = 0.0
    total_in_volume = sum(float(t["amount"]) for t in incoming)

    out_idx = 0
    for in_txn in incoming:
        in_time = _parse_timestamp(in_txn["timestamp"])
        in_amount = float(in_txn["amount"])

        # Search forward in outgoing for a match within the gap
        for j in range(out_idx, len(outgoing)):
            out_time = _parse_timestamp(outgoing[j]["timestamp"])
            delta = (out_time - in_time).total_seconds()
            if delta < 0:
                continue
            if delta > max_gap_seconds:
                break
            matched_deltas.append(delta)
            matched_volume += min(in_amount, float(outgoing[j]["amount"]))
            break

    if not matched_deltas:
        return TemporalResult(
            score=5.0,
            evidence=[
                f"Account {account_id}: no rapid in→out pairings found "
                f"within {max_gap_seconds/60:.0f}-minute window."
            ],
        )

    avg_delta = float(np.mean(matched_deltas))
    pass_ratio = matched_volume / total_in_volume if total_in_volume > 0 else 0.0

    # Score: short average delta + high pass ratio → high score
    time_factor = max(0.0, 1.0 - avg_delta / max_gap_seconds)
    score = round(min(100.0, time_factor * pass_ratio * 100.0), 1)

    evidence = [
        f"Account {account_id}: {len(matched_deltas)} in→out pairings found.",
        f"Average forwarding delay: {avg_delta:.0f}s.",
        f"Matched volume ratio: {pass_ratio:.1%} of total incoming.",
        f"Pass-through score: {score}/100.",
    ]

    return TemporalResult(
        score=score,
        evidence=evidence,
        metadata={
            "avg_delta_seconds": round(avg_delta, 1),
            "pass_ratio": round(pass_ratio, 3),
            "matched_pairs": len(matched_deltas),
            "total_incoming_txns": len(incoming),
        },
    )


# --------------------------------------------------------------------------
# 2. Burst Pattern Detection
# --------------------------------------------------------------------------


def detect_burst_patterns(
    account_id: str,
    transactions: List[Dict[str, Any]],
    window_seconds: float = 600.0,
    burst_threshold: int = 5,
) -> TemporalResult:
    """Detect sudden spikes in transaction frequency.

    Slides a window across the transaction timeline and flags periods
    where the count exceeds the burst threshold.

    Parameters
    ----------
    account_id : str
    transactions : list[dict]
    window_seconds : float
        Sliding window size in seconds (default 10 minutes).
    burst_threshold : int
        Minimum transactions within the window to constitute a burst.

    Returns
    -------
    TemporalResult
    """
    if len(transactions) < burst_threshold:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: only {len(transactions)} transactions, "
                f"below burst threshold of {burst_threshold}."
            ],
        )

    sorted_txns = _sort_by_time(transactions)
    timestamps = [_parse_timestamp(t["timestamp"]) for t in sorted_txns]

    bursts: List[Dict[str, Any]] = []
    i = 0
    while i < len(timestamps):
        j = i
        while (
            j < len(timestamps)
            and (timestamps[j] - timestamps[i]).total_seconds() <= window_seconds
        ):
            j += 1
        window_count = j - i
        if window_count >= burst_threshold:
            window_volume = sum(
                float(sorted_txns[k]["amount"]) for k in range(i, j)
            )
            bursts.append(
                {
                    "start": timestamps[i].isoformat(),
                    "end": timestamps[min(j - 1, len(timestamps) - 1)].isoformat(),
                    "count": window_count,
                    "volume": round(window_volume, 2),
                }
            )
            i = j  # skip past this burst
        else:
            i += 1

    if not bursts:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: no burst patterns detected "
                f"(window={window_seconds/60:.0f}min, threshold={burst_threshold})."
            ],
        )

    max_burst_count = max(b["count"] for b in bursts)
    # Score ramps up with burst intensity
    intensity = min(1.0, (max_burst_count - burst_threshold + 1) / 10.0)
    frequency_factor = min(1.0, len(bursts) / 5.0)
    score = round(min(100.0, (intensity * 0.6 + frequency_factor * 0.4) * 100.0), 1)

    evidence = [
        f"Account {account_id}: {len(bursts)} burst period(s) detected.",
        f"Largest burst: {max_burst_count} transactions in "
        f"{window_seconds/60:.0f}-minute window.",
        f"Burst score: {score}/100.",
    ]

    return TemporalResult(
        score=score,
        evidence=evidence,
        metadata={"bursts": bursts, "max_burst_count": max_burst_count},
    )


# --------------------------------------------------------------------------
# 3. Redistribution Ratio
# --------------------------------------------------------------------------


def calculate_redistribution_ratio(
    account_id: str,
    transactions: List[Dict[str, Any]],
    windows_hours: Optional[List[float]] = None,
) -> TemporalResult:
    """Calculate what percentage of incoming funds leave within time windows.

    Parameters
    ----------
    account_id : str
    transactions : list[dict]
    windows_hours : list[float] | None
        Time windows to evaluate (default: [1, 6, 24] hours).

    Returns
    -------
    TemporalResult
    """
    if windows_hours is None:
        windows_hours = [1.0, 6.0, 24.0]

    if not transactions:
        return TemporalResult(
            score=0.0,
            evidence=[f"No transactions for account {account_id}."],
        )

    sorted_txns = _sort_by_time(transactions)
    incoming, outgoing = _split_directions(sorted_txns)

    if not incoming or not outgoing:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id} lacks both incoming and outgoing "
                f"transactions for redistribution analysis."
            ],
        )

    total_in = sum(float(t["amount"]) for t in incoming)
    ratios: Dict[str, float] = {}

    for window_h in windows_hours:
        window_sec = window_h * 3600.0
        redistributed = 0.0

        for in_txn in incoming:
            in_time = _parse_timestamp(in_txn["timestamp"])
            for out_txn in outgoing:
                out_time = _parse_timestamp(out_txn["timestamp"])
                delta = (out_time - in_time).total_seconds()
                if 0 <= delta <= window_sec:
                    redistributed += float(out_txn["amount"])

        ratio = min(1.0, redistributed / total_in) if total_in > 0 else 0.0
        ratios[f"{window_h}h"] = round(ratio, 3)

    # Score based on shortest-window ratio being high
    shortest_ratio = ratios.get(f"{windows_hours[0]}h", 0.0)
    mid_ratio = ratios.get(f"{windows_hours[1]}h", 0.0) if len(windows_hours) > 1 else 0.0
    score = round(
        min(100.0, shortest_ratio * 60.0 + mid_ratio * 30.0 + 10.0 * (mid_ratio > 0.5)),
        1,
    )

    evidence = [
        f"Account {account_id} redistribution analysis:",
    ]
    for label, ratio in ratios.items():
        evidence.append(f"  {label} window: {ratio:.1%} of incoming funds redistributed.")
    evidence.append(f"Redistribution score: {score}/100.")

    return TemporalResult(
        score=score,
        evidence=evidence,
        metadata={"ratios": ratios, "total_incoming": round(total_in, 2)},
    )


# --------------------------------------------------------------------------
# 4. Dormant Reactivation
# --------------------------------------------------------------------------


def detect_dormant_reactivation(
    account_id: str,
    transactions: List[Dict[str, Any]],
    dormancy_days: float = 90.0,
    burst_count: int = 3,
) -> TemporalResult:
    """Detect long inactivity followed by sudden activity.

    Parameters
    ----------
    account_id : str
    transactions : list[dict]
    dormancy_days : float
        Minimum gap (in days) to consider an account dormant.
    burst_count : int
        Minimum transactions after reactivation to flag.

    Returns
    -------
    TemporalResult
    """
    if len(transactions) < 2:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: fewer than 2 transactions, "
                f"cannot assess dormancy."
            ],
        )

    sorted_txns = _sort_by_time(transactions)
    timestamps = [_parse_timestamp(t["timestamp"]) for t in sorted_txns]

    # Find the largest gap
    max_gap_days = 0.0
    reactivation_idx = -1
    for i in range(1, len(timestamps)):
        gap_days = (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400.0
        if gap_days > max_gap_days:
            max_gap_days = gap_days
            reactivation_idx = i

    if max_gap_days < dormancy_days:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: maximum inactivity gap is "
                f"{max_gap_days:.1f} days (threshold: {dormancy_days} days). "
                f"No dormancy detected."
            ],
        )

    # Count activity after reactivation
    post_reactivation = sorted_txns[reactivation_idx:]
    post_count = len(post_reactivation)
    post_volume = sum(float(t["amount"]) for t in post_reactivation)

    # Calculate how rapidly the post-reactivation activity occurs
    if post_count >= 2:
        post_span = (
            _parse_timestamp(post_reactivation[-1]["timestamp"])
            - _parse_timestamp(post_reactivation[0]["timestamp"])
        ).total_seconds() / 3600.0  # hours
    else:
        post_span = 0.0

    is_burst = post_count >= burst_count

    # Score: dormancy length × post-reactivation intensity
    dormancy_factor = min(1.0, max_gap_days / 365.0)
    intensity_factor = min(1.0, post_count / 10.0) if is_burst else 0.3
    score = round(min(100.0, (dormancy_factor * 0.4 + intensity_factor * 0.6) * 100.0), 1)

    evidence = [
        f"Account {account_id}: dormant for {max_gap_days:.0f} days.",
        f"Reactivated with {post_count} transaction(s) "
        f"totaling ${post_volume:,.2f}.",
    ]
    if post_span > 0:
        evidence.append(
            f"Post-reactivation activity spans {post_span:.1f} hours."
        )
    if is_burst:
        evidence.append("Activity constitutes a burst pattern after dormancy.")
    evidence.append(f"Dormant reactivation score: {score}/100.")

    return TemporalResult(
        score=score,
        evidence=evidence,
        metadata={
            "dormancy_days": round(max_gap_days, 1),
            "post_reactivation_count": post_count,
            "post_reactivation_volume": round(post_volume, 2),
            "post_span_hours": round(post_span, 1),
        },
    )


# --------------------------------------------------------------------------
# 5. Repeated Sequences
# --------------------------------------------------------------------------


def detect_repeated_sequences(
    account_id: str,
    transactions: List[Dict[str, Any]],
    min_repetitions: int = 3,
    amount_tolerance: float = 0.01,
) -> TemporalResult:
    """Detect repeated same-amount transfers to the same counterparties.

    Parameters
    ----------
    account_id : str
    transactions : list[dict]
    min_repetitions : int
        Minimum number of identical (amount, counterparty) pairs.
    amount_tolerance : float
        Relative tolerance for amount matching (1% default).

    Returns
    -------
    TemporalResult
    """
    if len(transactions) < min_repetitions:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: fewer than {min_repetitions} "
                f"transactions; cannot detect repeated sequences."
            ],
        )

    # Group by (rounded_amount, counterparty)
    pattern_counter: Dict[Tuple[float, str], int] = Counter()

    for txn in transactions:
        amount = float(txn["amount"])
        # Determine counterparty based on direction
        direction = str(txn.get("direction", "")).upper()
        if direction == "OUT":
            counterparty = str(txn.get("receiver_id", "unknown"))
        else:
            counterparty = str(txn.get("sender_id", "unknown"))

        # Round to tolerance bucket for fuzzy matching
        bucket = round(amount / max(amount * amount_tolerance, 0.01)) * max(
            amount * amount_tolerance, 0.01
        )
        pattern_counter[(bucket, counterparty)] += 1

    repeated = {
        k: v for k, v in pattern_counter.items() if v >= min_repetitions
    }

    if not repeated:
        return TemporalResult(
            score=0.0,
            evidence=[
                f"Account {account_id}: no repeated transfer sequences "
                f"detected (min_repetitions={min_repetitions})."
            ],
        )

    total_repeated_txns = sum(repeated.values())
    max_reps = max(repeated.values())
    unique_patterns = len(repeated)

    # Score: more patterns and higher repetition → higher risk
    rep_factor = min(1.0, max_reps / 10.0)
    pattern_factor = min(1.0, unique_patterns / 5.0)
    coverage = total_repeated_txns / len(transactions) if transactions else 0.0

    score = round(
        min(100.0, (rep_factor * 0.4 + pattern_factor * 0.3 + coverage * 0.3) * 100.0),
        1,
    )

    evidence = [
        f"Account {account_id}: {unique_patterns} repeated transfer pattern(s) detected.",
        f"Most repeated pattern: {max_reps} occurrences.",
        f"Total transactions in repeated patterns: {total_repeated_txns}/{len(transactions)}.",
        f"Repeated sequence score: {score}/100.",
    ]

    pattern_details = []
    for (amt, cp), count in sorted(repeated.items(), key=lambda x: -x[1]):
        pattern_details.append(
            {"amount_bucket": round(amt, 2), "counterparty": cp, "count": count}
        )

    return TemporalResult(
        score=score,
        evidence=evidence,
        metadata={
            "repeated_patterns": pattern_details,
            "total_repeated_txns": total_repeated_txns,
            "coverage_ratio": round(coverage, 3),
        },
    )
