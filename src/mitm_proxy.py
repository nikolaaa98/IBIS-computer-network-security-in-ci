# mitm_proxy.py
# Safe Modbus "MITM simulator" implemented as an explicit proxy.
#
# USAGE:
#  - Configure the HMI/client to connect to this proxy (default 0.0.0.0:1502).
#  - The proxy connects to the real Modbus server (PLC).
#
# WARNING: This is a simulator/proxy. It does NOT perform ARP spoofing or network-level attacks.
# Use only in an isolated lab environment.

from pyModbusTCP.server import ModbusServer, DataBank
from pyModbusTCP.client import ModbusClient
import threading, time, logging, argparse

import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROL_FILE = os.path.join(ROOT, "control.json")


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

DEFAULT_PROXY_HOST = '0.0.0.0'
DEFAULT_PROXY_PORT = 1502
DEFAULT_SERVER_HOST = '127.0.0.1'
DEFAULT_SERVER_PORT = 502
DEFAULT_SYNC_INTERVAL = 1.5

class ModbusProxy:
    def __init__(self, proxy_host, proxy_port, server_host, server_port, sync_interval, manipulate):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.server_host = server_host
        self.server_port = server_port
        self.sync_interval = sync_interval
        self.manipulate = manipulate
        self.client = ModbusClient(host=self.server_host, port=self.server_port, auto_open=True)
        self.server = ModbusServer(host=self.proxy_host, port=self.proxy_port, no_block=True)
        self.running = False

    def start(self):
        logging.info('Starting Modbus proxy server on %s:%s', self.proxy_host, self.proxy_port)
        self.server.start()
        self.running = True
        t = threading.Thread(target=self.sync_loop, daemon=True)
        t.start()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logging.info('Stopping proxy...')
            self.running = False
            self.server.stop()
            try:
                self.client.close()
            except:
                pass

    def sync_loop(self):
        # connect to real server
        while not self.client.is_open() and self.running:
            logging.info('Proxy waiting for connection to real server %s:%s', self.server_host, self.server_port)
            try:
                self.client.open()
            except Exception:
                pass
            time.sleep(1)

        logging.info('Proxy connected to real server %s:%s', self.server_host, self.server_port)
        while self.running:
            try:
                # --- dynamic control via control.json (UI) ---
                try:
                    if os.path.exists(CONTROL_FILE):
                        with open(CONTROL_FILE, "r") as f:
                            c = json.load(f)
                        # ensure boolean
                        self.manipulate = bool(c.get("manipulate", self.manipulate))
                except Exception:
                    pass
                # -------------------------------------------

                regs = self.client.read_holding_registers(0, 10)
                if regs:
                    copied = list(regs)
                    if self.manipulate:
                        # Simple manipulation: increase temperature (reg 0) by 10, humidity (reg 1) by 5, pressure (reg 2) by 20
                        orig_temp = copied[0]
                        orig_humidity = copied[1]
                        orig_pressure = copied[2]
                        copied[0] = max(0, orig_temp + 10)  # Temperature in °C
                        copied[1] = min(100, orig_humidity + 5)  # Cap humidity at 100%
                        copied[2] = max(900, min(1100, orig_pressure + 20))  # Cap pressure between 900–1100 hPa
                        logging.info(f'[PROXY] Manipulated reg0: {orig_temp} -> {copied[0]} °C, reg1: {orig_humidity} -> {copied[1]}%, reg2: {orig_pressure} -> {copied[2]} hPa')
                    DataBank.set_words(0, copied)
                else:
                    logging.debug('[PROXY] No registers read from real server.')
            except Exception as e:
                logging.exception('Error during sync: %s', e)
                try:
                    self.client.close()
                except:
                    pass
                # try to reconnect
                time.sleep(2)
                while not self.client.is_open() and self.running:
                    try:
                        self.client.open()
                        logging.info('Proxy reconnected to real server')
                    except:
                        time.sleep(1)
            time.sleep(self.sync_interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Modbus proxy (safe MITM simulator)')
    parser.add_argument('--proxy-host', default=DEFAULT_PROXY_HOST)
    parser.add_argument('--proxy-port', type=int, default=DEFAULT_PROXY_PORT)
    parser.add_argument('--server-host', default=DEFAULT_SERVER_HOST)
    parser.add_argument('--server-port', type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument('--sync-interval', type=float, default=DEFAULT_SYNC_INTERVAL)
    parser.add_argument('--no-manipulate', dest='manipulate', action='store_false', help='Disable manipulation (copy registers as-is)')
    args = parser.parse_args()

    proxy = ModbusProxy(
        proxy_host=args.proxy_host,
        proxy_port=args.proxy_port,
        server_host=args.server_host,
        server_port=args.server_port,
        sync_interval=args.sync_interval,
        manipulate=args.manipulate
    )
    proxy.start()
