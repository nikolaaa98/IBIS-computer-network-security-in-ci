#!/bin/bash
echo "=== Stopping IBIS Demo Environment ==="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Stopping all services..."
pkill -f "modbus_server.py" || true
pkill -f "modbus_client.py" || true
pkill -f "mitm_proxy.py" || true
pkill -f "ui_server.py" || true
pkill -f "modbus_recon_inject.py" || true
pkill -f "modbus_dos_attack.py" || true
pkill -f "defense_module.py" || true

sleep 3

# Clean up PID files
rm -f pids/*.pid

echo "All services stopped."
echo "=== Demo Environment Shutdown Complete ==="