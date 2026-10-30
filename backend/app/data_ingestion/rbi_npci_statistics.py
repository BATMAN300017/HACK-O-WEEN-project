"""
RBI & NPCI Payment Statistics Calibration Subsystem.

Aggregates official macro payment indicators from:
1. RBI Database on Indian Economy (Table: financial_sector.r612_payment_system_indicators)
   Source: https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators
2. RBI Payment System Indicators
   Source: https://dataful.in/datasets/136/
3. NPCI UPI Product Statistics
   Source: https://www.npci.org.in/product/upi/product-statistics
4. NPCI IMPS Product Statistics
   Source: https://www.npci.org.in/product/imps/product-statistics

PURPOSE:
Calibrate realistic monetary amount distributions, payment channel shares,
and velocity patterns for the synthetic Indian banking transaction simulator.

IMPORTANT DISCLAIMER:
These records are aggregate macro indicators published by central banking authorities.
They are used strictly to parameterize statistical distributions (log-normal, Pareto)
and do NOT represent real individual customer account records.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class PaymentChannelBenchmark:
    channel_code: str
    channel_name: str
    reporting_period: str
    source_url: str
    monthly_volume_million: float
    monthly_value_inr_crores: float
    avg_ticket_size_inr: float
    min_typical_inr: float
    max_typical_inr: float
    median_inr: float
    distribution_family: str  # lognormal, pareto, truncated_normal
    distribution_params: Dict[str, float]
    channel_share_percentage: float

# Aggregated and calibrated parameters from recent RBI & NPCI releases (FY 2024-25 baseline)
CALIBRATED_INDIAN_PAYMENT_BENCHMARKS: Dict[str, PaymentChannelBenchmark] = {
    "UPI": PaymentChannelBenchmark(
        channel_code="UPI",
        channel_name="Unified Payments Interface (NPCI)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://www.npci.org.in/product/upi/product-statistics",
        monthly_volume_million=14960.0,  # ~15 billion monthly transactions
        monthly_value_inr_crores=2064000.0,  # ~20.64 lakh crore INR
        avg_ticket_size_inr=1380.0,
        min_typical_inr=10.0,
        max_typical_inr=100000.0,
        median_inr=320.0,
        distribution_family="lognormal",
        distribution_params={"mean": 5.76, "sigma": 1.25},
        channel_share_percentage=72.0
    ),
    "IMPS": PaymentChannelBenchmark(
        channel_code="IMPS",
        channel_name="Immediate Payment Service (NPCI)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://www.npci.org.in/product/imps/product-statistics",
        monthly_volume_million=470.0,
        monthly_value_inr_crores=568000.0,
        avg_ticket_size_inr=12085.0,
        min_typical_inr=500.0,
        max_typical_inr=500000.0,
        median_inr=4500.0,
        distribution_family="lognormal",
        distribution_params={"mean": 8.41, "sigma": 1.10},
        channel_share_percentage=12.0
    ),
    "NEFT": PaymentChannelBenchmark(
        channel_code="NEFT",
        channel_name="National Electronic Funds Transfer (RBI)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators",
        monthly_volume_million=380.0,
        monthly_value_inr_crores=3250000.0,
        avg_ticket_size_inr=85500.0,
        min_typical_inr=5000.0,
        max_typical_inr=2000000.0,
        median_inr=35000.0,
        distribution_family="lognormal",
        distribution_params={"mean": 10.46, "sigma": 1.35},
        channel_share_percentage=8.0
    ),
    "RTGS": PaymentChannelBenchmark(
        channel_code="RTGS",
        channel_name="Real Time Gross Settlement (RBI - High Value)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators",
        monthly_volume_million=21.0,
        monthly_value_inr_crores=14800000.0,
        avg_ticket_size_inr=7047000.0,
        min_typical_inr=200000.0,
        max_typical_inr=100000000.0,
        median_inr=1500000.0,
        distribution_family="pareto",
        distribution_params={"alpha": 1.85, "scale": 200000.0},
        channel_share_percentage=1.5
    ),
    "CARDS": PaymentChannelBenchmark(
        channel_code="CARDS",
        channel_name="Debit and Credit Card PoS / E-Commerce (RBI)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://dataful.in/datasets/136/",
        monthly_volume_million=610.0,
        monthly_value_inr_crores=185000.0,
        avg_ticket_size_inr=3030.0,
        min_typical_inr=100.0,
        max_typical_inr=150000.0,
        median_inr=1450.0,
        distribution_family="lognormal",
        distribution_params={"mean": 7.28, "sigma": 0.95},
        channel_share_percentage=4.5
    ),
    "ATM_WITHDRAWAL": PaymentChannelBenchmark(
        channel_code="ATM_WITHDRAWAL",
        channel_name="Automated Teller Machine Cash Dispensation (RBI)",
        reporting_period="FY 2024-25 Monthly Average",
        source_url="https://dbie.rbihub.in/statistics?table=financial_sector.r612_payment_system_indicators",
        monthly_volume_million=420.0,
        monthly_value_inr_crores=198000.0,
        avg_ticket_size_inr=4714.0,
        min_typical_inr=100.0,
        max_typical_inr=20000.0,
        median_inr=3000.0,
        distribution_family="truncated_normal",
        distribution_params={"mean": 4500.0, "std": 3200.0, "min": 100.0, "max": 20000.0},
        channel_share_percentage=2.0
    )
}

def get_channel_benchmarks() -> List[Dict[str, Any]]:
    """Returns the list of official macro payment calibration profiles."""
    return [asdict(b) for b in CALIBRATED_INDIAN_PAYMENT_BENCHMARKS.values()]

def get_channel_weights() -> Dict[str, float]:
    """Returns relative sampling probabilities for each payment channel."""
    return {k: v.channel_share_percentage / 100.0 for k, v in CALIBRATED_INDIAN_PAYMENT_BENCHMARKS.items()}
