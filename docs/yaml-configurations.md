# YAML Configuration Files

This document provides readable inline copies of all YAML configuration files in the SentinelFlow AI repository so they can be inspected in any browser or viewer without triggering file downloads.

---

## 1. `docker-compose.yml`
Path: [`docker-compose.yml`](file:///C:/Users/BATMA/.gemini/antigravity/scratch/sentinelflow-ai/docker-compose.yml)

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: sentinelflow-backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://sentinel_user:sentinel_pass@postgres:5432/sentinelflow_db
      - SECRET_KEY=sentinelflow_production_docker_secret_key_8492048
      - CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: sentinelflow-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    depends_on:
      - backend
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: sentinelflow-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=sentinel_user
      - POSTGRES_PASSWORD=sentinel_pass
      - POSTGRES_DB=sentinelflow_db
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel_user -d sentinelflow_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

---

## 2. `.github/workflows/ci.yml`
Path: [`.github/workflows/ci.yml`](file:///C:/Users/BATMA/.gemini/antigravity/scratch/sentinelflow-ai/.github/workflows/ci.yml)

```yaml
name: SentinelFlow AI CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install Python Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install uvicorn fastapi pydantic scikit-learn numpy pandas scipy

    - name: Run Database Seeding
      run: |
        python scripts/seed_demo_data.py

    - name: Execute Automated Test Suite
      run: |
        python backend/tests/run_tests.py

    - name: Test Scenario Simulation
      run: |
        python scripts/run_demo_scenario.py --scenario rapid_movement
```

---

## 3. `pnpm-workspace.yaml`
Path: [`pnpm-workspace.yaml`](file:///C:/Users/BATMA/.gemini/antigravity/scratch/sentinelflow-ai/pnpm-workspace.yaml)

```yaml
packages:
  - 'frontend'
```
