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
for pidfile in "$PID_DIR"/*.pid; do
  [ -e "$pidfile" ] || continue
  name="$(basename "$pidfile" .pid)"
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "Killing $name (PID $pid) ..."
    kill "$pid"
    sleep 0.2
    # if still alive, force kill
    if kill -0 "$pid" 2>/dev/null; then
      echo "PID $pid still alive, sending SIGKILL ..."
      kill -9 "$pid" || true
    fi
    stopped=$((stopped+1))
  else
    echo "$name PID $pid not running."
  fi
  rm -f "$pidfile"
done

echo "Done. Stopped $stopped processes."
