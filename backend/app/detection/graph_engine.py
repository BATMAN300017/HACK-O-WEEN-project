"""Enhanced graph-based detection engine using NetworkX.

Builds directed, weighted, timestamped multigraphs from transaction data and
provides a comprehensive suite of structural pattern detectors — fan-in,
fan-out, multi-hop chains, split-and-merge, circular flows, pass-through
accounts, connected clusters, cross-bank/border chains, and centrality.

Designed with an abstract interface (``GraphDetectorInterface``) so the
implementation can later migrate to a graph database backend.

NEVER accesses ground-truth labels.

Graph structure:
    - Nodes: accounts with attributes {account_id, bank, country, currency}
    - Edges: transactions with attributes {amount, currency, timestamp,
      payment_method, transaction_id}
"""

from __future__ import annotations

import abc
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
)

import networkx as nx
import numpy as np

from app.core.logging import logger

__all__ = [
    "GraphDetectorInterface",
    "NetworkXGraphEngine",
    "GraphPatternResult",
    "build_transaction_graph",
    "detect_fan_in",
    "detect_fan_out",
    "detect_multi_hop_chains",
    "detect_split_and_merge",
    "detect_circular_flows",
    "detect_pass_through_accounts",
    "find_connected_clusters",
    "detect_cross_bank_chains",
    "detect_cross_border_chains",
    "calculate_pagerank_centrality",
]


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------


@dataclass
class GraphPatternResult:
    """Container for a single graph-pattern detection result."""

    pattern_type: str
    score: float  # 0-100
    accounts_involved: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Abstract interface — allows future migration to a graph database
# --------------------------------------------------------------------------


class GraphDetectorInterface(abc.ABC):
    """Abstract interface for graph-based fraud detection.

    Implementors must provide a method to build the graph and methods to
    detect each pattern.  This allows swapping NetworkX for Neo4j, TigerGraph,
    etc. without changing calling code.
    """

    @abc.abstractmethod
    def build_graph(self, transactions: Iterable[Dict[str, Any]]) -> Any:
        """Build the transaction graph from raw transaction dicts."""
        ...

    @abc.abstractmethod
    def fan_in(self, account_id: str, threshold: int) -> GraphPatternResult:
        ...

    @abc.abstractmethod
    def fan_out(self, account_id: str, threshold: int) -> GraphPatternResult:
        ...

    @abc.abstractmethod
    def multi_hop_chains(
        self, account_id: str, max_depth: int
    ) -> GraphPatternResult:
        ...

    @abc.abstractmethod
    def circular_flows(self, max_length: int) -> List[GraphPatternResult]:
        ...

    @abc.abstractmethod
    def pass_through_accounts(self) -> List[GraphPatternResult]:
        ...

    @abc.abstractmethod
    def connected_clusters(self, min_size: int) -> List[GraphPatternResult]:
        ...

    @abc.abstractmethod
    def pagerank_centrality(self) -> Dict[str, float]:
        ...


# --------------------------------------------------------------------------
# Internal timestamp helper
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
# Graph construction
# --------------------------------------------------------------------------


