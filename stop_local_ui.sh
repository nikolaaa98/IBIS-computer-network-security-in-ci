#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT_DIR/pids"

if [ ! -d "$PID_DIR" ]; then
  echo "No pids directory found ($PID_DIR). Nothing to stop."
  exit 0
fi

echo "Stopping processes from $PID_DIR ..."
stopped=0

# Iterate all .pid files and try to stop processes cleanly
for pidfile in "$PID_DIR"/*.pid; do
  [ -e "$pidfile" ] || continue
  name="$(basename "$pidfile" .pid)"
  pid="$(cat "$pidfile")"

  # Skip empty pid
  if [ -z "$pid" ]; then
    echo "Empty PID in $pidfile; removing file."
    rm -f "$pidfile"
    continue
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $name (PID $pid) ..."
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    # if still alive, escalate
    if kill -0 "$pid" 2>/dev/null; then
      echo "PID $pid still alive, sending SIGTERM again..."
      kill -15 "$pid" 2>/dev/null || true
      sleep 0.5
    fi
    if kill -0 "$pid" 2>/dev/null; then
      echo "PID $pid still alive, sending SIGKILL ..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    stopped=$((stopped+1))
  else
    echo "$name PID $pid not running."
  fi

  # remove pidfile regardless
  rm -f "$pidfile"
done

# Extra safety: try to find leftover processes by common script names and kill them (best-effort)
# This helps if processes were started without pids written.
for pname in modbus_server mitm_proxy modbus_client ui_server control_ui; do
  pids=$(pgrep -f "$pname" || true)
  if [ -n "$pids" ]; then
    echo "Also killing leftover processes matching '$pname': $pids"
    echo "$pids" | xargs -r kill -9
  fi
done

echo "Done. Stopped $stopped processes."
