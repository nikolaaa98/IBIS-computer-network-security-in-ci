#!/bin/bash

echo "=== 🔧 IBIS Demo - Nova Arhitektura ==="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

mkdir -p logs pids wireshark_captures

echo "Zaustavljam postojeće procese..."
pkill -f "modbus_server.py" || true
pkill -f "modbus_client.py" || true
pkill -f "mitm_proxy.py" || true
pkill -f "ui_server.py" || true
pkill -f "defense_module.py" || true
sleep 3


echo "🧹 Čistim logove..."
for logfile in logs/*.log; do
    if [ -f "$logfile" ]; then
        > "$logfile"
    fi
done

echo "🔧 Pokrećem Modbus Server na portu 5020..."
python3 src/modbus_server.py --port 5020 > logs/modbus_server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > pids/modbus_server.pid
echo "✅ Server PID: $SERVER_PID (port 5020)"
sleep 5

echo "Pokrećem MITM Proxy na portu 1502..."
python3 src/mitm_proxy.py --server-port 5020 > logs/modbus_proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > pids/modbus_proxy.pid
echo "Proxy PID: $PROXY_PID (1502 → 5020)"
sleep 3


echo "Pokrećem Modbus Client..."
python3 src/modbus_client.py --host 127.0.0.1 --port 1502 > logs/modbus_client.log 2>&1 &
CLIENT_PID=$!
echo $CLIENT_PID > pids/modbus_client.pid
echo "Client PID: $CLIENT_PID (port 1502 - PROXY)"

echo "Pokrećem Web UI..."
python3 src/ui_server.py > logs/ui_server.log 2>&1 &
UI_PID=$!
echo $UI_PID > pids/ui_server.pid
echo "UI PID: $UI_PID"
sleep 3

echo ""
echo "Defense System (502) → 🔧 Real Server (5020)"
echo "HMI Client (502) → 🛡️ Defense (502) → 🔧 Server (5020)"
echo "MITM Proxy (1502) → 🔧 Server (5020)"
echo ""
echo "=== Demo je spreman! ==="
echo "Web Interfejs: http://localhost:8080"
echo ""
echo "Testirajte:"
echo "1. Pokrenite napade - sada će ići kroz defense sistem"
echo "2. Vrednosti će biti: Client → Defense (502) → Server (5020)"
echo "3. MITM Proxy: Client → Proxy (1502) → Server (5020)"
echo "=============================="

wait