def build_transaction_graph(
    transactions_iter: Iterable[Dict[str, Any]],
) -> nx.MultiDiGraph:
    """Build a directed, weighted, timestamped multigraph from transactions.

    Parameters
    ----------
    transactions_iter : iterable[dict]
        Each dict should have:
        - ``sender_id``, ``receiver_id`` (account identifiers)
        - ``amount``, ``currency``, ``timestamp``
        - ``payment_method``, ``transaction_id``
        - Optional node metadata: ``sender_bank``, ``sender_country``,
          ``sender_currency``, ``receiver_bank``, ``receiver_country``,
          ``receiver_currency``

    Returns
    -------
    nx.MultiDiGraph
    """
    G = nx.MultiDiGraph()

    for txn in transactions_iter:
        sender = str(txn["sender_id"])
        receiver = str(txn["receiver_id"])

        # Ensure sender node exists with metadata
        if sender not in G:
            G.add_node(
                sender,
                account_id=sender,
                bank=txn.get("sender_bank", "unknown"),
                country=txn.get("sender_country", "unknown"),
                currency=txn.get("sender_currency", txn.get("currency", "unknown")),
            )
        else:
            # Update metadata if richer info is available
            if txn.get("sender_bank"):
                G.nodes[sender]["bank"] = txn["sender_bank"]
            if txn.get("sender_country"):
                G.nodes[sender]["country"] = txn["sender_country"]

        # Ensure receiver node exists
        if receiver not in G:
            G.add_node(
                receiver,
                account_id=receiver,
                bank=txn.get("receiver_bank", "unknown"),
                country=txn.get("receiver_country", "unknown"),
                currency=txn.get(
                    "receiver_currency", txn.get("currency", "unknown")
                ),
            )
        else:
            if txn.get("receiver_bank"):
                G.nodes[receiver]["bank"] = txn["receiver_bank"]
            if txn.get("receiver_country"):
                G.nodes[receiver]["country"] = txn["receiver_country"]

        # Add edge
        G.add_edge(
            sender,
            receiver,
            amount=float(txn.get("amount", 0.0)),
            currency=str(txn.get("currency", "unknown")),
            timestamp=_parse_ts(txn["timestamp"]),
            payment_method=str(txn.get("payment_method", "unknown")),
            transaction_id=str(txn.get("transaction_id", txn.get("id", ""))),
        )

    logger.info(
        "Transaction graph built: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


# --------------------------------------------------------------------------
# Pattern detectors (module-level functions)
# --------------------------------------------------------------------------


def detect_fan_in(
    graph: nx.MultiDiGraph,
    account_id: str,
    threshold: int = 4,
) -> GraphPatternResult:
    """Detect fan-in: many distinct sources sending to one account.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    account_id : str
    threshold : int
        Minimum distinct incoming sources to flag.

    Returns
    -------
    GraphPatternResult
    """
    if account_id not in graph:
        return GraphPatternResult(
            pattern_type="FAN_IN",
            score=0.0,
            evidence=[f"Account {account_id} not found in graph."],
        )

    predecessors = set(graph.predecessors(account_id))
    in_degree = len(predecessors)

    if in_degree < threshold:
        return GraphPatternResult(
            pattern_type="FAN_IN",
            score=0.0,
            accounts_involved=[account_id],
            evidence=[
                f"Account {account_id}: {in_degree} incoming sources "
                f"(threshold {threshold})."
            ],
        )

    # Aggregate incoming volume
    total_volume = sum(
        d["amount"]
        for u in predecessors
        for _, _, d in graph.edges(u, data=True)
        if _ == account_id or d.get("transaction_id")  # all edges to target
    )
    # More precise: sum edges terminating at account_id
    total_volume = 0.0
    for pred in predecessors:
        for _, _, d in graph.edges(pred, data=True):
            if _ == account_id:
                pass  # edges() gives (u,v,data) for MultiDiGraph
        # Use in_edges instead
    total_volume = sum(
        d["amount"] for _, _, d in graph.in_edges(account_id, data=True)
    )

    score = round(min(100.0, (in_degree / (threshold * 3)) * 100.0), 1)

    return GraphPatternResult(
        pattern_type="FAN_IN",
        score=score,
        accounts_involved=[account_id] + list(predecessors),
        evidence=[
            f"Account {account_id} receives from {in_degree} distinct sources.",
            f"Total incoming volume: ${total_volume:,.2f}.",
            f"Fan-in score: {score}/100.",
        ],
        metadata={"in_degree": in_degree, "total_volume": round(total_volume, 2)},
    )


def detect_fan_out(
    graph: nx.MultiDiGraph,
    account_id: str,
    threshold: int = 4,
) -> GraphPatternResult:
    """Detect fan-out: one account sending to many distinct destinations.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    account_id : str
    threshold : int

    Returns
    -------
    GraphPatternResult
    """
    if account_id not in graph:
        return GraphPatternResult(
            pattern_type="FAN_OUT",
            score=0.0,
            evidence=[f"Account {account_id} not found in graph."],
        )

    successors = set(graph.successors(account_id))
    out_degree = len(successors)

    if out_degree < threshold:
        return GraphPatternResult(
            pattern_type="FAN_OUT",
            score=0.0,
            accounts_involved=[account_id],
            evidence=[
                f"Account {account_id}: {out_degree} outgoing destinations "
                f"(threshold {threshold})."
            ],
        )

    total_volume = sum(
        d["amount"] for _, _, d in graph.out_edges(account_id, data=True)
    )

    score = round(min(100.0, (out_degree / (threshold * 3)) * 100.0), 1)

    return GraphPatternResult(
        pattern_type="FAN_OUT",
        score=score,
        accounts_involved=[account_id] + list(successors),
        evidence=[
            f"Account {account_id} sends to {out_degree} distinct destinations.",
            f"Total outgoing volume: ${total_volume:,.2f}.",
            f"Fan-out score: {score}/100.",
        ],
        metadata={"out_degree": out_degree, "total_volume": round(total_volume, 2)},
    )


def detect_multi_hop_chains(
    graph: nx.MultiDiGraph,
    account_id: str,
    max_depth: int = 5,
) -> GraphPatternResult:
    """Trace multi-hop money paths originating from an account.

    Uses BFS up to ``max_depth`` hops, following directed edges.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    account_id : str
    max_depth : int

    Returns
    -------
    GraphPatternResult
    """
    if account_id not in graph:
        return GraphPatternResult(
            pattern_type="MULTI_HOP_CHAIN",
            score=0.0,
            evidence=[f"Account {account_id} not found in graph."],
        )

    # BFS with depth tracking
    visited: Set[str] = {account_id}
    frontier: List[Tuple[str, int]] = [(account_id, 0)]
    chains: List[List[str]] = []
    longest_chain = 0

    while frontier:
        current, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for succ in graph.successors(current):
            if succ not in visited:
                visited.add(succ)
                frontier.append((succ, depth + 1))
                longest_chain = max(longest_chain, depth + 1)

    reachable = visited - {account_id}

    if longest_chain <= 1:
        return GraphPatternResult(
            pattern_type="MULTI_HOP_CHAIN",
            score=0.0,
            accounts_involved=[account_id],
            evidence=[
                f"Account {account_id}: no multi-hop chains detected "
                f"(max_depth={max_depth})."
            ],
        )

    score = round(min(100.0, (longest_chain / max_depth) * 70.0 + len(reachable) * 2.0), 1)

    return GraphPatternResult(
        pattern_type="MULTI_HOP_CHAIN",
        score=score,
        accounts_involved=[account_id] + list(reachable),
        evidence=[
            f"Account {account_id}: longest chain depth = {longest_chain}.",
            f"Reachable accounts: {len(reachable)}.",
            f"Multi-hop chain score: {score}/100.",
        ],
        metadata={
            "longest_chain": longest_chain,
            "reachable_count": len(reachable),
        },
    )


def detect_split_and_merge(
    graph: nx.MultiDiGraph,
) -> List[GraphPatternResult]:
    """Find accounts that split incoming funds and merge downstream.

    A "split" node has 1-2 predecessors and ≥3 successors.
    A "merge" node has ≥3 predecessors and 1-2 successors.
    Flagged when a split node is upstream of a merge node within 3 hops.

    Returns
    -------
    list[GraphPatternResult]
    """
    results: List[GraphPatternResult] = []
    simple = nx.DiGraph(graph)  # collapse multi-edges for topology

    split_nodes: Set[str] = set()
    merge_nodes: Set[str] = set()

    for node in simple.nodes():
        in_deg = simple.in_degree(node)
        out_deg = simple.out_degree(node)
        if in_deg <= 2 and out_deg >= 3:
            split_nodes.add(node)
        if in_deg >= 3 and out_deg <= 2:
            merge_nodes.add(node)

    # Check split→merge connectivity
    for split in split_nodes:
        for merge in merge_nodes:
            if split == merge:
                continue
            try:
                path_len = nx.shortest_path_length(simple, split, merge)
                if path_len <= 3:
                    score = round(min(100.0, 50.0 + (3 - path_len) * 15.0), 1)
                    results.append(
                        GraphPatternResult(
                            pattern_type="SPLIT_AND_MERGE",
                            score=score,
                            accounts_involved=[split, merge],
                            evidence=[
                                f"Split node {split} (out-degree "
                                f"{simple.out_degree(split)}) connects to "
                                f"merge node {merge} (in-degree "
                                f"{simple.in_degree(merge)}) within "
                                f"{path_len} hop(s).",
                                f"Score: {score}/100.",
                            ],
                            metadata={
                                "split_node": split,
                                "merge_node": merge,
                                "path_length": path_len,
                            },
                        )
                    )
            except nx.NetworkXNoPath:
                continue

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="SPLIT_AND_MERGE",
                score=0.0,
                evidence=["No split-and-merge patterns detected."],
            )
        )

    return results


