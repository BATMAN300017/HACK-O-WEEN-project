"""
SentinelFlow AI Data Ingestion & Label Isolation Subsystem.
"""

from app.data_ingestion.base import BaseDatasetAdapter, IngestionBatchResult, NormalizedTransaction
from app.data_ingestion.label_isolation import (
    strip_labels_for_detection,
    store_protected_transaction_label,
    store_protected_account_label,
    store_protected_scenario_label,
    get_protected_evaluation_labels,
    assert_no_label_leakage,
    LabelLeakageError
)
from app.data_ingestion.currency_service import CurrencyConversionService, SUPPORTED_CURRENCIES
from app.data_ingestion.rbi_npci_statistics import CALIBRATED_INDIAN_PAYMENT_BENCHMARKS
from app.data_ingestion.india_simulator import IndiaBankingSimulator
from app.data_ingestion.saml_d_adapter import SamlDAdapter
from app.data_ingestion.nfpc_adapter import NfpcAdapter
from app.data_ingestion.schema_inspector import SchemaInspector
from app.data_ingestion.normalizer import TransactionNormalizer
from app.data_ingestion.validator import DataValidator
from app.data_ingestion.batch_loader import BatchLoader
from app.data_ingestion.provenance import ProvenanceTracker
from app.data_ingestion.dataset_registry import DatasetRegistry
