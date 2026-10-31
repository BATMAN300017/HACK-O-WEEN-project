"""
Elliptic Bitcoin Dataset Source Adapter.

Source: https://www.kaggle.com/datasets/ellipticco/elliptic-data-set
Characteristics:
- Cryptocurrency graph dataset of 203,769 Bitcoin transaction nodes and directed transfer edges.
- Classes:
  - '1': Illicit (ransomware, darknet markets, scams)
  - '2': Licit (exchanges, mining pools, legal services)
  - 'unknown': Unlabeled transactions
- IMPORTANT DOMAIN DISTINCTION: This is a cryptocurrency on-chain forensics graph dataset,
  NOT a conventional banking AML ground-truth dataset.
- Preserves original cryptographic transaction IDs (`txId`) and directed input-output graph edges.
- Isolates on-chain entity classification strictly into the protected evaluation vault.
"""

import os
import csv
from typing import Dict, Any, Generator, Optional, List
from datetime import datetime, timezone, timedelta
from app.data_ingestion.label_isolation import store_protected_transaction_label

ELLIPTIC_BASE_TIME = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

class EllipticAdapter:
    """Streams and parses Elliptic Bitcoin graph records into canonical SentinelFlow format."""

    @staticmethod
    def parse_records(
        classes_file_path: str,
        edgelist_file_path: Optional[str] = None,
        max_records: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        if not os.path.exists(classes_file_path):
            raise FileNotFoundError(f"Elliptic classes file not found at: {classes_file_path}")

        # Optional edge lookup
        dest_map: Dict[str, str] = {}
        if edgelist_file_path and os.path.exists(edgelist_file_path):
            with open(edgelist_file_path, mode="r", encoding="utf-8") as f_edge:
                reader_edge = csv.reader(f_edge)
                next(reader_edge, None)  # header txId1, txId2
                for row_e in reader_edge:
                    if len(row_e) >= 2 and row_e[0] not in dest_map:
                        dest_map[row_e[0]] = row_e[1]

        with open(classes_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for idx, row in enumerate(reader):
                if max_records and count >= max_records:
                    break

                tx_id = row.get("txId", f"BTC_TX_{idx:08d}")
                raw_class = str(row.get("class", "unknown")).strip()

                # Map class: '1' is illicit, '2' is licit, 'unknown' is unlabelled
                if raw_class == "1":
                    ground_truth = 1
                    scenario_tag = "CRYPTO_ILLICIT_ONCHAIN"
                elif raw_class == "2":
                    ground_truth = 0
                    scenario_tag = "CRYPTO_LICIT_EXCHANGE"
                else:
                    ground_truth = -1  # Unknown / unlabelled
                    scenario_tag = "CRYPTO_UNKNOWN"

                dest_tx = dest_map.get(tx_id, f"BTC_OUT_{tx_id[:8]}")
                canonical_id = f"TXN-ELLIPTIC-{tx_id}"
                event_id = f"EVT-BTC-{tx_id}"

                # 49 timesteps of 2 weeks each in Elliptic
                ts = (ELLIPTIC_BASE_TIME + timedelta(days=idx % 700)).isoformat()

                # Store ground truth label in isolated evaluation vault if known
                if ground_truth != -1:
                    store_protected_transaction_label(
                        transaction_id=canonical_id,
                        ground_truth_label=ground_truth,
                        dataset_name="ELLIPTIC",
                        scenario_id=scenario_tag
                    )

                canonical_txn = {
                    "id": canonical_id,
                    "event_id": event_id,
                    "source_account_id": f"BTC:{tx_id}",
                    "destination_account_id": f"BTC:{dest_tx}",
                    "customer_id": f"CUST-BTC-{tx_id[:8]}",
                    "amount": 1.0,  # BTC normalized unit
                    "currency": "BTC",
                    "transaction_type": "CRYPTO_TRANSFER",
                    "payment_channel": "BITCOIN_NETWORK",
                    "status": "COMPLETED",
                    "dataset_source": "ELLIPTIC",
                    "is_ground_truth_fraud": 0,  # Zeroed out in feature feed
                    "created_at": ts
                }

                yield canonical_txn
                count += 1