def detect_circular_flows(
    graph: nx.MultiDiGraph,
    max_length: int = 6,
) -> List[GraphPatternResult]:
    """Find closed cycles in the transaction graph.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    max_length : int
        Maximum cycle length to search for.

    Returns
    -------
    list[GraphPatternResult]
    """
    simple = nx.DiGraph(graph)
    results: List[GraphPatternResult] = []

    try:
        cycles = list(nx.simple_cycles(simple, length_bound=max_length))
    except TypeError:
        # Older networkx versions don't support length_bound
        all_cycles = list(nx.simple_cycles(simple))
        cycles = [c for c in all_cycles if len(c) <= max_length]

    # Limit to top 50 cycles to avoid excessive output
    cycles = cycles[:50]

    for cycle in cycles:
        cycle_len = len(cycle)
        # Shorter cycles are more suspicious
        score = round(min(100.0, 40.0 + (max_length - cycle_len + 1) * 12.0), 1)

        # Calculate total volume in cycle
        total_volume = 0.0
        for i in range(cycle_len):
            u = cycle[i]
            v = cycle[(i + 1) % cycle_len]
            if graph.has_edge(u, v):
                for _, _, d in graph.edges(u, data=True):
                    total_volume += d.get("amount", 0.0)

        results.append(
            GraphPatternResult(
                pattern_type="CIRCULAR_FLOW",
                score=score,
                accounts_involved=list(cycle),
                evidence=[
                    f"Circular flow of length {cycle_len}: "
                    f"{' → '.join(cycle)} → {cycle[0]}.",
                    f"Estimated cycle volume: ${total_volume:,.2f}.",
                    f"Circular flow score: {score}/100.",
                ],
                metadata={
                    "cycle": cycle,
                    "cycle_length": cycle_len,
                    "estimated_volume": round(total_volume, 2),
                },
            )
        )

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="CIRCULAR_FLOW",
                score=0.0,
                evidence=[
                    f"No circular flows detected (max_length={max_length})."
                ],
            )
        )

    return results


