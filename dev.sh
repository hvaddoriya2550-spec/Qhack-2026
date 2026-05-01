#!/usr/bin/env bash
# =============================================================================
# dev.sh — Start / Stop / Restart the full dev stack
#
# Usage:
#   bash dev.sh start     Start backend + frontend (default)
#   bash dev.sh stop      Kill any running backend/frontend processes
#   bash dev.sh restart   Stop then start
#   bash dev.sh nuke      Stop, delete SQLite DB, then start fresh
# =============================================================================

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$ROOT/.dev-pids"
BE_PORT=8000
FE_PORT=5173

# ---------- helpers ----------------------------------------------------------

kill_by_port() {
  local port=$1
  if command -v lsof &>/dev/null; then
    lsof -ti :"$port" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  elif command -v netstat &>/dev/null; then
    netstat -ano 2>/dev/null \
      | grep ":${port} " \
      | grep LISTENING \
      | awk '{print $NF}' \
      | sort -u \
      | while read -r pid; do
          [ -n "$pid" ] && [ "$pid" != "0" ] && taskkill //F //PID "$pid" 2>/dev/null || true
        done
  fi
}

kill_saved_pids() {
  if [ -f "$PIDFILE" ]; then
    while read -r pid; do
      kill "$pid" 2>/dev/null || true
    done < "$PIDFILE"
    rm -f "$PIDFILE"
  fi
}

port_is_free() {
  local port=$1
  ! netstat -ano 2>/dev/null | grep ":${port} " | grep -q LISTENING
}

do_stop() {
  echo "==> Stopping dev stack..."
  kill_saved_pids
  kill_by_port $BE_PORT
  kill_by_port $FE_PORT
  sleep 1
  echo "    All processes stopped."
}

do_start() {
  echo "==> Starting dev stack..."

  # Backend
  echo "    Backend on :$BE_PORT ..."
  cd "$ROOT/backend"
  # Support both Windows (Scripts/) and Unix (bin/) venv layouts
  if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
  else
    source .venv/bin/activate
  fi
  uvicorn app.main:app --reload --host 0.0.0.0 --port $BE_PORT &
  BE_PID=$!

  # Frontend
  echo "    Frontend on :$FE_PORT ..."
  cd "$ROOT/frontend"
  npm run dev &
  FE_PID=$!

  # Save PIDs for later stop
  printf "%s\n%s\n" "$BE_PID" "$FE_PID" > "$PIDFILE"

  echo ""
  echo "    Backend  PID=$BE_PID  http://localhost:$BE_PORT"
  echo "    Frontend PID=$FE_PID  http://localhost:$FE_PORT"
  echo ""
  echo "    Press Ctrl+C to stop both."

  # Cleanup on Ctrl+C
  trap 'do_stop; exit 0' SIGINT SIGTERM

  wait
}

do_nuke() {
  echo "==> Nuking database and restarting fresh..."
  do_stop

  # Remove all SQLite DB files in backend/
  for db in "$ROOT"/backend/*.db; do
    if [ -f "$db" ]; then
      echo "    Deleted $(basename "$db")"
      rm -f "$db"
    fi
  done

  echo "    DB will be recreated on startup."
  do_start
}

# ---------- main -------------------------------------------------------------

CMD="${1:-start}"

case "$CMD" in
  start)
    do_stop
    do_start
    ;;
  stop)
    do_stop
    ;;
  restart)
    do_stop
    do_start
    ;;
  nuke)
    do_nuke
    ;;
  *)
    echo "Usage: bash dev.sh {start|stop|restart|nuke}"
    exit 1
    ;;
esac
