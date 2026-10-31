"""
IBM AML-Data Source Adapter.

Source: https://github.com/IBM/AML-Data
Characteristics:
- Multi-bank synthetic transactions modeling cross-institutional money laundering.
- Preserves original fields (From Bank, From Account, To Bank, To Account, Payment Format).
- Strictly isolates `Is Laundering` into protected evaluation vault.
"""

import os
import csv
from typing import Dict, Any, Generator, Optional
from datetime import datetime, timezone
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import store_protected_transaction_label

class IbmAmlAdapter:
    """Streams and transforms IBM AML-Data CSV partitions into canonical SentinelFlow format."""

    @staticmethod
    def parse_records(file_path: str, max_records: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"IBM AML-Data file not found at: {file_path}")

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for idx, row in enumerate(reader):
                if max_records and count >= max_records:
                    break

                # Extract original fields
                ts_str = row.get("Timestamp", "")
                from_bank = row.get("From Bank", "BANK_001")
                from_acc = row.get("From Account", "ACC_001")
                to_bank = row.get("To Bank", "BANK_002")
                to_acc = row.get("To Account", "ACC_002")
                amt_str = row.get("Amount Paid", row.get("Amount Received", "0.0"))
                curr_str = row.get("Payment Currency", row.get("Receiving Currency", "USD"))
                format_str = row.get("Payment Format", "WIRE")
                is_laundering = int(row.get("Is Laundering", "0") or 0)

                try:
                    amount = float(amt_str)
                except ValueError:
                    amount = 0.0

                iso_curr = CurrencyConversionService.normalize_currency_code(curr_str)
                txn_id = f"TXN-IBMAML-{idx:08d}"
                event_id = f"EVT-IBMAML-{from_bank}-{idx:08d}"
                src_acc = f"{from_bank}:{from_acc}"
                dest_acc = f"{to_bank}:{to_acc}"

                # Parse timestamp safely
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).isoformat()
                except Exception:
                    ts = datetime.now(timezone.utc).isoformat()

                # Store ground truth label in isolated protected store (no leak to detection)
                store_protected_transaction_label(
                    transaction_id=txn_id,
                    ground_truth_label=is_laundering,
                    dataset_name="IBM_AML",
                    scenario_id="IBM_SYNTHETIC_AML"
                )

                canonical_txn = {
                    "id": txn_id,
                    "event_id": event_id,
                    "source_account_id": src_acc,
                    "destination_account_id": dest_acc,
                    "customer_id": f"CUST-IBM-{from_acc[:8]}",
                    "amount": amount,
                    "currency": iso_curr,
                    "transaction_type": "TRANSFER",
                    "payment_channel": format_str,
                    "status": "COMPLETED",
                    "dataset_source": "IBM_AML",
                    "is_ground_truth_fraud": 0,  # Zeroed out in feature feed to guarantee zero leakage
                    "created_at": ts
                }

                yield canonical_txn
                count += 1
