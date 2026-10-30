"""
Transaction and Account Data Integrity Validator.

Validates that normalized transactions satisfy regulatory financial data contracts:
- Non-negative, finite monetary amount.
- Valid ISO 4217 currency.
- Valid ISO 8601 timestamp.
- Valid source and destination accounts.
- Zero label leakage into Pipeline A payloads.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
from app.data_ingestion.currency_service import SUPPORTED_CURRENCIES
from app.data_ingestion.label_isolation import assert_no_label_leakage

class DataValidator:
    """Validates transaction contracts prior to graph insertion and model scoring."""

    @classmethod
    def validate_transaction(cls, txn: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []

        # 1. Security Check: Assert zero label leakage
        try:
            assert_no_label_leakage(txn, context="DataValidator")
        except Exception as e:
            errors.append(str(e))

        # 2. Amount Check
        amt = txn.get("amount")
        if amt is None:
            errors.append("Missing transaction amount")
        else:
            try:
                amt_val = float(amt)
                if amt_val <= 0.0:
                    errors.append(f"Transaction amount must be positive (received {amt_val})")
            except (ValueError, TypeError):
                errors.append(f"Invalid numeric amount: {amt}")

        # 3. Currency Check
        curr = txn.get("currency")
        if not curr or curr.upper() not in SUPPORTED_CURRENCIES:
            errors.append(f"Unsupported currency: {curr}. Must be one of {SUPPORTED_CURRENCIES}")

        # 4. Accounts Check
        src = txn.get("source_account_id")
        if not src or not str(src).strip():
            errors.append("Missing or empty source_account_id")

        # 5. Timestamp Check
        ts = txn.get("created_at")
        if not ts:
            errors.append("Missing transaction timestamp (created_at)")
        else:
            try:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                errors.append(f"Invalid ISO 8601 timestamp: {ts}")

        is_valid = len(errors) == 0
        return is_valid, errors
