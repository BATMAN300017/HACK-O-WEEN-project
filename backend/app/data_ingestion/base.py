"""
Base classes and interfaces for dataset ingestion adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class IngestionBatchResult:
    dataset_name: str
    batch_index: int
    records_processed: int
    valid_records: int
    invalid_records: int
    labels_isolated: int
    duration_seconds: float
    checkpoint_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class NormalizedTransaction:
    id: str
    source_account_id: str
    destination_account_id: str
    amount: float
    currency: str
    created_at: str
    sender_bank: Optional[str] = None
    receiver_bank: Optional[str] = None
    sender_country: Optional[str] = "IND"
    receiver_country: Optional[str] = "IND"
    payment_channel: Optional[str] = "BANK_TRANSFER"
    payment_type: Optional[str] = "TRANSFER"
    converted_amount: Optional[float] = None
    converted_currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    exchange_rate_source: Optional[str] = None
    exchange_rate_timestamp: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    dataset_source: str = "UNKNOWN"
    batch_id: Optional[str] = None

class BaseDatasetAdapter(ABC):
    """Abstract base class for all dataset ingestion adapters."""

    def __init__(self, dataset_name: str, batch_size: int = 1000):
        self.dataset_name = dataset_name
        self.batch_size = batch_size

    @abstractmethod
    def inspect_schema(self, source_path: str) -> Dict[str, Any]:
        """Inspect column names, data types, and row count without loading full data into RAM."""
        pass

    @abstractmethod
    def load_batches(
        self,
        source_path: str,
        max_records: Optional[int] = None
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream dataset in chunked batches."""
        pass

    @abstractmethod
    def process_and_isolate(
        self,
        batch: List[Dict[str, Any]],
        batch_id: str
    ) -> IngestionBatchResult:
        """
        Process a batch:
        1. Strip all ground-truth labels and route them to Pipeline B (Protected Store).
        2. Normalize label-free records for Pipeline A (Detection Engine).
        """
        pass
