SentinelFlow AI — API Reference
All versioned REST endpoints are exposed under /api/v1.
Health & Authentication
GET /health & GET /api/v1/health: System connectivity and database health status.
POST /api/v1/auth/login: Authenticate with username and password, returns JWT token.
POST /api/v1/auth/logout: Revoke active session.
GET /api/v1/auth/me: Retrieve authenticated user identity and role.
Dashboard & Analytics
GET /api/v1/dashboard/summary: High-level KPI metrics (transactions, alerts, open cases, confirmed fraud).
GET /api/v1/dashboard/trends: Hourly volume, risk band distribution, case status breakdown.
GET /api/v1/dashboard/activity: Audit trail event stream for recent operations.
Transactions
GET /api/v1/transactions: Paginated transaction explorer with risk band and account filters.
GET /api/v1/transactions/{id}: Detailed transaction attributes.
GET /api/v1/transactions/{id}/risk: Breakdown of component detector scores and narrative explanation.
GET /api/v1/transactions/{id}/relationships: 1-hop counterparty and device graph.
Alerts & Triage
GET /api/v1/alerts: Priority alert queue with severity and status filters.
GET /api/v1/alerts/{id}: Alert details with component findings.
POST /api/v1/alerts/{id}/assign: Assign alert to investigator.
POST /api/v1/alerts/{id}/triage: Update severity and add triage notes.
POST /api/v1/alerts/{id}/dismiss: Dismiss alert with mandatory auditable rationale.
POST /api/v1/alerts/{id}/investigate: Convert alert into a self-directed case.
Investigations & Evidence
GET /api/v1/investigations: Paginated case dossier explorer.
POST /api/v1/investigations: Create new investigation.
GET /api/v1/investigations/{id}: Complete case dossier with counts.
PATCH /api/v1/investigations/{id}: Update case priority or assignees.
GET /api/v1/investigations/{id}/evidence: Typed evidence records with verification status.
POST /api/v1/investigations/{id}/evidence: Add evidence item with SHA256 integrity hash.
GET /api/v1/investigations/{id}/tasks: Retrieve investigative checklist tasks.
PATCH /api/v1/investigations/{id}/tasks/{task_id}: Mark checklist task complete.
POST /api/v1/investigations/{id}/disposition: Submit case outcome with auditable justification.
POST /api/v1/investigations/{id}/review: Peer review approval or rejection.
Graph Intelligence & Copilot
GET /api/v1/graph: Multi-hop relationship graph data.
POST /api/v1/graph/expand: Expand immediate neighbors for a selected node.
POST /api/v1/graph/paths: Shortest path discovery between counterparties.
GET /api/v1/graph/suspicious-paths: Detect fan-in, circular transfers, and intermediary mules.
POST /api/v1/intelligence/copilot: Natural language question answering grounded in evidence citations.
Controlled Continuous Learning
GET /api/v1/learning/status: Model registry status, label readiness, drift warnings.
POST /api/v1/learning/train-candidate: Train candidate model on verified outcomes.
POST /api/v1/learning/promote-candidate: Promote candidate passing holdout validation gates.
POST /api/v1/learning/rollback: Roll back scoring model to baseline version.
Streaming & Simulation
GET /api/v1/stream/transactions: SSE event stream for live dashboard telemetry.
GET /api/v1/stream/simulation/status: Simulation engine state.
POST /api/v1/stream/simulation/scenario/{name}: 1-click deterministic execution of Scenarios A, B, C, D.
