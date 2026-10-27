from typing import Dict, Any, List

def generate_risk_explanation(
    txn: Dict[str, Any],
    features: Dict[str, Any],
    rules: List[Dict[str, Any]],
    anomaly: Dict[str, Any],
    graph: Dict[str, Any],
    supervised: Dict[str, Any],
    final_score: float
) -> str:
    parts = []
    
    amount = float(txn["amount"])
    source = txn["source_account_id"]
    dest = txn.get("destination_account_id") or txn.get("beneficiary_name") or "External counterparty"
    
    parts.append(f"Account {source} initiated a {txn.get('transaction_type', 'transfer')} of ${amount:,.2f} to {dest}.")
    
    # Rules finding
    if rules:
        rule_names = [f"'{r['name']}'" for r in rules]
        parts.append(f"Activity triggered {len(rules)} detection rule(s): {', '.join(rule_names)}.")
    
    # Statistical Anomaly finding
    if anomaly.get("anomaly_detected"):
        parts.append(f"Behavioral deviation detected: {anomaly['reason']}.")
    elif anomaly.get("confidence") == "LOW_HISTORY_CONFIDENCE":
        parts.append("Note: The account has limited transaction history, indicating low baseline confidence.")
        
    # Graph finding
    graph_signals = graph.get("signals", [])
    if graph_signals:
        sig_descs = [s["description"] for s in graph_signals]
        parts.append(f"Network topology signals observed: {'; '.join(sig_descs)}.")
        
    # Velocity finding
    count = features.get("short_window_count", 1)
    if count > 2:
        parts.append(f"Velocity monitor observed {count} transfers totaling ${features.get('short_window_sum', 0):,.2f} in recent window.")
        
    parts.append(f"Composite risk score calibrated at {final_score:.1f}/100. This evaluation constitutes an investigative priority indicator and warrants analyst examination.")
    
    return " ".join(parts)
