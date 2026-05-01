#!/usr/bin/env bash
# Starts both backend and frontend in parallel for local development.
# Usage: bash infra/scripts/dev.sh

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

cleanup() {
  echo "Shutting down..."
  kill $BE_PID $FE_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# Backend
echo "Starting backend on :8000..."
cd "$ROOT/backend"
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BE_PID=$!

# Frontend
echo "Starting frontend on :5173..."
cd "$ROOT/frontend"
npm run dev &
FE_PID=$!

echo "Backend PID=$BE_PID | Frontend PID=$FE_PID"
echo "Press Ctrl+C to stop both."
wait