def detect_pass_through_accounts(
    graph: nx.MultiDiGraph,
    in_degree_min: int = 3,
    out_degree_min: int = 3,
) -> List[GraphPatternResult]:
    """Identify accounts with high in-degree AND high out-degree.

    These accounts act as intermediaries — they collect funds from multiple
    sources and distribute to multiple destinations.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    in_degree_min : int
    out_degree_min : int

    Returns
    -------
    list[GraphPatternResult]
    """
    simple = nx.DiGraph(graph)
    results: List[GraphPatternResult] = []

    for node in simple.nodes():
        in_deg = simple.in_degree(node)
        out_deg = simple.out_degree(node)

        if in_deg >= in_degree_min and out_deg >= out_degree_min:
            total_in = sum(
                d["amount"] for _, _, d in graph.in_edges(node, data=True)
            )
            total_out = sum(
                d["amount"] for _, _, d in graph.out_edges(node, data=True)
            )
            pass_ratio = total_out / total_in if total_in > 0 else 0.0

            # Higher score when pass-through ratio ≈ 1.0
            ratio_factor = 1.0 - abs(pass_ratio - 1.0)
            ratio_factor = max(0.0, ratio_factor)
            degree_factor = min(1.0, (in_deg + out_deg) / 20.0)
            score = round(
                min(100.0, (ratio_factor * 0.6 + degree_factor * 0.4) * 100.0),
                1,
            )

            results.append(
                GraphPatternResult(
                    pattern_type="PASS_THROUGH",
                    score=score,
                    accounts_involved=[node],
                    evidence=[
                        f"Account {node}: in-degree={in_deg}, "
                        f"out-degree={out_deg}.",
                        f"Total in: ${total_in:,.2f}, total out: "
                        f"${total_out:,.2f}, pass-through ratio: "
                        f"{pass_ratio:.2f}.",
                        f"Pass-through score: {score}/100.",
                    ],
                    metadata={
                        "in_degree": in_deg,
                        "out_degree": out_deg,
                        "total_in": round(total_in, 2),
                        "total_out": round(total_out, 2),
                        "pass_ratio": round(pass_ratio, 3),
                    },
                )
            )

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="PASS_THROUGH",
                score=0.0,
                evidence=["No pass-through accounts detected."],
            )
        )

    return results


