import sqlite3
from typing import Dict, Any, List

def build_investigation_subgraph(
    conn: sqlite3.Connection,
    account_ids: List[str],
    max_hops: int = 2
) -> Dict[str, Any]:
    nodes = {}
    edges = {}
    
    visited_accounts = set(account_ids)
    frontier = set(account_ids)
    
    cursor = conn.cursor()
    
    # Add initial account nodes and their customers
    for acc_id in account_ids:
        cursor.execute("""
            SELECT a.id, a.account_number, a.balance, a.currency, a.is_dormant, c.id as cust_id, c.full_name, c.risk_tier
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.id = ?
        """, (acc_id,))
        row = cursor.fetchone()
        if row:
            nodes[acc_id] = {
                "id": acc_id,
                "label": f"Account {row['account_number']}",
                "type": "ACCOUNT",
                "risk_level": "HIGH" if row["is_dormant"] else "LOW",
                "properties": {
                    "balance": row["balance"],
                    "currency": row["currency"],
                    "dormant": bool(row["is_dormant"])
                }
            }
            cust_id = row["cust_id"]
            if cust_id not in nodes:
                nodes[cust_id] = {
                    "id": cust_id,
                    "label": f"Customer: {row['full_name']}",
                    "type": "CUSTOMER",
                    "risk_level": row["risk_tier"],
                    "properties": {"name": row["full_name"], "risk_tier": row["risk_tier"]}
                }
            e_id = f"owns_{cust_id}_{acc_id}"
            edges[e_id] = {
                "id": e_id,
                "source": cust_id,
                "target": acc_id,
                "type": "OWNS",
                "properties": {}
            }
            
    # Expand hops via transactions
    for _ in range(max_hops):
        if not frontier:
            break
        next_frontier = set()
        
        for curr_acc in list(frontier):
            # Outgoing transfers
            cursor.execute("""
                SELECT id, destination_account_id, beneficiary_name, amount, currency, created_at, device_id, ip_address
                FROM transactions
                WHERE source_account_id = ?
                ORDER BY created_at DESC LIMIT 30
            """, (curr_acc,))
            out_rows = cursor.fetchall()
            for r in out_rows:
                txn_id = r["id"]
                dest_acc = r["destination_account_id"]
                ben_name = r["beneficiary_name"]
                dev_id = r["device_id"]
                ip_addr = r["ip_address"]
                amt = float(r["amount"])
                
                # Device node
                if dev_id and dev_id not in nodes:
                    nodes[dev_id] = {
                        "id": dev_id,
                        "label": f"Device {dev_id[:8]}",
                        "type": "DEVICE",
                        "risk_level": "LOW",
                        "properties": {}
                    }
                    e_dev = f"dev_{curr_acc}_{dev_id}"
                    edges[e_dev] = {
                        "id": e_dev,
                        "source": curr_acc,
                        "target": dev_id,
                        "type": "USES_DEVICE",
                        "properties": {}
                    }
                    
                target_node_id = dest_acc or f"BEN-{ben_name}"
                if target_node_id and target_node_id not in nodes:
                    nodes[target_node_id] = {
                        "id": target_node_id,
                        "label": f"Beneficiary: {ben_name or dest_acc}",
                        "type": "ACCOUNT" if dest_acc else "BENEFICIARY",
                        "risk_level": "MEDIUM",
                        "properties": {"name": ben_name or dest_acc}
                    }
                    if dest_acc and dest_acc not in visited_accounts:
                        next_frontier.add(dest_acc)
                        visited_accounts.add(dest_acc)
                        
                e_flow = f"flow_{curr_acc}_{target_node_id}_{txn_id}"
                edges[e_flow] = {
                    "id": e_flow,
                    "source": curr_acc,
                    "target": target_node_id,
                    "type": "TRANSFERS_TO",
                    "amount": amt,
                    "currency": r["currency"],
                    "timestamp": r["created_at"],
                    "properties": {"transaction_id": txn_id}
                }
                
            # Inbound transfers
            cursor.execute("""
                SELECT id, source_account_id, amount, currency, created_at
                FROM transactions
                WHERE destination_account_id = ?
                ORDER BY created_at DESC LIMIT 30
            """, (curr_acc,))
            in_rows = cursor.fetchall()
            for r in in_rows:
                src_acc = r["source_account_id"]
                amt = float(r["amount"])
                txn_id = r["id"]
                if src_acc not in nodes:
                    nodes[src_acc] = {
                        "id": src_acc,
                        "label": f"Account {src_acc}",
                        "type": "ACCOUNT",
                        "risk_level": "LOW",
                        "properties": {}
                    }
                    if src_acc not in visited_accounts:
                        next_frontier.add(src_acc)
                        visited_accounts.add(src_acc)
                        
                e_in = f"flow_{src_acc}_{curr_acc}_{txn_id}"
                edges[e_in] = {
                    "id": e_in,
                    "source": src_acc,
                    "target": curr_acc,
                    "type": "TRANSFERS_TO",
                    "amount": amt,
                    "currency": r["currency"],
                    "timestamp": r["created_at"],
                    "properties": {"transaction_id": txn_id}
                }
                
        frontier = next_frontier
        
    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values())
    }
