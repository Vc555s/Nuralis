#!/usr/bin/env bash
#
# Nuralis launcher: FastAPI backend + Vite frontend.
#
# Usage:
#   ./start.sh [--install] [--no-frontend] [--clean]
#
#   --install      (Re)install Python and npm dependencies before starting.
#                  Runs automatically on the first start.
#   --no-frontend  Start the API only.
#   --clean        Recreate .venv and frontend/node_modules, then install.
#
# Environment:
#   BACKEND_PORT   API port (default 8010)
#   FRONTEND_PORT  UI port (default 5050)
#   BACKEND_HOST   API bind address (default 0.0.0.0)
#   PYTHON_BIN     Python used to create the virtualenv (default python3)
#   NURALIS_LLM_ENABLED=false   run without the local LLM (no GPU needed)
#
# Logs go to ./logs. Stop with Ctrl+C.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5050}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_PATH="$SCRIPT_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

INSTALL=0
CLEAN=0
START_FRONTEND=1
BACKEND_PID=""
FRONTEND_PID=""

for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    --clean) CLEAN=1; INSTALL=1 ;;
    --no-frontend) START_FRONTEND=0 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 1 ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Error: '$1' is required but not installed." >&2; exit 1; }
}

port_in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH "sport = :$1" 2>/dev/null | grep -q .
  else
    lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  fi
}

# Stop a previous Nuralis process on this port. Anything else that holds the
# port is left alone and reported, so other services are never killed.
free_port() {
  local port=$1 var=$2 pid cwd
  if command -v lsof >/dev/null 2>&1; then
    for pid in $(lsof -a -t -iTCP:"$port" -sTCP:LISTEN -u "$(id -u)" 2>/dev/null || true); do
      cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
      if [[ "$cwd" == "$SCRIPT_DIR"* ]]; then
        echo "  stopping previous Nuralis process on :$port (PID $pid)"
        kill "$pid" 2>/dev/null || true
      fi
    done
    sleep 1
  fi
  if port_in_use "$port"; then
    echo "Error: port $port is already in use by another program." >&2
    echo "       Pick another one, e.g.  $var=$((port + 1)) ./start.sh" >&2
    exit 1
  fi
}

wait_for_http() {
  local url=$1 timeout=${2:-60} i
  for ((i = 0; i < timeout * 2; i++)); do
    curl -fsS -o /dev/null "$url" 2>/dev/null && return 0
    sleep 0.5
  done
  return 1
}

cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "Stopping Nuralis..."
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "Stopped."
}
trap cleanup EXIT INT TERM

echo "=============================================="
echo " Nuralis — research intelligence platform"
echo "=============================================="

require_cmd "$PYTHON_BIN"
require_cmd curl
# The pinned PyTorch 2.0 / bitsandbytes stack only ships wheels for Python 3.9 - 3.11.
if ! "$PYTHON_BIN" -c 'import sys; sys.exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 11) else 1)'; then
  echo "Error: $("$PYTHON_BIN" --version 2>&1) is not supported; Nuralis needs Python 3.9 - 3.11." >&2
  echo "       Install one and run:  PYTHON_BIN=python3.11 ./start.sh" >&2
  exit 1
fi
[[ "$START_FRONTEND" -eq 1 ]] && require_cmd npm
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------- backend deps
if [[ "$CLEAN" -eq 1 && -d "$VENV_PATH" ]]; then
  echo "--clean: removing .venv"
  rm -rf "$VENV_PATH"
fi
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "Creating virtual environment in .venv ($("$PYTHON_BIN" --version 2>&1))..."
  "$PYTHON_BIN" -m venv "$VENV_PATH"
  INSTALL=1
fi
if [[ "$INSTALL" -eq 1 ]]; then
  echo "Installing Python dependencies (this downloads PyTorch; a few minutes on first run)..."
  "$VENV_PATH/bin/python" -m pip install --quiet --upgrade pip
  "$VENV_PATH/bin/python" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  echo "GPU: $(nvidia-smi -L | head -n 1)"
else
  echo "GPU: none detected — embeddings run on CPU and the LLM summary is skipped."
fi

# ---------------------------------------------------------------- backend
free_port "$BACKEND_PORT" BACKEND_PORT
echo "Starting API on ${BACKEND_HOST}:${BACKEND_PORT}..."
: >"$BACKEND_LOG"
PYTHONUNBUFFERED=1 "$VENV_PATH/bin/python" -m uvicorn api_server:app \
  --host "$BACKEND_HOST" --port "$BACKEND_PORT" --log-level warning >>"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/api/status" 90; then
  echo "Error: the API did not come up. Last log lines:" >&2
  tail -n 30 "$BACKEND_LOG" >&2
  exit 1
fi
echo "  API ready  → http://localhost:${BACKEND_PORT}/docs"

# ---------------------------------------------------------------- frontend
if [[ "$START_FRONTEND" -eq 1 ]]; then
  if [[ "$CLEAN" -eq 1 && -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "--clean: removing frontend/node_modules"
    rm -rf "$FRONTEND_DIR/node_modules"
  fi
  if [[ "$INSTALL" -eq 1 || ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm ci --no-audit --no-fund >/dev/null)
  fi

  # Tell the Vite dev proxy where the API lives.
  cat >"$FRONTEND_DIR/.env.local" <<EOF
VITE_API_BASE_URL=/api
VITE_MOCK_MODE=false
VITE_API_PROXY_TARGET=http://127.0.0.1:${BACKEND_PORT}
EOF

  free_port "$FRONTEND_PORT" FRONTEND_PORT
  echo "Starting UI on :${FRONTEND_PORT}..."
  : >"$FRONTEND_LOG"
  (cd "$FRONTEND_DIR" && exec ./node_modules/.bin/vite --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort) \
    >>"$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!
  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}/" 60; then
    echo "Error: the UI did not come up. Last log lines:" >&2
    tail -n 30 "$FRONTEND_LOG" >&2
    exit 1
  fi
  echo "  UI ready   → http://localhost:${FRONTEND_PORT}"
fi

echo ""
echo "Nuralis is running. Models load on the first analysis request."
echo "Logs: $LOG_DIR      Press Ctrl+C to stop."
wait
