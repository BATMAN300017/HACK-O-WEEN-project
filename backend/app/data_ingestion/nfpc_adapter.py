"""
NFPC (National Fraud Prevention Council / Indian Banking Mule Dataset) Ingestion Adapter.

Source Reference:
- HuggingFace: https://huggingface.co/datasets/preetisheoran/nfpc-parquet-dataset

Dataset Characteristics:
- ~400 Million transactions across 5-year window (July 2020 – June 2025).
- ~159,000 customers, ~160,000 accounts.
- Parquet files partitioned across batches.
- Ground truth is primarily **ACCOUNT-LEVEL** (`mule_label`, `is_mule`).

CRITICAL MEMORY & ISOLATION CONSTRAINTS:
1. NEVER loads full 400M dataset into RAM.
2. Uses `pyarrow.parquet.ParquetFile.iter_batches()` for streaming chunk ingestion.
3. Isolates account-level mule labels into `protected_ground_truth.db`.
4. Emits strictly label-free transaction records for Pipeline A.
"""

import os
import uuid
from typing import Dict, Any, List, Optional, Generator, Tuple
from datetime import datetime, timezone
import pandas as pd

from app.data_ingestion.base import BaseDatasetAdapter, IngestionBatchResult
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import (
    strip_labels_for_detection,
    store_protected_account_label,
    assert_no_label_leakage
)
from app.core.logging import logger

NFPC_CANONICAL_COLUMNS = [
    "transaction_id",
    "account_number",
    "counterparty_account",
    "transaction_amount",
    "transaction_timestamp",
    "payment_mode",
    "bank_code",
    "mule_label"  # Ground-truth label (Account-level)
]

