#!/bin/bash

echo "=== IBIS Demo - Industrial Control System Security ==="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Install required packages
echo "Installing required packages..."
pip install pypcap netifaces > /dev/null 2>&1

mkdir -p logs pids wireshark_captures

echo "Stopping existing processes..."
pkill -f "modbus_server.py" 2>/dev/null || true
pkill -f "modbus_client.py" 2>/dev/null || true
pkill -f "mitm_proxy.py" 2>/dev/null || true
pkill -f "ui_server.py" 2>/dev/null || true
pkill -f "defense_module.py" 2>/dev/null || true
pkill -f "packet_capture.py" 2>/dev/null || true
sleep 3

echo "Cleaning logs..."
for logfile in logs/*.log; do
    if [ -f "$logfile" ]; then
        > "$logfile"
    fi
done

echo "Starting Modbus Server on port 5020..."
python3 src/modbus_server.py --port 5020 > logs/modbus_server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > pids/modbus_server.pid
echo "Server PID: $SERVER_PID (port 5020)"
sleep 5

echo "Starting MITM Proxy on port 1502..."
python3 src/mitm_proxy.py --server-port 5020 > logs/modbus_proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > pids/modbus_proxy.pid
echo "Proxy PID: $PROXY_PID (1502 -> 5020)"
sleep 3

echo "Starting Modbus Client..."
python3 src/modbus_client.py --host 127.0.0.1 --port 1502 > logs/modbus_client.log 2>&1 &
CLIENT_PID=$!
echo $CLIENT_PID > pids/modbus_client.pid
echo "Client PID: $CLIENT_PID (port 1502 - PROXY)"
sleep 2

echo "Starting Web UI..."
python3 src/ui_server.py > logs/ui_server.log 2>&1 &
UI_PID=$!
echo $UI_PID > pids/ui_server.pid
echo "UI PID: $UI_PID"
sleep 3

echo ""
echo "=== Architecture ==="
echo "Real Server (5020)"
echo "HMI Client -> Proxy (1502) -> Server (5020)"
echo ""
echo "=== Demo is running! ==="
echo "Web Interface: http://localhost:8080"
echo "Packet Capture: ACTIVE (Pure Python)"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "=============================="

# Keep script running and wait for Ctrl+C
trap 'echo ""; echo "Stopping demo..."; pkill -P $$; exit 0' INT

# Monitor services and keep script alive
while true; do
    sleep 10
    # Check if UI server is still running
    if ! ps -p $UI_PID > /dev/null 2>&1; then
        echo "UI server stopped - ending demo"
        break
    fi
done

echo "Stopping all services..."
pkill -f "modbus_server.py" 2>/dev/null || true
pkill -f "modbus_client.py" 2>/dev/null || true
pkill -f "mitm_proxy.py" 2>/dev/null || true
pkill -f "ui_server.py" 2>/dev/null || true
pkill -f "defense_module.py" 2>/dev/null || true
pkill -f "packet_capture.py" 2>/dev/null || true

echo "Demo stopped successfully"