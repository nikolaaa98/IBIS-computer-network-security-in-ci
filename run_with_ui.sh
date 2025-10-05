#!/usr/bin/env bash
set -euo pipefail
# run_with_ui.sh - runs Modbus server, proxy, client, and Flask UI server
# Usage: ./run_with_ui.sh [server_port] [proxy_port] [ui_port]

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

SERVER_PORT="${1:-502}"
PROXY_PORT="${2:-1502}"
UI_PORT="${3:-8080}"
SERVER_HOST="127.0.0.1"
PROXY_HOST="127.0.0.1"
CLIENT_INTERVAL=3

LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# create venv if not exists
if [ ! -x "$PYTHON" ]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
  "$PIP" install --upgrade pip
  "$PIP" install -r "$ROOT_DIR/requirements.txt"
else
  "$PIP" install --upgrade pip
  "$PIP" install -r "$ROOT_DIR/requirements.txt"
fi

run_bg() {
  local name="$1"; shift
  local logfile="$LOG_DIR/${name}.log"
  echo "Starting $name -> $logfile"
  nohup "$PYTHON" "$@" > "$logfile" 2>&1 &
  echo $! > "$PID_DIR/${name}.pid"
}

# 1) start server
run_bg "modbus_server" "$ROOT_DIR/src/modbus_server.py" --host "$SERVER_HOST" --port "$SERVER_PORT"
sleep 1

# 2) start proxy
run_bg "modbus_proxy" "$ROOT_DIR/src/mitm_proxy.py" --proxy-host 0.0.0.0 --proxy-port "$PROXY_PORT" --server-host "$SERVER_HOST" --server-port "$SERVER_PORT"
sleep 1

# 3) start client
run_bg "modbus_client" "$ROOT_DIR/src/modbus_client.py" --host "$PROXY_HOST" --port "$PROXY_PORT" --interval "$CLIENT_INTERVAL"
sleep 1

# 4) start UI server
run_bg "ui_server" "$ROOT_DIR/src/ui_server.py" --proxy-host "$PROXY_HOST" --proxy-port "$PROXY_PORT" --port "$UI_PORT"

echo ""
echo "All services started."
echo "Server: $SERVER_HOST:$SERVER_PORT"
echo "Proxy: $PROXY_HOST:$PROXY_PORT"
echo "UI: http://$PROXY_HOST:$UI_PORT"
echo "Logs: $LOG_DIR, PIDs: $PID_DIR"
echo "To stop: ./stop_local.sh"
