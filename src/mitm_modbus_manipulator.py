# mitm_modbus_manipulator.py
# Simple script that connects as a Modbus client and writes a value to register 0.
# Use only in test environments where you control the server.
from pyModbusTCP.client import ModbusClient
import argparse, logging, time

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def write_register(host, port, value):
    client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)
    logging.info('Connecting to Modbus server %s:%s', host, port)
    if not client.open():
        logging.error('Failed to connect to server')
        return
    try:
        # write single holding register at address 0
        ok = client.write_single_register(0, int(value))
        if ok:
            logging.info('Wrote value %s to register 0', value)
        else:
            logging.error('Failed to write register')
    except Exception as e:
        logging.exception('Error writing register: %s', e)
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Write one register on a Modbus server (test only)')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=502, help='Server port')
    parser.add_argument('--value', type=int, required=True, help='Value to write to register 0')
    args = parser.parse_args()
    write_register(args.host, args.port, args.value)
