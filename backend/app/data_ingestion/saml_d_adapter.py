"""
SAML-D (Synthetic Transaction Monitoring Dataset for AML) Ingestion Adapter.

Source Reference:
- Kaggle: https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml/data
- HuggingFace AMLGraphX: https://huggingface.co/datasets/LordNR/AMLGraphX-SAML-D

Dataset Characteristics:
- Schema fields:
  `Sender_account`, `Receiver_account`, `Amount`, `Payment_currency`, `Received_currency`,
  `Sender_bank_location`, `Receiver_bank_location`, `Payment_type`, `Is_laundering`, `Laundering_type`, `Date`
- 18 geographic locations, 13 currencies, 28 typologies.

CRITICAL SECURITY CONSTRAINT:
- `Is_laundering` and `Laundering_type` MUST BE STRIPPED during ingestion.
- They are routed directly to the protected evaluation store (`protected_ground_truth.db`).
- Pipeline A (Detection) receives ONLY normalized, label-free records.
- Chronological train/test split: Earlier records used for unsupervised baseline; later for blind testing.
"""

import os
import csv
import uuid
from typing import Dict, Any, List, Optional, Generator, Tuple
from datetime import datetime, timezone
import pandas as pd

from app.data_ingestion.base import BaseDatasetAdapter, IngestionBatchResult
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import (
    strip_labels_for_detection,
    store_protected_transaction_label,
    assert_no_label_leakage
)
from app.core.logging import logger

SAML_D_CANONICAL_COLUMNS = [
    "Sender_account",
    "Receiver_account",
    "Amount",
    "Payment_currency",
    "Received_currency",
    "Sender_bank_location",
    "Receiver_bank_location",
    "Payment_type",
    "Is_laundering",
    "Laundering_type",
    "Date"
]

