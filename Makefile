SHELL := /bin/bash
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest

.PHONY: all setup dev test fixtures types build clean

all: setup fixtures test build

setup:
	@echo "==> Setting up Python virtual environment and dependencies..."
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	@echo "==> Setting up Frontend dependencies..."
	cd frontend && npm install
	@echo "==> Ensuring data and doc directories..."
	mkdir -p data/synthetic data/jobs data/outputs data/local docs/evidence

fixtures:
	@echo "==> Generating synthetic radar fixtures..."
	source $(VENV)/bin/activate && PYTHONPATH=backend $(PYTHON) backend/scripts/make_synthetic.py

types:
	@echo "==> Generating OpenAPI specification and TypeScript contracts..."
	source $(VENV)/bin/activate && PYTHONPATH=backend $(PYTHON) -c "import json; from app.main import app; open('backend/openapi.json', 'w').write(json.dumps(app.openapi(), indent=2))"
	cd frontend && npx openapi-typescript ../backend/openapi.json -o ./lib/api-types.ts

test:
	@echo "==> Running backend tests..."
	source $(VENV)/bin/activate && PYTHONPATH=backend $(PYTEST) backend/tests -v
	@echo "==> Running frontend tests..."
	cd frontend && npm test

dev:
	@echo "==> Starting backend and frontend in development mode..."
	source $(VENV)/bin/activate && PYTHONPATH=backend $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 & \
	BACKEND_PID=$$!; \
	cd frontend && npm run dev & \
	FRONTEND_PID=$$!; \
	trap 'kill $$BACKEND_PID $$FRONTEND_PID' SIGINT SIGTERM EXIT; \
	wait

build:
	@echo "==> Building frontend..."
	cd frontend && npm run build
	@echo "==> Build complete."

clean:
	rm -rf data/jobs/* data/outputs/* frontend/.next frontend/node_modules $(VENV) backend/openapi.json

