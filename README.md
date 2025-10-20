# IBIS Project - Network Security in Critical Infrastructure

## Running with Docker
# 1. build + up (detached)
```
UI_PORT=8080 docker-compose up --build -d
```

# 2. check logs
```
docker-compose logs -f ui_server modbus_proxy modbus_server modbus_client
```

# 3. docker stop
```
docker-compose down
```

# 4. delete artifactes
```
docker-compose down --volumes --remove-orphans
```

## Running locally
```
1. python -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. python src/modbus_server.py
   python src/modbus_client.py
   sudo python src/mitm_attack.py
```

# Running using scripts (without UI)
```
1. chmod +x run_local.sh stop_local.sh
2. run script ./run_local.sh 15002 1502
3. check logs tail -f logs/modbus_server.log logs/modbus_proxy.log logs/modbus_client.log
4. stop process ./stop_local.sh
```

# Running using scripts (with UI)
```
1. chmod +x run_with_ui.sh stop_local_ui.sh
2. run script ./run_with_ui.sh 15002 1502 8080
3. check browser : http://127.0.0.1:8080
3. check logs tail -n 30 logs/ui_server.log
4. stop process ./stop_local_ui.sh
```

# 5. HOW TO RUN (MAC OS)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x run_with_ui_mac.sh stop_demo_mac.sh
./run_with_ui_mac.sh 
```

# 5. HOW TO RUN (WINDOWS)
```
# Create virtual environment
python -m venv .venv
# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# Install requirements
pip install -r requirements.txt
# Run the demo
.\run_demo.ps1
.\stop_demo.ps1
```