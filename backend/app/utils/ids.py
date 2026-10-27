import uuid

def generate_id(prefix: str = "") -> str:
    short_uuid = uuid.uuid4().hex[:12]
    if prefix:
        return f"{prefix.upper()}-{short_uuid}"
    return short_uuid

def generate_transaction_id() -> str:
    return generate_id("TXN")

def generate_alert_id() -> str:
    return generate_id("ALT")

def generate_investigation_id() -> str:
    return generate_id("INV")

def generate_evidence_id() -> str:
    return generate_id("EVD")

def generate_customer_id() -> str:
    return generate_id("CUST")

def generate_account_id() -> str:
    return generate_id("ACT")

def generate_user_id() -> str:
    return generate_id("USR")

def generate_rule_id() -> str:
    return generate_id("RULE")
