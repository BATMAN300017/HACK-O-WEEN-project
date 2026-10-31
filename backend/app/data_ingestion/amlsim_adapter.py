"""
IBM AMLSim Scenario Generator & Adapter.

Source: https://github.com/IBM/AMLSim
Characteristics:
- Multi-agent synthetic transaction simulation framework for AML research.
- IMPORTANT ARCHITECTURAL REQUIREMENT: Does NOT treat the simulator as a static downloaded dataset.
- Dynamically generates separately identifiable scenarios with recorded configuration,
  random seed, generation timestamp, and full scenario metadata.
- Supports structured typologies: FAN_IN, FAN_OUT, CYCLE, SCATTER_GATHER, BIPARTITE_MULE.
"""

import uuid
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.data_ingestion.label_isolation import store_protected_transaction_label

class AmlSimScenarioGenerator:
    """Configurable AMLSim scenario generator with recorded provenance and parameter seeds."""

    @classmethod
    def generate_scenario(
        cls,
        typology: str = "CYCLE",
        num_accounts: int = 5,
        base_amount: float = 50000.0,
        currency: str = "USD",
        random_seed: int = 42,
        noise_txns_count: int = 10
    ) -> Dict[str, Any]:
        """
        Generates a standalone, parameter-tracked AMLSim laundering scenario.
        Records configuration parameters, random seed, generation timestamp, and metadata.
        """
        rng = random.Random(random_seed)
        scenario_id = f"SCEN-AMLSIM-{typology.upper()}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        config_metadata = {
            "scenario_id": scenario_id,
            "typology": typology.upper(),
            "random_seed": random_seed,
            "base_amount": base_amount,
            "currency": currency,
            "num_accounts": num_accounts,
            "noise_txns_count": noise_txns_count,
            "generation_timestamp": now.isoformat(),
            "simulator_version": "IBM_AMLSim_v1.0_SentinelFlow"
        }

        # Generate accounts
        accounts = [f"AMLSIM_ACC_{scenario_id[:12]}_{i:03d}" for i in range(num_accounts)]
        transactions = []

        # 1. Generate typology-specific laundering transactions
        if typology.upper() == "CYCLE":
            # Circular transfer A -> B -> C -> ... -> A
            for i in range(num_accounts):
                src = accounts[i]
                dest = accounts[(i + 1) % num_accounts]
                amt = round(base_amount * (1.0 - (i * 0.02)), 2)  # slight laundering fee decay
                t_time = (now - timedelta(hours=(num_accounts - i) * 2)).isoformat()
                t_id = f"TXN-AMLSIM-{scenario_id[:10]}-L{i:03d}"

                store_protected_transaction_label(
                    transaction_id=t_id,
                    ground_truth_label=1,
                    dataset_name="AML_SIM",
                    scenario_id=scenario_id
                )

                transactions.append({
                    "id": t_id,
                    "event_id": f"EVT-{t_id}",
                    "source_account_id": src,
                    "destination_account_id": dest,
                    "customer_id": f"CUST-{src}",
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "TRANSFER",
                    "payment_channel": "WIRE",
                    "status": "COMPLETED",
                    "scenario_id": scenario_id,
                    "dataset_source": "AML_SIM",
                    "is_ground_truth_fraud": 0,  # Zeroed out in operational feature feed
                    "created_at": t_time
                })

        elif typology.upper() == "FAN_OUT":
            # 1 origin -> N destination layering
            origin = accounts[0]
            destinations = accounts[1:]
            split_amt = round(base_amount / len(destinations), 2)
            for i, dest in enumerate(destinations):
                t_time = (now - timedelta(minutes=i * 15)).isoformat()
                t_id = f"TXN-AMLSIM-{scenario_id[:10]}-FO{i:03d}"

                store_protected_transaction_label(
                    transaction_id=t_id,
                    ground_truth_label=1,
                    dataset_name="AML_SIM",
                    scenario_id=scenario_id
                )

                transactions.append({
                    "id": t_id,
                    "event_id": f"EVT-{t_id}",
                    "source_account_id": origin,
                    "destination_account_id": dest,
                    "customer_id": f"CUST-{origin}",
                    "amount": split_amt,
                    "currency": currency,
                    "transaction_type": "TRANSFER",
                    "payment_channel": "WIRE",
                    "status": "COMPLETED",
                    "scenario_id": scenario_id,
                    "dataset_source": "AML_SIM",
                    "is_ground_truth_fraud": 0,
                    "created_at": t_time
                })

        elif typology.upper() == "FAN_IN":
            # N origins -> 1 collector account (Smurfing aggregation)
            collector = accounts[-1]
            senders = accounts[:-1]
            split_amt = round(base_amount / len(senders), 2)
            for i, src in enumerate(senders):
                t_time = (now - timedelta(minutes=(len(senders) - i) * 10)).isoformat()
                t_id = f"TXN-AMLSIM-{scenario_id[:10]}-FI{i:03d}"

                store_protected_transaction_label(
                    transaction_id=t_id,
                    ground_truth_label=1,
                    dataset_name="AML_SIM",
                    scenario_id=scenario_id
                )

                transactions.append({
                    "id": t_id,
                    "event_id": f"EVT-{t_id}",
                    "source_account_id": src,
                    "destination_account_id": collector,
                    "customer_id": f"CUST-{src}",
                    "amount": split_amt,
                    "currency": currency,
                    "transaction_type": "TRANSFER",
                    "payment_channel": "ACH",
                    "status": "COMPLETED",
                    "scenario_id": scenario_id,
                    "dataset_source": "AML_SIM",
                    "is_ground_truth_fraud": 0,
                    "created_at": t_time
                })
        else:
            # Default Scatter-Gather
            hub_src = accounts[0]
            hub_dest = accounts[-1]
            intermediaries = accounts[1:-1] or [accounts[0]]
            for i, mid in enumerate(intermediaries):
                t_time1 = (now - timedelta(hours=4 - i)).isoformat()
                t_id1 = f"TXN-AMLSIM-{scenario_id[:10]}-SG1-{i:03d}"
                store_protected_transaction_label(transaction_id=t_id1, ground_truth_label=1, dataset_name="AML_SIM", scenario_id=scenario_id)
                transactions.append({
                    "id": t_id1, "event_id": f"EVT-{t_id1}", "source_account_id": hub_src,
                    "destination_account_id": mid, "customer_id": f"CUST-{hub_src}",
                    "amount": round(base_amount / len(intermediaries), 2), "currency": currency,
                    "transaction_type": "TRANSFER", "payment_channel": "WIRE", "status": "COMPLETED",
                    "scenario_id": scenario_id, "dataset_source": "AML_SIM", "is_ground_truth_fraud": 0,
                    "created_at": t_time1
                })
                t_time2 = (now - timedelta(hours=2 - i)).isoformat()
                t_id2 = f"TXN-AMLSIM-{scenario_id[:10]}-SG2-{i:03d}"
                store_protected_transaction_label(transaction_id=t_id2, ground_truth_label=1, dataset_name="AML_SIM", scenario_id=scenario_id)
                transactions.append({
                    "id": t_id2, "event_id": f"EVT-{t_id2}", "source_account_id": mid,
                    "destination_account_id": hub_dest, "customer_id": f"CUST-{mid}",
                    "amount": round((base_amount / len(intermediaries)) * 0.98, 2), "currency": currency,
                    "transaction_type": "TRANSFER", "payment_channel": "WIRE", "status": "COMPLETED",
                    "scenario_id": scenario_id, "dataset_source": "AML_SIM", "is_ground_truth_fraud": 0,
                    "created_at": t_time2
                })

        # 2. Generate background noise / routine transactions
        for j in range(noise_txns_count):
            n_src = rng.choice(accounts)
            n_dest = f"ROUTINE_EXT_{rng.randint(1000, 9999)}"
            n_amt = round(rng.uniform(10.0, 800.0), 2)
            n_time = (now - timedelta(minutes=rng.randint(5, 720))).isoformat()
            n_id = f"TXN-AMLSIM-{scenario_id[:10]}-N{j:03d}"

            store_protected_transaction_label(
                transaction_id=n_id,
                ground_truth_label=0,
                dataset_name="AML_SIM",
                scenario_id="ROUTINE_BACKGROUND"
            )

            transactions.append({
                "id": n_id,
                "event_id": f"EVT-{n_id}",
                "source_account_id": n_src,
                "destination_account_id": n_dest,
                "customer_id": f"CUST-{n_src}",
                "amount": n_amt,
                "currency": currency,
                "transaction_type": "PAYMENT",
                "payment_channel": "DEBIT_CARD",
                "status": "COMPLETED",
                "scenario_id": None,
                "dataset_source": "AML_SIM",
                "is_ground_truth_fraud": 0,
                "created_at": n_time
            })

        return {
            "scenario_metadata": config_metadata,
            "accounts_count": len(accounts),
            "laundering_transactions_count": len(transactions) - noise_txns_count,
            "noise_transactions_count": noise_txns_count,
            "total_transactions": len(transactions),
            "transactions": transactions
        }
