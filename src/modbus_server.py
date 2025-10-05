# modbus_server.py
# Simple Modbus TCP server using pyModbusTCP - simulates a PLC sensor (temperature)
from pyModbusTCP.server import ModbusServer, DataBank
import time, random, logging
import argparse

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_server(host='0.0.0.0', port=502, interval=3):
    server = ModbusServer(host=host, port=port, no_block=True)
    try:
        server.start()
        logging.info('Modbus server started on %s:%s', host, port)
        while True:
            temperature = random.randint(20, 100)
            # store temperature in holding register 0
            DataBank.set_words(0, [temperature])
            logging.info(f'[SERVER] Temperature set to {temperature} °C (holding register 0)')
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info('Stopping server...')
        server.stop()
    except Exception as e:
        logging.exception('Server error: %s', e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple Modbus TCP server (simulator)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default 0.0.0.0)')
    parser.add_argument('--port', type=int, default=502, help='Port to bind (default 502)')
    parser.add_argument('--interval', type=float, default=3.0, help='Seconds between updates')
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, interval=args.interval)
