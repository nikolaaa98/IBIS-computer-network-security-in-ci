# modbus_client.py
# HMI / operator client that reads register 0 every N seconds
from pyModbusTCP.client import ModbusClient
import time, logging
import argparse

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_client(target_host='modbus_server', target_port=502, poll_interval=3):
    client = ModbusClient(host=target_host, port=target_port, auto_open=True, auto_close=False)
    logging.info('Modbus client initialized to %s:%s', target_host, target_port)
    # wait until open
    while not client.is_open():
        logging.info('Waiting for server...')
        try:
            client.open()
        except Exception:
            pass
        time.sleep(1)
    logging.info('Client connected to %s:%s', target_host, target_port)

    try:
        while True:
            regs = client.read_holding_registers(0, 1)
            if regs:
                logging.info(f'[CLIENT] Current temperature read from register 0: {regs[0]} °C')
            else:
                logging.warning('No registers read (None)')
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logging.info('Client stopped by user')
    except Exception as e:
        logging.exception('Client error: %s', e)
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Modbus HMI client')
    parser.add_argument('--host', default='modbus_server', help='Target Modbus host (default: modbus_server)')
    parser.add_argument('--port', type=int, default=502, help='Target Modbus port (default: 502)')
    parser.add_argument('--interval', type=float, default=3.0, help='Polling interval seconds')
    args = parser.parse_args()
    run_client(target_host=args.host, target_port=args.port, poll_interval=args.interval)
