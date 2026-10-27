SentinelFlow AI — Graph Intelligence & Money-Flow Analysis
Graph Topology
SentinelFlow AI constructs an in-memory sub-graph representing financial money flows and entity relationships:
Nodes
Account: Primary financial transacting node.
Customer: Legal entity owning one or more accounts.
Beneficiary: Destination counterparty.
Device: Physical device fingerprint used to execute transactions.
Edges
OWNS: Customer owns Account.
TRANSFERS_TO: Money flow edge with amount, currency, and timestamp.
USES_DEVICE: Account transacted through Device.
Algorithmic Capabilities
Breadth-First Multi-Hop Traversal: Expands up to 3 hops from any focal account to discover connected counterparties.
Shortest Suspicious Path: Identifies fund movement chains between suspicious accounts.
Fan-In Collection Discovery: Flags accounts receiving transfers from 3 or more distinct accounts in short windows (typical of money mule collection).
Intermediary Mule Forwarding: Detects A → B → C flows where account B forwards 70%–110% of inbound funds while holding minimal permanent balance.
Circular Flow Detection: Detects reciprocal flows where funds return to the originator.
