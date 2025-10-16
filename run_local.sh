#!/usr/bin/env bash
set -euo pipefail
# run_local.sh - sets up .venv (if needed), installs requirements, and starts server+proxy+client
# Logs go to ./logs/, PIDs to ./pids/
# Usage: ./run_local.sh [server_port] [proxy_port]
# Example: ./run_local.sh 502 1502

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

# Cross-platform venv paths (Windows uses Scripts, Unix uses bin)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    VENV_BIN="Scripts"
else
    VENV_BIN="bin"
fi

PYTHON="$VENV_DIR/$VENV_BIN/python"
PIP="$VENV_DIR/$VENV_BIN/pip"

SERVER_PORT="${1:-502}"
PROXY_PORT="${2:-1502}"
SERVER_HOST="127.0.0.1"
PROXY_HOST="127.0.0.1"
CLIENT_INTERVAL=3

LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

echo "Project root: $ROOT_DIR"
echo "Using server: $SERVER_HOST:$SERVER_PORT"
echo "Proxy (HMI endpoint): $PROXY_HOST:$PROXY_PORT"

# 1) create venv if needed
if [ ! -x "$PYTHON" ]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
  echo "Activating venv and installing requirements..."
  "$PIP" install --upgrade pip
  "$PIP" install -r "$ROOT_DIR/requirements.txt"
else
  echo "Virtual environment found. Ensuring requirements are installed..."
  "$PIP" install --upgrade pip
  "$PIP" install -r "$ROOT_DIR/requirements.txt"
fi

# helper to run a command in background and record PID
run_bg() {
  local name="$1"; shift
  local logfile="$LOG_DIR/${name}.log"
  echo "Starting $name -> $logfile"
  # start process in background
  nohup "$PYTHON" "$@" > "$logfile" 2>&1 &
  local pid=$!
  echo $pid > "$PID_DIR/${name}.pid"
  echo "$name PID: $pid"
}

# 2) start modbus server
run_bg "modbus_server" "$ROOT_DIR/src/modbus_server.py" --host "$SERVER_HOST" --port "$SERVER_PORT"

# small sleep to give server time to bind
sleep 1

# 3) start proxy (connects to server)
run_bg "modbus_proxy" "$ROOT_DIR/src/mitm_proxy.py" --proxy-host 0.0.0.0 --proxy-port "$PROXY_PORT" --server-host "$SERVER_HOST" --server-port "$SERVER_PORT"

# small sleep before client
sleep 1

# 4) start client (connects to proxy)
run_bg "modbus_client" "$ROOT_DIR/src/modbus_client.py" --host "$PROXY_HOST" --port "$PROXY_PORT" --interval "$CLIENT_INTERVAL"

echo ""
echo "All services started. Logs: $LOG_DIR   PIDs: $PID_DIR"
echo "To follow logs, run: tail -f logs/modbus_server.log logs/modbus_proxy.log logs/modbus_client.log"
echo "To stop: ./stop_local.sh"
