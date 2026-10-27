from typing import Dict, Any

def evaluate_velocity(features: Dict[str, Any]) -> Dict[str, Any]:
    count = features.get("short_window_count", 1)
    total_sum = features.get("short_window_sum", 0.0)
    
    score = 0.0
    is_triggered = False
    details = []
    
    if count >= 5:
        score += 45.0
        is_triggered = True
        details.append(f"High transaction frequency: {count} transactions in 10 minutes")
    elif count >= 3:
        score += 20.0
        details.append(f"Elevated frequency: {count} transactions in 10 minutes")
        
    if total_sum > 25000.0:
        score += 35.0
        is_triggered = True
        details.append(f"High cumulative outgoing volume: ${total_sum:,.2f} in 10 minutes")
        
    return {
        "velocity_score": min(score, 100.0),
        "is_triggered": is_triggered,
        "details": details
    }
