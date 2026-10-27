#!/usr/bin/env bash
set -e

echo "=== Bootstrapping SentinelFlow AI ==="

# 1. Initialize environment
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Seed database
echo "Seeding deterministic demo data..."
python scripts/seed_demo_data.py

echo "=== SentinelFlow AI is ready to launch! ==="
echo "Run: uvicorn app.main:app --app-dir backend --reload --port 8000"
