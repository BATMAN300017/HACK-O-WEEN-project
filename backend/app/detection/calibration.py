def assign_triage_band(score: float) -> str:
    if score >= 75.0:
        return "HIGH"
    elif score >= 50.0:
        return "ELEVATED"
    elif score >= 25.0:
        return "LOW"
    return "ROUTINE"

def assign_alert_severity(score: float) -> str:
    if score >= 85.0:
        return "CRITICAL"
    elif score >= 70.0:
        return "HIGH"
    elif score >= 45.0:
        return "MEDIUM"
    return "LOW"
