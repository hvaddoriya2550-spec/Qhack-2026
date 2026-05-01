.PHONY: setup dev stop restart nuke backend frontend lint test clean

# First-time setup
setup:
	bash infra/scripts/setup.sh

# Run both backend + frontend (stops stale processes first)
dev:
	bash dev.sh start

# Stop all running dev processes
stop:
	bash dev.sh stop

# Restart everything (stop + start)
restart:
	bash dev.sh restart

# Nuke DB and restart fresh
nuke:
	bash dev.sh nuke

# Run backend only
backend:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Run frontend only
frontend:
	cd frontend && npm run dev

# Lint both
lint:
	cd backend && source .venv/bin/activate && ruff check . && mypy app
	cd frontend && npm run lint

# Test both
test:
	cd backend && source .venv/bin/activate && pytest
	cd frontend && npm test

# Clean build artifacts
clean:
	rm -rf backend/.venv backend/__pycache__ backend/*.egg-info
	rm -rf frontend/node_modules frontend/dist