class SamlDAdapter(BaseDatasetAdapter):
    """Ingests, normalizes, and isolates ground truth for the SAML-D dataset."""

    def __init__(self, batch_size: int = 5000):
        super().__init__(dataset_name="SAML_D", batch_size=batch_size)

    def inspect_schema(self, source_path: str) -> Dict[str, Any]:
        """Inspects CSV / Parquet header and estimated record count without full RAM load."""
        if not os.path.exists(source_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            real_fallback = os.path.join(base_dir, "data", "saml_d", "saml_d_real.csv")
            if os.path.exists(real_fallback):
                source_path = real_fallback
            else:
                return {
                    "dataset": self.dataset_name,
                    "status": "NOT_FOUND",
                    "canonical_columns": SAML_D_CANONICAL_COLUMNS,
                    "label_fields_detected": ["Is_laundering", "Laundering_type"],
                    "security_status": "PROTECTED_ISOLATION_ACTIVE"
                }

        if source_path.endswith(".parquet"):
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(source_path)
            schema = parquet_file.schema.names
            num_rows = parquet_file.metadata.num_rows
        else:
            with open(source_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                schema = next(reader)
            # Estimate line count quickly
            num_rows = sum(1 for _ in open(source_path, "r", encoding="utf-8")) - 1

        label_cols = [c for c in schema if c.lower() in ("is_laundering", "laundering_type")]
        return {
            "dataset": self.dataset_name,
            "source_path": source_path,
            "columns_found": schema,
            "total_records_estimated": num_rows,
            "label_fields_detected": label_cols,
            "security_status": "READY_FOR_ISOLATED_INGESTION"
        }

    def load_batches(
        self,
        source_path: str,
        max_records: Optional[int] = None
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Streams records in chunked batches from disk."""
        if not os.path.exists(source_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            real_fallback = os.path.join(base_dir, "data", "saml_d", "saml_d_real.csv")
            if os.path.exists(real_fallback):
                source_path = real_fallback
            else:
                logger.warning(f"SAML-D file not found at {source_path}. Generating verified benchmark sample batch.")
                yield self.generate_verification_sample(count=max_records or 200)
                return

        if source_path.endswith(".parquet"):
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
        else:
            # Stream CSV via pandas chunksize
            count = 0
            for chunk in pd.read_csv(source_path, chunksize=self.batch_size):
                batch = chunk.to_dict(orient="records")
                if max_records:
                    if count + len(batch) > max_records:
                        batch = batch[:max_records - count]
                        count += len(batch)
                        yield batch
                        break
                count += len(batch)
                yield batch

    def process_and_isolate(
        self,
        batch: List[Dict[str, Any]],
        batch_id: str
    ) -> Tuple[List[Dict[str, Any]], IngestionBatchResult]:
        """
        Processes a raw SAML-D batch:
        1. Strips `Is_laundering` and `Laundering_type`.
        2. Routes labels to protected storage.
        3. Normalizes currencies and countries.
        4. Returns clean records for Pipeline A.
        """
        start_t = datetime.now()
        normalized_txns: List[Dict[str, Any]] = []
        labels_isolated = 0
        valid = 0
        invalid = 0
        errors = []

        for row in batch:
            try:
                # 1. Strict Label Splitting
                det_row, prot_labels = strip_labels_for_detection(row)

                # 2. Extract Canonical Fields
                src_acc = str(det_row.get("Sender_account") or det_row.get("source_account_id"))
                dest_acc = str(det_row.get("Receiver_account") or det_row.get("destination_account_id"))
                amt = float(det_row.get("Amount") or det_row.get("amount", 0.0))
                
                raw_pay_curr = str(det_row.get("Payment_currency") or det_row.get("currency", "USD"))
                raw_rcv_curr = str(det_row.get("Received_currency") or raw_pay_curr)
                pay_curr = CurrencyConversionService.normalize_currency_code(raw_pay_curr)
                rcv_curr = CurrencyConversionService.normalize_currency_code(raw_rcv_curr)

                src_country = str(det_row.get("Sender_bank_location") or det_row.get("sender_country", "USA"))
                dest_country = str(det_row.get("Receiver_bank_location") or det_row.get("receiver_country", src_country))
                pay_type = str(det_row.get("Payment_type") or det_row.get("payment_type", "TRANSFER"))
                
                # Timestamp parsing with optional Time field
                d_val = str(det_row.get("Date") or det_row.get("created_at") or "").strip()
                t_val = str(det_row.get("Time") or "").strip()
                if d_val and t_val:
                    date_val = f"{d_val}T{t_val}Z" if "T" not in d_val else d_val
                elif d_val:
                    date_val = d_val if "T" in d_val else f"{d_val}T00:00:00Z"
                else:
                    date_val = datetime.now(timezone.utc).isoformat()

                txn_id = f"SAML-{uuid.uuid4().hex[:12]}"

                # 3. Currency Conversion Handling
                conv_info = CurrencyConversionService.convert_amount(
                    amount=amt,
                    from_currency=pay_curr,
                    to_currency=rcv_curr,
                    timestamp=date_val
                )

                norm_record = {
                    "id": txn_id,
                    "event_id": f"EVT-{txn_id}",
                    "source_account_id": src_acc,
                    "destination_account_id": dest_acc,
                    "amount": amt,
                    "currency": pay_curr,
                    "created_at": date_val,
                    "sender_bank": "SAML_SOURCE_BANK",
                    "receiver_bank": "SAML_DEST_BANK",
                    "sender_country": src_country,
                    "receiver_country": dest_country,
                    "payment_channel": pay_type,
                    "payment_type": pay_type,
                    "converted_amount": conv_info["converted_amount"],
                    "converted_currency": conv_info["converted_currency"],
                    "exchange_rate": conv_info["exchange_rate"],
                    "exchange_rate_source": conv_info["exchange_rate_source"],
                    "exchange_rate_timestamp": conv_info["exchange_rate_timestamp"],
                    "dataset_source": "SAML_D",
                    "batch_id": batch_id,
                    "status": "COMPLETED"
                }

                # Verify clean detection record
                assert_no_label_leakage(norm_record, context="SamlDAdapter.process")
                normalized_txns.append(norm_record)
                valid += 1

                # 4. Route Protected Labels to Pipeline B Store
                is_laundering = None
                for k in ["Is_laundering", "is_laundering", "is_fraud"]:
                    if k in prot_labels:
                        try:
                            is_laundering = int(prot_labels[k])
                        except Exception:
                            is_laundering = 1 if str(prot_labels[k]).lower() in ("true", "1") else 0
                        break

                laundering_type = prot_labels.get("Laundering_type") or prot_labels.get("laundering_type")

                if is_laundering is not None or laundering_type is not None:
                    store_protected_transaction_label(
                        transaction_id=txn_id,
                        dataset_name="SAML_D",
                        is_laundering=is_laundering,
                        laundering_type=laundering_type,
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
        """
        Generates a validated synthetic benchmark batch conforming 1:1
        to the official SAML-D schema for unit testing and offline evaluation.
        """
        import random
        rng = random.Random(101)
        sample = []
        currencies = ["USD", "EUR", "AED", "GBP", "INR", "SGD"]
        countries = ["USA", "GBR", "ARE", "DEU", "IND", "SGP"]
        typologies = [
            "Fan-Out", "Fan-In", "Cycle", "Gather-Scatter", "Scatter-Gather",
            "Bipartite", "Stack", "Forwarding", "Legitimate-Normal"
        ]

        now = datetime.now(timezone.utc)
        for i in range(count):
            is_laund = 1 if rng.random() < 0.15 else 0
            typology = rng.choice(typologies[:-1]) if is_laund else "Legitimate-Normal"
            curr = rng.choice(currencies)
            rcv_curr = curr if rng.random() > 0.3 else rng.choice(currencies)

            sample.append({
                "Sender_account": f"SAML_ACC_{rng.randint(1000, 1500)}",
                "Receiver_account": f"SAML_ACC_{rng.randint(2000, 2500)}",
                "Amount": round(rng.uniform(50.0, 75000.0), 2),
                "Payment_currency": curr,
                "Received_currency": rcv_curr,
                "Sender_bank_location": rng.choice(countries),
                "Receiver_bank_location": rng.choice(countries),
                "Payment_type": rng.choice(["WIRE", "CREDIT", "ACH", "CHEQUE"]),
                "Is_laundering": is_laund,
                "Laundering_type": typology,
                "Date": (now - pd.Timedelta(hours=i*2)).isoformat()
            })
        return sample
