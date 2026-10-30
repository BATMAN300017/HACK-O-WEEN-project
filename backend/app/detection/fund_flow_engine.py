"""Fund-flow reconstruction and tracing engine.

Traces where money went after a seed transaction, handling splits, merges,
cross-country movement, and currency conversions. Calculates amount
attribution with uncertainty (money is fungible).

NEVER accesses ground-truth labels.

Typical usage:
    engine = FundFlowEngine(graph)
    trace = engine.trace_fund_flow(start_txn_id="TXN-001", max_hops=6)
    network = engine.reconstruct_network(seed_accounts=["ACC-A", "ACC-B"])
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx

from app.core.logging import logger

__all__ = [
    "FundFlowEngine",
    "FundFlowTrace",
    "FundFlowHop",
    "ReconstructedNetwork",
]


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------


@dataclass
class FundFlowHop:
    """A single hop in a fund-flow trace."""

    from_account: str
    to_account: str
    amount: float
    currency: str
    converted_amount: Optional[float] = None
    converted_currency: Optional[str] = None
    timestamp: Optional[datetime] = None
    hop_depth: int = 0
    country_from: str = "unknown"
    country_to: str = "unknown"
    bank_from: str = "unknown"
    bank_to: str = "unknown"
    attribution_confidence: float = 1.0  # 0-1
    transaction_id: str = ""


@dataclass
class FundFlowTrace:
    """Complete result of a fund-flow trace operation."""

    seed_transaction_id: str
    hops: List[FundFlowHop] = field(default_factory=list)
    total_hops: int = 0
    total_amount_traced: float = 0.0
    currencies_involved: List[str] = field(default_factory=list)
    countries_involved: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    uncertainty_notes: List[str] = field(default_factory=list)


@dataclass
class ReconstructedNetwork:
    """Result of reconstructing a network from seed accounts."""

    seed_accounts: List[str] = field(default_factory=list)
    accounts: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    total_volume: float = 0.0
    currencies_involved: List[str] = field(default_factory=list)
    countries_involved: List[str] = field(default_factory=list)
    depth_reached: int = 0


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _parse_ts(ts: Any) -> datetime:
    """Parse a timestamp to a timezone-aware datetime."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        cleaned = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    raise ValueError(f"Cannot parse timestamp: {ts!r}")


# --------------------------------------------------------------------------
# Fund-flow engine
# --------------------------------------------------------------------------


