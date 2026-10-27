.PHONY: install dev up down migrate seed test lint demo reset-demo

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --reload --port 8000

up:
	docker-compose up -d

down:
	docker-compose down

seed:
	$(PYTHON) scripts/seed_demo_data.py

test:
	$(PYTHON) -m pytest backend/tests

lint:
	$(PYTHON) -m ruff check backend || true

demo:
	$(PYTHON) scripts/run_demo_scenario.py --scenario rapid-movement

reset-demo:
	$(PYTHON) scripts/reset_demo_data.py
