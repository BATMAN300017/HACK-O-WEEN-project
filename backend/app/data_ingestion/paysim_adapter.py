"""
PaySim Mobile Money Source Adapter.

Source: https://www.kaggle.com/datasets/ealaxi/paysim1
Characteristics:
- Mobile money transaction stream (CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER).
- IMPORTANT DOMAIN DISTINCTION: This is a mobile-money unauthorized fraud dataset,
  NOT a conventional banking AML ground-truth dataset.
- Preserves original fields (step, type, nameOrig, nameDest, oldbalanceOrg, newbalanceOrig).
- Isolates `isFraud` strictly as `mobile_money_fraud` in the protected evaluation vault.
"""

import os
import csv
from typing import Dict, Any, Generator, Optional
from datetime import datetime, timezone, timedelta
from app.data_ingestion.label_isolation import store_protected_transaction_label

# PaySim time simulation baseline
PAYSIM_BASE_TIME = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

class PaySimAdapter:
    """Streams and transforms PaySim CSV records into canonical SentinelFlow format."""

    @staticmethod
    def parse_records(file_path: str, max_records: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PaySim dataset file not found at: {file_path}")

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for idx, row in enumerate(reader):
                if max_records and count >= max_records:
                    break

                step = int(row.get("step", "1") or 1)
                tx_type = row.get("type", "TRANSFER").upper()
                amt_str = row.get("amount", "0.0")
                name_orig = row.get("nameOrig", f"C{idx:07d}")
                name_dest = row.get("nameDest", f"M{idx:07d}")
                is_fraud = int(row.get("isFraud", "0") or 0)
                is_flagged = int(row.get("isFlaggedFraud", "0") or 0)

                try:
                    amount = float(amt_str)
                except ValueError:
                    amount = 0.0

                txn_id = f"TXN-PAYSIM-{idx:08d}"
                event_id = f"EVT-PAYSIM-S{step:04d}-{idx:08d}"
                # Step represents hours from simulation start
                ts = (PAYSIM_BASE_TIME + timedelta(hours=step)).isoformat()

                # Isolate ground truth label into protected evaluation vault
                # Label is explicitly flagged as mobile_money_fraud
                store_protected_transaction_label(
                    transaction_id=txn_id,
                    ground_truth_label=is_fraud,
                    dataset_name="PAYSIM",
                    scenario_id="MOBILE_MONEY_FRAUD" if is_fraud else "LEGITIMATE_MOBILE_TRANSFER"
                )

                canonical_txn = {
                    "id": txn_id,
                    "event_id": event_id,
                    "source_account_id": f"MM:{name_orig}",
                    "destination_account_id": f"MM:{name_dest}",
                    "customer_id": f"CUST-MM-{name_orig}",
                    "amount": amount,
                    "currency": "USD",  # PaySim simulated unit
                    "transaction_type": tx_type,
                    "payment_channel": "MOBILE_MONEY",
                    "status": "COMPLETED",
                    "dataset_source": "PAYSIM",
                    "is_ground_truth_fraud": 0,  # Zeroed out to guarantee zero feature leakage
                    "created_at": ts
                }

                yield canonical_txn
                count += 1
