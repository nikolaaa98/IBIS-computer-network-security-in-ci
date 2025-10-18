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
            temperature = random.randint(20, 100)  # Temperature in °C
            humidity = random.randint(0, 100)  # Humidity in %
            pressure = random.randint(900, 1100)  # Pressure in hPa
            # Store temperature in register 0, humidity in register 1, pressure in register 2
            DataBank.set_words(0, [temperature, humidity, pressure])
            logging.info(f'[SERVER] Temperature set to {temperature} °C, Humidity set to {humidity}%, Pressure set to {pressure} hPa (holding registers 0, 1, 2)')
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