class FundFlowEngine:
    """Fund-flow reconstruction and tracing engine.

    Operates on a NetworkX MultiDiGraph built by ``graph_engine.build_transaction_graph``.

    Parameters
    ----------
    graph : nx.MultiDiGraph
        The transaction graph.  Nodes carry account metadata; edges carry
        transaction attributes (amount, currency, timestamp, payment_method,
        transaction_id).
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        # Build a transaction_id → edge lookup for fast seed resolution
        self._txn_index: Dict[str, Tuple[str, str, int]] = {}
        self._build_txn_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trace_fund_flow(
        self,
        start_txn_id: str,
        max_hops: int = 6,
        time_window_hours: float = 72.0,
    ) -> FundFlowTrace:
        """Trace where money went after a seed transaction.

        Follows outgoing edges from the receiver of the seed transaction,
        bounded by ``max_hops`` and a time window.

        Parameters
        ----------
        start_txn_id : str
            Transaction ID to start the trace from.
        max_hops : int
            Maximum depth of the trace.
        time_window_hours : float
            Only follow edges whose timestamp is within this window after
            the seed transaction.

        Returns
        -------
        FundFlowTrace
        """
        # Resolve seed transaction
        if start_txn_id not in self._txn_index:
            logger.warning(
                "Transaction %s not found in graph; cannot trace fund flow.",
                start_txn_id,
            )
            return FundFlowTrace(
                seed_transaction_id=start_txn_id,
                uncertainty_notes=[
                    f"Seed transaction {start_txn_id} not found in the "
                    f"transaction graph."
                ],
            )

        u, v, key = self._txn_index[start_txn_id]
        seed_data = self._graph.edges[u, v, key]
        seed_amount = float(seed_data["amount"])
        seed_time = seed_data["timestamp"]
        if not isinstance(seed_time, datetime):
            seed_time = _parse_ts(seed_time)

        time_limit = seed_time + timedelta(hours=time_window_hours)

        trace = FundFlowTrace(seed_transaction_id=start_txn_id)
        currencies_seen: Set[str] = {str(seed_data.get("currency", "unknown"))}
        countries_seen: Set[str] = set()
        timeline_events: List[Dict[str, Any]] = []

        # Add the seed hop
        seed_hop = self._make_hop(u, v, seed_data, depth=0, attribution=1.0)
        trace.hops.append(seed_hop)
        countries_seen.update(
            filter(lambda c: c != "unknown", [seed_hop.country_from, seed_hop.country_to])
        )
        timeline_events.append(self._timeline_entry(seed_hop))

        # BFS from the receiver of the seed transaction
        # (account, depth, remaining_amount, attribution_confidence)
        queue: deque[Tuple[str, int, float, float]] = deque()
        queue.append((v, 1, seed_amount, 1.0))
        visited_edges: Set[Tuple[str, str, int]] = {(u, v, key)}

        while queue:
            current_account, depth, remaining, parent_confidence = queue.popleft()

            if depth > max_hops:
                continue

            # Collect all outgoing edges from this account within time window
            outgoing_edges: List[Tuple[str, str, int, Dict[str, Any]]] = []
            for _, target, ekey, edata in self._graph.out_edges(
                current_account, data=True, keys=True
            ):
                edge_tuple = (current_account, target, ekey)
                if edge_tuple in visited_edges:
                    continue

                edge_time = edata.get("timestamp")
                if edge_time is not None:
                    if not isinstance(edge_time, datetime):
                        edge_time = _parse_ts(edge_time)
                    if edge_time < seed_time or edge_time > time_limit:
                        continue

                outgoing_edges.append(
                    (current_account, target, ekey, edata)
                )

            if not outgoing_edges:
                continue

            # Calculate attribution: split remaining funds among outgoing
            total_outgoing = sum(
                float(ed["amount"]) for _, _, _, ed in outgoing_edges
            )

            if total_outgoing > remaining * 1.5:
                # More money going out than came in → fungibility uncertainty
                trace.uncertainty_notes.append(
                    f"At account {current_account} (depth {depth}): "
                    f"outgoing total (${total_outgoing:,.2f}) exceeds "
                    f"traced incoming (${remaining:,.2f}). "
                    f"Money is fungible — attribution is uncertain."
                )

            for src, tgt, ek, ed in outgoing_edges:
                visited_edges.add((src, tgt, ek))
                edge_amount = float(ed["amount"])

                # Attribution: proportion of remaining funds this edge carries
                if total_outgoing > 0:
                    proportion = edge_amount / total_outgoing
                else:
                    proportion = 1.0 / len(outgoing_edges) if outgoing_edges else 0.0

                attributed_amount = min(edge_amount, remaining * proportion)
                confidence = parent_confidence * min(1.0, proportion)

                # Check for currency conversion
                edge_currency = str(ed.get("currency", "unknown"))
                sender_currency = self._graph.nodes.get(src, {}).get(
                    "currency", "unknown"
                )
                converted_amount: Optional[float] = None
                converted_currency: Optional[str] = None
                if (
                    edge_currency != "unknown"
                    and sender_currency != "unknown"
                    and edge_currency != sender_currency
                ):
                    converted_amount = edge_amount
                    converted_currency = edge_currency
                    trace.uncertainty_notes.append(
                        f"Currency conversion detected at hop depth {depth}: "
                        f"{sender_currency} → {edge_currency} "
                        f"(${edge_amount:,.2f}). Exchange rate unknown."
                    )

                hop = self._make_hop(
                    src, tgt, ed, depth=depth, attribution=confidence,
                    converted_amount=converted_amount,
                    converted_currency=converted_currency,
                )
                trace.hops.append(hop)
                currencies_seen.add(edge_currency)
                countries_seen.update(
                    filter(
                        lambda c: c != "unknown",
                        [hop.country_from, hop.country_to],
                    )
                )
                timeline_events.append(self._timeline_entry(hop))

                # Continue tracing from the target
                new_remaining = attributed_amount
                queue.append((tgt, depth + 1, new_remaining, confidence))

        # Finalise trace
        trace.total_hops = len(trace.hops)
        trace.total_amount_traced = round(
            sum(h.amount * h.attribution_confidence for h in trace.hops), 2
        )
        trace.currencies_involved = sorted(currencies_seen)
        trace.countries_involved = sorted(countries_seen)
        trace.timeline = sorted(
            timeline_events,
            key=lambda e: e.get("timestamp", ""),
        )

        logger.info(
            "Fund flow trace from %s: %d hops, %d currencies, %d countries",
            start_txn_id,
            trace.total_hops,
            len(trace.currencies_involved),
            len(trace.countries_involved),
        )

        return trace

    def reconstruct_network(
        self,
        seed_accounts: List[str],
        max_depth: int = 4,
    ) -> ReconstructedNetwork:
        """Build the full connected network from seed suspicious accounts.

        Expands outward from each seed account (both directions) up to
        ``max_depth`` hops.

        Parameters
        ----------
        seed_accounts : list[str]
            Starting account IDs.
        max_depth : int
            Maximum BFS depth from each seed.

        Returns
        -------
        ReconstructedNetwork
        """
        if not seed_accounts:
            return ReconstructedNetwork(seed_accounts=[])

        network_nodes: Set[str] = set()
        network_edges: List[Dict[str, Any]] = []
        max_depth_reached = 0
        currencies: Set[str] = set()
        countries: Set[str] = set()
        total_volume = 0.0

        # BFS from each seed, expanding in both directions
        for seed in seed_accounts:
            if seed not in self._graph:
                continue

            visited: Set[str] = {seed}
            frontier: deque[Tuple[str, int]] = deque([(seed, 0)])

            while frontier:
                current, depth = frontier.popleft()
                network_nodes.add(current)
                max_depth_reached = max(max_depth_reached, depth)

                node_data = self._graph.nodes.get(current, {})
                country = node_data.get("country", "unknown")
                if country != "unknown":
                    countries.add(country)

                if depth >= max_depth:
                    continue

                # Expand successors
                for _, target, edata in self._graph.out_edges(
                    current, data=True
                ):
                    edge_info = {
                        "from": current,
                        "to": target,
                        "amount": round(float(edata.get("amount", 0)), 2),
                        "currency": str(edata.get("currency", "unknown")),
                        "transaction_id": str(edata.get("transaction_id", "")),
                    }
                    network_edges.append(edge_info)
                    total_volume += edge_info["amount"]
                    currencies.add(edge_info["currency"])

                    if target not in visited:
                        visited.add(target)
                        frontier.append((target, depth + 1))

                # Expand predecessors
                for source, _, edata in self._graph.in_edges(
                    current, data=True
                ):
                    edge_info = {
                        "from": source,
                        "to": current,
                        "amount": round(float(edata.get("amount", 0)), 2),
                        "currency": str(edata.get("currency", "unknown")),
                        "transaction_id": str(edata.get("transaction_id", "")),
                    }
                    network_edges.append(edge_info)
                    total_volume += edge_info["amount"]
                    currencies.add(edge_info["currency"])

                    if source not in visited:
                        visited.add(source)
                        frontier.append((source, depth + 1))

        # Deduplicate edges by transaction_id
        seen_txn_ids: Set[str] = set()
        unique_edges: List[Dict[str, Any]] = []
        for edge in network_edges:
            txn_id = edge.get("transaction_id", "")
            if txn_id and txn_id in seen_txn_ids:
                continue
            seen_txn_ids.add(txn_id)
            unique_edges.append(edge)

        # Recalculate total volume from unique edges
        total_volume = sum(e["amount"] for e in unique_edges)

        currencies.discard("unknown")

        result = ReconstructedNetwork(
            seed_accounts=list(seed_accounts),
            accounts=sorted(network_nodes),
            edges=unique_edges,
            total_volume=round(total_volume, 2),
            currencies_involved=sorted(currencies),
            countries_involved=sorted(countries),
            depth_reached=max_depth_reached,
        )

        logger.info(
            "Network reconstructed from %d seeds: %d accounts, %d edges, "
            "%d countries, depth %d",
            len(seed_accounts),
            len(result.accounts),
            len(result.edges),
            len(result.countries_involved),
            result.depth_reached,
        )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_txn_index(self) -> None:
        """Index edges by transaction_id for O(1) lookup."""
        for u, v, key, data in self._graph.edges(keys=True, data=True):
            txn_id = data.get("transaction_id", "")
            if txn_id:
                self._txn_index[txn_id] = (u, v, key)

    def _make_hop(
        self,
        src: str,
        tgt: str,
        edge_data: Dict[str, Any],
        depth: int,
        attribution: float,
        converted_amount: Optional[float] = None,
        converted_currency: Optional[str] = None,
    ) -> FundFlowHop:
        """Create a FundFlowHop from graph edge data."""
        src_data = self._graph.nodes.get(src, {})
        tgt_data = self._graph.nodes.get(tgt, {})

        timestamp = edge_data.get("timestamp")
        if timestamp is not None and not isinstance(timestamp, datetime):
            timestamp = _parse_ts(timestamp)

        return FundFlowHop(
            from_account=src,
            to_account=tgt,
            amount=float(edge_data.get("amount", 0.0)),
            currency=str(edge_data.get("currency", "unknown")),
            converted_amount=converted_amount,
            converted_currency=converted_currency,
            timestamp=timestamp,
            hop_depth=depth,
            country_from=src_data.get("country", "unknown"),
            country_to=tgt_data.get("country", "unknown"),
            bank_from=src_data.get("bank", "unknown"),
            bank_to=tgt_data.get("bank", "unknown"),
            attribution_confidence=round(attribution, 4),
            transaction_id=str(edge_data.get("transaction_id", "")),
        )

    @staticmethod
    def _timeline_entry(hop: FundFlowHop) -> Dict[str, Any]:
        """Create a chronologically sortable timeline entry from a hop."""
        return {
            "timestamp": (
                hop.timestamp.isoformat() if hop.timestamp else ""
            ),
            "from": hop.from_account,
            "to": hop.to_account,
            "amount": hop.amount,
            "currency": hop.currency,
            "hop_depth": hop.hop_depth,
            "attribution_confidence": hop.attribution_confidence,
            "country_from": hop.country_from,
            "country_to": hop.country_to,
        }
