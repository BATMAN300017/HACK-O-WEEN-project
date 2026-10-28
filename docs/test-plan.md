# SentinelFlow AI — Automated Test Plan

## Implemented tests

Backend tests in `backend/tests/` cover login, disabled-account rejection,
existing-token invalidation after account deactivation, production secret
validation, and unsupported database URLs.

Frontend tests in `frontend/tests/unit/` cover currency and empty-date
formatting.

Run them from the repository root:

```shell
python -m pytest
npm test
```

GitHub Actions also runs frontend lint/build and the backend test suite on
Python 3.11 and 3.12.

## Remaining coverage

Add focused tests for transaction ingestion and detection, graph traversal,
investigation lifecycle and permissions, API routes, and frontend components.