class NfpcAdapter(BaseDatasetAdapter):
    """Ingests NFPC Parquet batches incrementally while strictly isolating account mule labels."""

    def __init__(self, batch_size: int = 5000):
        super().__init__(dataset_name="NFPC_MULE", batch_size=batch_size)

    def inspect_schema(self, source_path: str) -> Dict[str, Any]:
        """Inspects Parquet metadata without loading records into memory."""
        if not os.path.exists(source_path):
            return {
                "dataset": self.dataset_name,
                "status": "NOT_FOUND",
                "canonical_columns": NFPC_CANONICAL_COLUMNS,
                "label_granularity": "ACCOUNT_LEVEL",
                "security_status": "PROTECTED_ISOLATION_ACTIVE"
            }

        import pyarrow.parquet as pq
        parquet_file = pq.ParquetFile(source_path)
        schema = parquet_file.schema.names
        num_rows = parquet_file.metadata.num_rows

        label_cols = [c for c in schema if "mule" in c.lower() or "label" in c.lower() or "fraud" in c.lower()]

        return {
            "dataset": self.dataset_name,
            "source_path": source_path,
            "columns_found": schema,
            "total_records_in_parquet": num_rows,
            "num_row_groups": parquet_file.num_row_groups,
            "label_fields_detected": label_cols,
            "label_granularity": "ACCOUNT_LEVEL",
            "security_status": "READY_FOR_ISOLATED_STREAMING"
        }

    def load_batches(
        self,
        source_path: str,
        max_records: Optional[int] = None
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Streams Parquet batches via PyArrow iter_batches to maintain a constant tiny memory footprint."""
        if not os.path.exists(source_path):
            logger.warning(f"NFPC file not found at {source_path}. Generating verified benchmark sample batch.")
            yield self.generate_verification_sample(count=max_records or 200)
            return

        import pyarrow.parquet as pq
        parquet_file = pq.ParquetFile(source_path)
        batch = []
        count = 0

        for record_batch in parquet_file.iter_batches(batch_size=self.batch_size):
            df_chunk = record_batch.to_pandas()
            for _, row in df_chunk.iterrows():
                batch.append(row.to_dict())
                count += 1
                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []
                if max_records and count >= max_records:
                    break
            if max_records and count >= max_records:
                break

        if batch:
            yield batch

    def process_and_isolate(
        self,
        batch: List[Dict[str, Any]],
        batch_id: str
    ) -> Tuple[List[Dict[str, Any]], IngestionBatchResult]:
        """
        Processes an NFPC batch:
        1. Strips `mule_label` / `is_mule`.
        2. Routes account-level labels to the protected store.
        3. Returns clean transactions for Pipeline A.
        """
        start_t = datetime.now()
        normalized_txns: List[Dict[str, Any]] = []
        labels_isolated = 0
        valid = 0
        invalid = 0
        errors = []

        seen_accounts = set()

        for row in batch:
            try:
                # 1. Strict Label Splitting
                det_row, prot_labels = strip_labels_for_detection(row)

                # 2. Extract Canonical Fields
                src_acc = str(det_row.get("account_number") or det_row.get("source_account_id") or det_row.get("Sender_account"))
                dest_acc = str(det_row.get("counterparty_account") or det_row.get("destination_account_id") or det_row.get("Receiver_account"))
                amt = float(det_row.get("transaction_amount") or det_row.get("amount", 0.0))
                date_val = str(det_row.get("transaction_timestamp") or det_row.get("created_at") or datetime.now(timezone.utc).isoformat())
                channel = str(det_row.get("payment_mode") or det_row.get("payment_channel", "IMPS")).upper()
                bank_code = str(det_row.get("bank_code") or "INDIAN_BANK")

                txn_id = f"NFPC-{uuid.uuid4().hex[:12]}"

                norm_record = {
                    "id": txn_id,
                    "event_id": f"EVT-{txn_id}",
                    "source_account_id": src_acc,
                    "destination_account_id": dest_acc,
                    "amount": amt,
                    "currency": "INR",  # NFPC is domestic Indian banking
                    "created_at": date_val,
                    "sender_bank": bank_code,
                    "receiver_bank": "COUNTERPARTY_BANK",
                    "sender_country": "IND",
                    "receiver_country": "IND",
                    "payment_channel": channel,
                    "payment_type": "TRANSFER",
                    "converted_amount": amt,
                    "converted_currency": "INR",
                    "exchange_rate": 1.0,
                    "exchange_rate_source": "DOMESTIC_PARITY",
                    "exchange_rate_timestamp": date_val,
                    "dataset_source": "NFPC_MULE",
                    "batch_id": batch_id,
                    "status": "COMPLETED"
                }

                assert_no_label_leakage(norm_record, context="NfpcAdapter.process")
                normalized_txns.append(norm_record)
                valid += 1

                # 3. Route Account-Level Mule Labels to Pipeline B Store
                is_mule = None
                for k in ["mule_label", "is_mule", "label"]:
                    if k in prot_labels:
                        try:
                            is_mule = int(prot_labels[k])
                        except Exception:
                            is_mule = 1 if str(prot_labels[k]).lower() in ("true", "1", "mule") else 0
                        break

                if is_mule is not None and src_acc not in seen_accounts:
                    seen_accounts.add(src_acc)
                    store_protected_account_label(
                        account_id=src_acc,
                        dataset_name="NFPC_MULE",
                        is_mule=is_mule,
                        mule_role="MULE_SUSPECT" if is_mule == 1 else "LEGITIMATE",
                        raw_labels=prot_labels,
                        timestamp=date_val
                    )
                    labels_isolated += 1

            except Exception as e:
                invalid += 1
                errors.append(str(e))

        duration = (datetime.now() - start_t).total_seconds()
        res = IngestionBatchResult(
            dataset_name=self.dataset_name,
            batch_index=0,
            records_processed=len(batch),
            valid_records=valid,
            invalid_records=invalid,
            labels_isolated=labels_isolated,
            duration_seconds=duration,
            checkpoint_id=batch_id,
            errors=errors[:5]
        )
        return normalized_txns, res

    def generate_verification_sample(self, count: int = 200) -> List[Dict[str, Any]]:
        """Generates a sample conforming 1:1 to NFPC Indian banking schema."""
        import random
        rng = random.Random(202)
        sample = []
        modes = ["UPI", "IMPS", "NEFT", "RTGS", "ATM"]
        banks = ["SBI", "HDFC", "ICICI", "AXIS", "PNB", "BOB"]

        now = datetime.now(timezone.utc)
        for i in range(count):
            src_acc = f"NFPC_ACC_{rng.randint(1000, 1200)}"
            # Ground truth: Account-level mule flag
            is_mule = 1 if (hash(src_acc) % 10 == 0) else 0

            sample.append({
                "transaction_id": f"TXN-NFPC-{rng.randint(100000, 999999)}",
                "account_number": src_acc,
                "counterparty_account": f"NFPC_ACC_{rng.randint(2000, 2200)}",
                "transaction_amount": round(rng.uniform(100.0, 150000.0), 2),
                "transaction_timestamp": (now - pd.Timedelta(minutes=i*15)).isoformat(),
                "payment_mode": rng.choice(modes),
                "bank_code": rng.choice(banks),
                "mule_label": is_mule
            })
        return sample
