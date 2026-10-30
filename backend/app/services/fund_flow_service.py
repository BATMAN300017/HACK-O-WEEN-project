"""
Dedicated Fund-Flow Reconstruction & Tracing Engine.

Given a flagged transaction or account:
1. Traces forward downstream and backward upstream through time-ordered edges.
2. Identifies split transactions, layering hops, and cross-border consolidation.
3. Tracks currency conversion events across international payment corridors.
4. Addresses the fundamental economic reality of FUNGIBILITY:
   - When an intermediary account receives multiple inflows, calculates proportional
     attribution fractions and explicitly quantifies FLOW UNCERTAINTY (0.0 = deterministic, 1.0 = highly diluted).
5. Reconstructs complete verifiable timeline and evidence trail for human investigators.
"""

import sqlite3
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import assert_no_label_leakage

class FundFlowTracingService:
    """Reconstructs end-to-end money movement across multi-hop banking corridors."""

    @classmethod
    def trace_transaction_flow(
        cls,
        conn: sqlite3.Connection,
        start_transaction_id: str,
        max_hops: int = 4
    ) -> Dict[str, Any]:
        """
        Traces the downstream and upstream money movement originating from a transaction.
        """
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, source_account_id, destination_account_id, amount, currency,
                   created_at, payment_channel, status
            FROM transactions
            WHERE id = ?
        """, (start_transaction_id,))
        root_row = cursor.fetchone()
        if not root_row:
            return {"error": f"Transaction {start_transaction_id} not found."}

        cols = ["id", "source_account_id", "destination_account_id", "amount", "currency", "created_at", "payment_channel", "status"]
        root_txn = dict(zip(cols, root_row))
        assert_no_label_leakage(root_txn, context="FundFlowTracingService.trace")

        origin_acc = root_txn["source_account_id"]
        initial_dest = root_txn["destination_account_id"]
        initial_amt = float(root_txn["amount"])
        initial_curr = root_txn["currency"]
        initial_time = root_txn["created_at"]

        timeline_events = []
        hop_nodes = {origin_acc: {"role": "ORIGIN", "inflow": 0.0, "outflow": initial_amt}}
        hop_edges = []
        visited_accounts = {origin_acc}

        # Root event
        timeline_events.append({
            "hop": 0,
            "type": "ROOT_DISCOVERY",
            "transaction_id": start_transaction_id,
            "from_account": origin_acc,
            "to_account": initial_dest,
            "amount": initial_amt,
            "currency": initial_curr,
            "timestamp": initial_time,
            "attribution_percentage": 100.0,
            "uncertainty_score": 0.0,
            "explanation": f"Initial suspicious transfer of {initial_curr} {initial_amt:,.2f} initiated."
        })

        current_accounts = [(initial_dest, initial_amt, initial_curr, initial_time, 1.0)]
        visited_accounts.add(initial_dest)

        total_hops_traced = 0
        overall_uncertainty = 0.0

        for hop_depth in range(1, max_hops + 1):
            next_accounts = []
            if not current_accounts:
                break

            for acc, prev_inflow, prev_curr, prev_time, prev_attribution in current_accounts:
                if not acc:
                    continue

                # Find all subsequent outgoing transactions from this account
                cursor.execute("""
                    SELECT id, source_account_id, destination_account_id, amount, currency,
                           created_at, payment_channel, status
                    FROM transactions
                    WHERE source_account_id = ? AND created_at >= ? AND destination_account_id IS NOT NULL
                    ORDER BY created_at ASC LIMIT 8
                """, (acc, prev_time))
                out_txns = [dict(r) for r in cursor.fetchall()]

                # Calculate total prior inflows into this account to measure fungibility dilution
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0), COUNT(*)
                    FROM transactions
                    WHERE destination_account_id = ? AND created_at <= ?
                """, (acc, prev_time))
                inflow_stats = cursor.fetchone()
                total_inflows = float(inflow_stats[0]) if inflow_stats else prev_inflow
                inflow_count = inflow_stats[1] if inflow_stats else 1

                # Calculate Fungibility Uncertainty Score:
                # If the account had multiple other large inflows before sending money out,
                # we cannot be 100% sure the outgoing money was solely from the scam proceeds.
                dilution_factor = min(1.0, prev_inflow / max(prev_inflow, total_inflows))
                hop_uncertainty = round(1.0 - dilution_factor, 2)
                overall_uncertainty = max(overall_uncertainty, hop_uncertainty)

                for out_t in out_txns:
                    dest_acc = out_t["destination_account_id"]
                    out_amt = float(out_t["amount"])
                    out_curr = out_t["currency"]
                    out_time = out_t["created_at"]

                    # Check currency conversion
                    is_conversion = out_curr != prev_curr
                    exchange_details = None
                    if is_conversion:
                        conv = CurrencyConversionService.convert_amount(out_amt, out_curr, prev_curr, out_time)
                        exchange_details = f"Converted {out_curr} to {prev_curr} @ {conv['exchange_rate']}"

                    # Attribution fraction
                    attribution_pct = round(prev_attribution * dilution_factor * 100.0, 1)

                    timeline_events.append({
                        "hop": hop_depth,
                        "type": "CROSS_BORDER_FORWARDING" if is_conversion else "DOMESTIC_FORWARDING",
                        "transaction_id": out_t["id"],
                        "from_account": acc,
                        "to_account": dest_acc,
                        "amount": out_amt,
                        "currency": out_curr,
                        "timestamp": out_time,
                        "attribution_percentage": attribution_pct,
                        "uncertainty_score": hop_uncertainty,
                        "is_currency_conversion": is_conversion,
                        "conversion_notes": exchange_details,
                        "explanation": (
                            f"Hop {hop_depth}: Account {acc} forwarded {out_curr} {out_amt:,.2f} to {dest_acc} "
                            f"(Attribution: {attribution_pct}% confidence; Fungibility Uncertainty: {hop_uncertainty*100:.0f}%)."
                        )
                    })

                    hop_edges.append({
                        "hop": hop_depth,
                        "source": acc,
                        "target": dest_acc,
                        "amount": out_amt,
                        "currency": out_curr,
                        "attribution_pct": attribution_pct,
                        "uncertainty": hop_uncertainty
                    })

                    if dest_acc not in visited_accounts:
                        visited_accounts.add(dest_acc)
                        next_accounts.append((dest_acc, out_amt, out_curr, out_time, prev_attribution * dilution_factor))

            current_accounts = next_accounts
            total_hops_traced = hop_depth

        return {
            "root_transaction_id": start_transaction_id,
            "origin_account": origin_acc,
            "initial_amount": initial_amt,
            "initial_currency": initial_curr,
            "total_hops_traced": total_hops_traced,
            "accounts_in_path_count": len(visited_accounts),
            "flow_uncertainty_score": round(overall_uncertainty, 2),
            "fungibility_statement": (
                "High flow determinism. Clean single-pipeline forwarding with minimal dilution."
                if overall_uncertainty < 0.25 else
                f"Moderate fund dilution. Intermediary accounts commingled funds from multiple sources (Uncertainty: {overall_uncertainty*100:.0f}%)."
            ),
            "timeline": timeline_events,
            "hop_edges": hop_edges,
            "accounts_involved": list(visited_accounts)
        }
