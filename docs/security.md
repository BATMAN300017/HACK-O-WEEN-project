# SentinelFlow AI — Security & Responsible AI Safeguards

## Access Control Matrix

| Role | View Alerts | Triage Alerts | Open Case | Submit Disposition | Peer Review | Edit Rules | Train Model | Promote Model | Audit Trail |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Investigator** | &check; | &check; | &check; | &check; | &cross; | &cross; | &cross; | &cross; | &cross; |
| **Senior Investigator** | &check; | &check; | &check; | &check; | &check; | &cross; | &check; | &check; | &check; |
| **Fraud Ops Admin** | &check; | &check; | &check; | &check; | &check; | &check; | &check; | &check; | &check; |
| **Auditor** | &check; | &cross; | &cross; | &cross; | &cross; | &cross; | &cross; | &cross; | &check; |

## Defense in Depth
1. **Password Hashing**: PBKDF2 with SHA-256 and unique per-user cryptographic salt (100,000 iterations).
2. **Access Tokens**: Short-lived HMAC-SHA256 bearer tokens with payload expiration checks.
3. **Sensitive Field Redaction**: Tokens, passwords, card numbers, and credentials are automatically redacted in structured JSON logs.
4. **Untrusted Data Sanitization**: External transaction descriptions and payee notes are sanitized to protect against XSS and prompt injection attacks.
5. **Human-in-the-Loop Safeguard**: The system never automatically closes customer accounts, freezes funds, or declares legal guilt without an authorized investigator disposition.
