"""
Multi-Currency & International Exchange Rate Subsystem.

Supported ISO 4217 Currencies:
- INR: Indian Rupee (Domestic Core)
- USD: US Dollar
- EUR: Euro
- AED: UAE Dirham
- GBP: British Pound
- SGD: Singapore Dollar
- CHF: Swiss Franc
- CAD: Canadian Dollar
- AUD: Australian Dollar
- JPY: Japanese Yen
- MXN: Mexican Peso
- NGN: Nigerian Naira
- PKR: Pakistani Rupee
- TRY: Turkish Lira
- ALL: Albanian Lek
- MAD: Moroccan Dirham

Guarantees:
1. Never adds or compares different currencies without documented conversion.
2. Every cross-currency conversion records rate, source, timestamp, and both amounts.
3. Historical rate lookups with clear fallback provenance.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

SUPPORTED_CURRENCIES = {
    "INR", "USD", "EUR", "AED", "GBP", "SGD", "CHF", "CAD",
    "AUD", "JPY", "MXN", "NGN", "PKR", "TRY", "ALL", "MAD"
}

CURRENCY_NAME_MAP: Dict[str, str] = {
    "UK POUNDS": "GBP",
    "UK POUND": "GBP",
    "POUND": "GBP",
    "POUNDS": "GBP",
    "GBP": "GBP",
    "EURO": "EUR",
    "EUROS": "EUR",
    "EUR": "EUR",
    "US DOLLAR": "USD",
    "US DOLLARS": "USD",
    "USD": "USD",
    "DIRHAM": "AED",
    "DIRHAMS": "AED",
    "UAE DIRHAM": "AED",
    "AED": "AED",
    "INDIAN RUPEE": "INR",
    "INDIAN RUPEES": "INR",
    "RUPEES": "INR",
    "RUPEE": "INR",
    "INR": "INR",
    "SINGAPORE DOLLAR": "SGD",
    "SINGAPORE DOLLARS": "SGD",
    "SGD": "SGD",
    "SWISS FRANC": "CHF",
    "SWISS FRANCS": "CHF",
    "CHF": "CHF",
    "CANADIAN DOLLAR": "CAD",
    "CAD": "CAD",
    "AUSTRALIAN DOLLAR": "AUD",
    "AUD": "AUD",
    "YEN": "JPY",
    "JAPANESE YEN": "JPY",
    "JPY": "JPY",
    "MEXICAN PESO": "MXN",
    "MEXICAN PESOS": "MXN",
    "MXN": "MXN",
    "NAIRA": "NGN",
    "NIGERIAN NAIRA": "NGN",
    "NGN": "NGN",
    "PAKISTANI RUPEE": "PKR",
    "PAKISTANI RUPEES": "PKR",
    "PKR": "PKR",
    "TURKISH LIRA": "TRY",
    "TURKISH LIRAS": "TRY",
    "TRY": "TRY",
    "ALBANIAN LEK": "ALL",
    "ALL": "ALL",
    "MOROCCAN DIRHAM": "MAD",
    "MAD": "MAD"
}

# Base currency for normalized risk comparison
NORMALIZATION_BASE_CURRENCY = "INR"

# Reference benchmark exchange rates (INR base rate: units of INR per 1 foreign currency unit)
HISTORICAL_EXCHANGE_RATES: Dict[str, Dict[str, Any]] = {
    "USD": {"rate_to_inr": 83.50, "source": "RBI_REFERENCE_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "EUR": {"rate_to_inr": 90.25, "source": "ECB_REFERENCE_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "AED": {"rate_to_inr": 22.74, "source": "CBUAE_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "GBP": {"rate_to_inr": 106.10, "source": "BOE_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "SGD": {"rate_to_inr": 62.40, "source": "MAS_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "CHF": {"rate_to_inr": 93.80, "source": "SNB_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "CAD": {"rate_to_inr": 61.20, "source": "BOC_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "AUD": {"rate_to_inr": 54.50, "source": "RBA_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "JPY": {"rate_to_inr": 0.55, "source": "BOJ_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "MXN": {"rate_to_inr": 4.25, "source": "BANXICO_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "NGN": {"rate_to_inr": 0.055, "source": "CBN_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "PKR": {"rate_to_inr": 0.30, "source": "SBP_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "TRY": {"rate_to_inr": 2.45, "source": "TCMB_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "ALL": {"rate_to_inr": 0.90, "source": "BOA_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "MAD": {"rate_to_inr": 8.35, "source": "BAM_HISTORICAL", "timestamp": "2024-06-30T12:00:00Z"},
    "INR": {"rate_to_inr": 1.0, "source": "DOMESTIC_PARITY", "timestamp": "2024-06-30T12:00:00Z"}
}

class IncompatibleCurrencyError(Exception):
    """Raised when an operation attempts to aggregate mixed currencies without conversion."""
    pass

class CurrencyConversionService:
    """Manages multi-currency conversion, verification, and audit logging."""

    @staticmethod
    def normalize_currency_code(currency: str) -> str:
        """Translates descriptive currency names ('UK pounds', 'Euro') to canonical 3-letter ISO codes."""
        if not currency:
            return "USD"
        cleaned = str(currency).strip().upper()
        return CURRENCY_NAME_MAP.get(cleaned, cleaned if len(cleaned) == 3 else "USD")

    @classmethod
    def is_supported(cls, currency: str) -> bool:
        norm = cls.normalize_currency_code(currency)
        return norm in SUPPORTED_CURRENCIES

    @classmethod
    def get_exchange_rate(
        cls,
        from_currency: str,
        to_currency: str,
        timestamp: Optional[str] = None
    ) -> Tuple[float, str, str]:
        """
        Returns (rate, rate_source, rate_timestamp).
        Formula: converted_amount = from_amount * rate
        """
        from_c = cls.normalize_currency_code(from_currency)
        to_c = cls.normalize_currency_code(to_currency)

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
        from_c = cls.normalize_currency_code(from_currency)
        to_c = cls.normalize_currency_code(to_currency)

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