def find_connected_clusters(
    graph: nx.MultiDiGraph,
    min_size: int = 3,
) -> List[GraphPatternResult]:
    """Find connected sub-networks of suspicious size.

    Uses weakly connected components on the underlying undirected graph.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    min_size : int

    Returns
    -------
    list[GraphPatternResult]
    """
    results: List[GraphPatternResult] = []

    for component in nx.weakly_connected_components(graph):
        if len(component) >= min_size:
            subgraph = graph.subgraph(component)
            edge_count = subgraph.number_of_edges()
            total_volume = sum(
                d["amount"] for _, _, d in subgraph.edges(data=True)
            )
            density = nx.density(subgraph)

            score = round(
                min(100.0, len(component) * 5.0 + density * 40.0 + 10.0), 1
            )

            results.append(
                GraphPatternResult(
                    pattern_type="CONNECTED_CLUSTER",
                    score=score,
                    accounts_involved=list(component),
                    evidence=[
                        f"Connected cluster of {len(component)} accounts, "
                        f"{edge_count} edges.",
                        f"Total volume: ${total_volume:,.2f}, "
                        f"density: {density:.3f}.",
                        f"Cluster score: {score}/100.",
                    ],
                    metadata={
                        "size": len(component),
                        "edge_count": edge_count,
                        "total_volume": round(total_volume, 2),
                        "density": round(density, 4),
                    },
                )
            )

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="CONNECTED_CLUSTER",
                score=0.0,
                evidence=[
                    f"No connected clusters of size ≥ {min_size} found."
                ],
            )
        )

    return results


def detect_cross_bank_chains(
    graph: nx.MultiDiGraph,
    min_banks: int = 2,
    max_depth: int = 5,
) -> List[GraphPatternResult]:
    """Detect multi-hop chains crossing different banks.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    min_banks : int
        Minimum distinct banks in a chain to flag.
    max_depth : int

    Returns
    -------
    list[GraphPatternResult]
    """
    results: List[GraphPatternResult] = []
    simple = nx.DiGraph(graph)

    # For each source node with out-edges, do BFS
    for source in simple.nodes():
        if simple.out_degree(source) == 0:
            continue

        visited: Dict[str, int] = {source: 0}
        frontier = [(source, 0)]
        banks_seen: Set[str] = {graph.nodes[source].get("bank", "unknown")}

        while frontier:
            current, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for succ in simple.successors(current):
                if succ not in visited:
                    visited[succ] = depth + 1
                    frontier.append((succ, depth + 1))
                    banks_seen.add(graph.nodes[succ].get("bank", "unknown"))

        banks_seen.discard("unknown")

        if len(banks_seen) >= min_banks and len(visited) > 2:
            chain_accounts = list(visited.keys())
            max_chain_depth = max(visited.values())
            score = round(
                min(
                    100.0,
                    len(banks_seen) * 15.0 + max_chain_depth * 10.0,
                ),
                1,
            )

            results.append(
                GraphPatternResult(
                    pattern_type="CROSS_BANK_CHAIN",
                    score=score,
                    accounts_involved=chain_accounts,
                    evidence=[
                        f"Chain from {source}: spans {len(banks_seen)} banks "
                        f"over {max_chain_depth} hops.",
                        f"Banks involved: {', '.join(sorted(banks_seen))}.",
                        f"Cross-bank score: {score}/100.",
                    ],
                    metadata={
                        "source": source,
                        "banks": sorted(banks_seen),
                        "max_depth": max_chain_depth,
                        "chain_size": len(chain_accounts),
                    },
                )
            )

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="CROSS_BANK_CHAIN",
                score=0.0,
                evidence=["No cross-bank chains detected."],
            )
        )

    return results


def detect_cross_border_chains(
    graph: nx.MultiDiGraph,
    min_countries: int = 2,
    max_depth: int = 5,
) -> List[GraphPatternResult]:
    """Detect multi-hop chains crossing country borders.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    min_countries : int
    max_depth : int

    Returns
    -------
    list[GraphPatternResult]
    """
    results: List[GraphPatternResult] = []
    simple = nx.DiGraph(graph)

    for source in simple.nodes():
        if simple.out_degree(source) == 0:
            continue

        visited: Dict[str, int] = {source: 0}
        frontier = [(source, 0)]
        countries_seen: Set[str] = {
            graph.nodes[source].get("country", "unknown")
        }

        while frontier:
            current, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for succ in simple.successors(current):
                if succ not in visited:
                    visited[succ] = depth + 1
                    frontier.append((succ, depth + 1))
                    countries_seen.add(
                        graph.nodes[succ].get("country", "unknown")
                    )

        countries_seen.discard("unknown")

        if len(countries_seen) >= min_countries and len(visited) > 2:
            chain_accounts = list(visited.keys())
            max_chain_depth = max(visited.values())
            score = round(
                min(
                    100.0,
                    len(countries_seen) * 18.0 + max_chain_depth * 8.0,
                ),
                1,
            )

            results.append(
                GraphPatternResult(
                    pattern_type="CROSS_BORDER_CHAIN",
                    score=score,
                    accounts_involved=chain_accounts,
                    evidence=[
                        f"Chain from {source}: spans {len(countries_seen)} "
                        f"countries over {max_chain_depth} hops.",
                        f"Countries: {', '.join(sorted(countries_seen))}.",
                        f"Cross-border score: {score}/100.",
                    ],
                    metadata={
                        "source": source,
                        "countries": sorted(countries_seen),
                        "max_depth": max_chain_depth,
                        "chain_size": len(chain_accounts),
                    },
                )
            )

    if not results:
        results.append(
            GraphPatternResult(
                pattern_type="CROSS_BORDER_CHAIN",
                score=0.0,
                evidence=["No cross-border chains detected."],
            )
        )

    return results


