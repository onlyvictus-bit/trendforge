PYTHON ?= python

.PHONY: install install-ai test screen dashboard endpoint-audit

install:
	$(PYTHON) -m pip install -r backend/requirements-dev.txt

install-ai:
	$(PYTHON) -m pip install -r backend/requirements-ai.txt

test:
	cd backend && $(PYTHON) -m pytest -q
	cd backend && $(PYTHON) -m ruff check trendforge_api tests
	cd backend && $(PYTHON) -m mypy trendforge_api --ignore-missing-imports
	cd frontend && npm test

screen:
	cd backend && $(PYTHON) -m trendforge_api.cli benchmark-nifty50

dashboard:
	cd backend && $(PYTHON) -m uvicorn trendforge_api.main:app --host 127.0.0.1 --port 8000

endpoint-audit:
	cd backend && $(PYTHON) -m tools.audit_institutional_endpoints
