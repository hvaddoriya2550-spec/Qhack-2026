#!/usr/bin/env bash
set -e

echo "=== Setting up Multi-Agent Chat ==="

# Backend
echo "--- Backend setup ---"
cd "$(dirname "$0")/../../backend"
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp -n .env.example .env 2>/dev/null || true
echo "Backend ready. Activate with: source backend/.venv/bin/activate"

# Frontend
echo "--- Frontend setup ---"
cd ../frontend
npm install
echo "Frontend ready."

echo ""
echo "=== Setup complete ==="
echo "Run backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "Run frontend: cd frontend && npm run dev"