def calculate_pagerank_centrality(
    graph: nx.MultiDiGraph,
    alpha: float = 0.85,
    top_n: int = 20,
) -> Dict[str, Any]:
    """Identify central hub accounts using PageRank.

    Parameters
    ----------
    graph : nx.MultiDiGraph
    alpha : float
        Damping factor.
    top_n : int
        Number of top-ranked accounts to return in detail.

    Returns
    -------
    dict
        Keys: ``pagerank`` (full dict), ``top_accounts`` (list of dicts
        with account_id, rank, score), ``max_rank``, ``mean_rank``.
    """
    if graph.number_of_nodes() == 0:
        return {
            "pagerank": {},
            "top_accounts": [],
            "max_rank": 0.0,
            "mean_rank": 0.0,
        }

    simple = nx.DiGraph(graph)
    pr = nx.pagerank(simple, alpha=alpha)

    sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)
    top = sorted_pr[:top_n]

    top_accounts = [
        {
            "account_id": acct,
            "pagerank": round(score, 6),
            "rank_position": i + 1,
        }
        for i, (acct, score) in enumerate(top)
    ]

    values = list(pr.values())

    return {
        "pagerank": {k: round(v, 6) for k, v in pr.items()},
        "top_accounts": top_accounts,
        "max_rank": round(max(values), 6) if values else 0.0,
        "mean_rank": round(float(np.mean(values)), 6) if values else 0.0,
    }


# --------------------------------------------------------------------------
# NetworkX implementation of the abstract interface
# --------------------------------------------------------------------------


class NetworkXGraphEngine(GraphDetectorInterface):
    """Concrete implementation of GraphDetectorInterface using NetworkX.

    Wraps all module-level functions with stateful graph management.
    """

    def __init__(self) -> None:
        self._graph: Optional[nx.MultiDiGraph] = None

    @property
    def graph(self) -> nx.MultiDiGraph:
        """Access the underlying graph, raising if not built."""
        if self._graph is None:
            raise RuntimeError("Graph not built. Call build_graph() first.")
        return self._graph

    def build_graph(
        self, transactions: Iterable[Dict[str, Any]]
    ) -> nx.MultiDiGraph:
        """Build and store the transaction graph."""
        self._graph = build_transaction_graph(transactions)
        return self._graph

    def fan_in(
        self, account_id: str, threshold: int = 4
    ) -> GraphPatternResult:
        return detect_fan_in(self.graph, account_id, threshold)

    def fan_out(
        self, account_id: str, threshold: int = 4
    ) -> GraphPatternResult:
        return detect_fan_out(self.graph, account_id, threshold)

    def multi_hop_chains(
        self, account_id: str, max_depth: int = 5
    ) -> GraphPatternResult:
        return detect_multi_hop_chains(self.graph, account_id, max_depth)

    def circular_flows(
        self, max_length: int = 6
    ) -> List[GraphPatternResult]:
        return detect_circular_flows(self.graph, max_length)

    def pass_through_accounts(self) -> List[GraphPatternResult]:
        return detect_pass_through_accounts(self.graph)

    def connected_clusters(
        self, min_size: int = 3
    ) -> List[GraphPatternResult]:
        return find_connected_clusters(self.graph, min_size)

    def split_and_merge(self) -> List[GraphPatternResult]:
        return detect_split_and_merge(self.graph)

    def cross_bank_chains(self) -> List[GraphPatternResult]:
        return detect_cross_bank_chains(self.graph)

    def cross_border_chains(self) -> List[GraphPatternResult]:
        return detect_cross_border_chains(self.graph)

    def pagerank_centrality(self) -> Dict[str, float]:
        return calculate_pagerank_centrality(self.graph)
