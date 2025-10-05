# IBIS-computer-network-security-in-ci

## Running (Docker)
1. docker-compose up --build
2. docker-compose down

## Running locally
1. python -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. python src/modbus_server.py
   python src/modbus_client.py
   sudo python src/mitm_attack.py
