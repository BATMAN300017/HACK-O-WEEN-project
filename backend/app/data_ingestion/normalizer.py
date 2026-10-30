"""
Transaction and Entity Schema Normalizer.

Standardizes disparate schemas (SAML-D, NFPC, Simulator) into the canonical
SentinelFlow data contract for graph modeling and unsupervised detection.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.data_ingestion.currency_service import CurrencyConversionService
from app.data_ingestion.label_isolation import assert_no_label_leakage

# Standard ISO country code mapping
COUNTRY_NORMALIZE = {
    "INDIA": "IND", "IND": "IND", "IN": "IND",
    "UNITED STATES": "USA", "USA": "USA", "US": "USA",
    "UNITED ARAB EMIRATES": "ARE", "ARE": "ARE", "UAE": "ARE",
    "UNITED KINGDOM": "GBR", "GBR": "GBR", "UK": "GBR",
    "SINGAPORE": "SGP", "SGP": "SGP", "SG": "SGP",
    "GERMANY": "DEU", "DEU": "DEU", "DE": "DEU"
}

class TransactionNormalizer:
    """Normalizes raw heterogeneous records into canonical detection format."""

    @staticmethod
    def normalize_country(country_str: Optional[str]) -> str:
        if not country_str:
            return "IND"
        clean = country_str.strip().upper()
        return COUNTRY_NORMALIZE.get(clean, clean[:3])

    @classmethod
    def normalize_transaction(cls, raw: Dict[str, Any], dataset_name: str) -> Dict[str, Any]:
        """Converts raw record into canonical detection-safe transaction record."""
        # Ensure zero label leakage
        assert_no_label_leakage(raw, context=f"Normalizer ({dataset_name})")

        txn_id = raw.get("id") or raw.get("transaction_id") or f"TXN-{uuid.uuid4().hex[:10]}"
        src = raw.get("source_account_id") or raw.get("Sender_account") or raw.get("account_number")
        dest = raw.get("destination_account_id") or raw.get("Receiver_account") or raw.get("counterparty_account")
        amt = float(raw.get("amount") or raw.get("Amount") or raw.get("transaction_amount", 0.0))
        currency = (raw.get("currency") or raw.get("Payment_currency") or "INR").strip().upper()
        ts = raw.get("created_at") or raw.get("Date") or raw.get("transaction_timestamp") or datetime.now(timezone.utc).isoformat()

        src_country = cls.normalize_country(raw.get("sender_country") or raw.get("Sender_bank_location"))
        dest_country = cls.normalize_country(raw.get("receiver_country") or raw.get("Receiver_bank_location") or src_country)

        # Handle currency conversion
        conv = CurrencyConversionService.convert_amount(amt, currency, "INR", ts)

        norm = {
            "id": str(txn_id),
            "event_id": f"EVT-{txn_id}",
            "source_account_id": str(src),
            "destination_account_id": str(dest) if dest else None,
            "amount": amt,
            "currency": currency,
            "created_at": str(ts),
            "sender_bank": raw.get("sender_bank") or "BANK_A",
            "receiver_bank": raw.get("receiver_bank") or "BANK_B",
            "sender_country": src_country,
            "receiver_country": dest_country,
            "payment_channel": (raw.get("payment_channel") or raw.get("payment_mode") or raw.get("Payment_type") or "TRANSFER").upper(),
            "payment_type": raw.get("payment_type") or "TRANSFER",
            "converted_amount": conv["converted_amount"],
            "converted_currency": conv["converted_currency"],
            "exchange_rate": conv["exchange_rate"],
            "exchange_rate_source": conv["exchange_rate_source"],
            "exchange_rate_timestamp": conv["exchange_rate_timestamp"],
            "device_id": raw.get("device_id"),
            "ip_address": raw.get("ip_address"),
            "dataset_source": dataset_name,
            "status": raw.get("status", "COMPLETED")
        }

        assert_no_label_leakage(norm, context="Normalizer Output")
        return norm
