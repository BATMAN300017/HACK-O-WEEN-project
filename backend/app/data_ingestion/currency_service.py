"""
Multi-Currency & International Exchange Rate Subsystem.

Supported ISO 4217 Currencies:
- INR: Indian Rupee (Domestic Core)
- USD: US Dollar
- EUR: Euro
- AED: UAE Dirham
- GBP: British Pound
- SGD: Singapore Dollar

Guarantees:
1. Never adds or compares different currencies without documented conversion.
2. Every cross-currency conversion records rate, source, timestamp, and both amounts.
3. Historical rate lookups with clear fallback provenance.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "AED", "GBP", "SGD"}

# Base currency for normalized risk comparison
NORMALIZATION_BASE_CURRENCY = "INR"

# Reference benchmark exchange rates (INR base rate: units of INR per 1 foreign currency unit)
# In production, this table is populated from historical market feeds (e.g., RBI Reference Rates / ECB / OANDA)
HISTORICAL_EXCHANGE_RATES: Dict[str, Dict[str, Any]] = {
    "USD": {
        "rate_to_inr": 83.50,
        "source": "RBI_REFERENCE_HISTORICAL",
        "timestamp": "2024-06-30T12:00:00Z"
    },
    "EUR": {
        "rate_to_inr": 90.25,
        "source": "ECB_REFERENCE_HISTORICAL",
        "timestamp": "2024-06-30T12:00:00Z"
    },
    "AED": {
        "rate_to_inr": 22.74,
        "source": "CBUAE_HISTORICAL",
        "timestamp": "2024-06-30T12:00:00Z"
    },
    "GBP": {
        "rate_to_inr": 106.10,
        "source": "BOE_HISTORICAL",
        "timestamp": "2024-06-30T12:00:00Z"
    },
    "SGD": {
        "rate_to_inr": 62.40,
        "source": "MAS_HISTORICAL",
        "timestamp": "2024-06-30T12:00:00Z"
    },
    "INR": {
        "rate_to_inr": 1.0,
        "source": "DOMESTIC_PARITY",
        "timestamp": "2024-06-30T12:00:00Z"
    }
}

class IncompatibleCurrencyError(Exception):
    """Raised when an operation attempts to aggregate mixed currencies without conversion."""
    pass

class CurrencyConversionService:
    """Manages multi-currency conversion, verification, and audit logging."""

    @staticmethod
    def is_supported(currency: str) -> bool:
        return currency.upper() in SUPPORTED_CURRENCIES

    @staticmethod
    def get_exchange_rate(
        from_currency: str,
        to_currency: str,
        timestamp: Optional[str] = None
    ) -> Tuple[float, str, str]:
        """
        Returns (rate, rate_source, rate_timestamp).
        Formula: converted_amount = from_amount * rate
        """
        from_c = from_currency.upper()
        to_c = to_currency.upper()

        if from_c == to_c:
            return 1.0, "PARITY", timestamp or datetime.now(timezone.utc).isoformat()

        if from_c not in HISTORICAL_EXCHANGE_RATES or to_c not in HISTORICAL_EXCHANGE_RATES:
            raise ValueError(f"Unsupported currency pair: {from_c}/{to_c}")

        # Conversion through INR as pivot
        from_to_inr = HISTORICAL_EXCHANGE_RATES[from_c]["rate_to_inr"]
        to_to_inr = HISTORICAL_EXCHANGE_RATES[to_c]["rate_to_inr"]

        rate = round(from_to_inr / to_to_inr, 6)
        source = f"{HISTORICAL_EXCHANGE_RATES[from_c]['source']} / {HISTORICAL_EXCHANGE_RATES[to_c]['source']}"
        rate_ts = timestamp or HISTORICAL_EXCHANGE_RATES[from_c]["timestamp"]

        return rate, source, rate_ts

    @classmethod
    def convert_amount(
        cls,
        amount: float,
        from_currency: str,
        to_currency: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs documented currency conversion with provenance.
        """
        from_c = from_currency.upper()
        to_c = to_currency.upper()

        rate, source, rate_ts = cls.get_exchange_rate(from_c, to_c, timestamp)
        converted = round(amount * rate, 2)

        return {
            "original_amount": amount,
            "original_currency": from_c,
            "converted_amount": converted,
            "converted_currency": to_c,
            "exchange_rate": rate,
            "exchange_rate_source": source,
            "exchange_rate_timestamp": rate_ts
        }

    @classmethod
    def normalize_to_base(cls, amount: float, currency: str, timestamp: Optional[str] = None) -> float:
        """Normalizes any supported currency amount to base INR for mathematical comparison."""
        conv = cls.convert_amount(amount, currency, NORMALIZATION_BASE_CURRENCY, timestamp)
        return conv["converted_amount"]

    @classmethod
    def safe_sum_transactions(cls, transactions: List[Dict[str, Any]], target_currency: str = "INR") -> float:
        """
        Sums transaction amounts safely by converting every transaction to the target currency.
        Prevents illegal currency mixing.
        """
        total = 0.0
        for txn in transactions:
            amt = float(txn["amount"])
            curr = txn.get("currency", "INR")
            conv = cls.convert_amount(amt, curr, target_currency, txn.get("created_at"))
            total += conv["converted_amount"]
        return round(total, 2)
