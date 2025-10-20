# defense_module.py - KOMPLETNO NOVA VERZIJA
#!/usr/bin/env python3
"""
Advanced Modbus Defense System with Real Attack Prevention
"""

import socket
import struct
import time
import logging
import threading
from collections import defaultdict, deque
from datetime import datetime
import json
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/defense.log'),
        logging.StreamHandler()
    ]
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERT_FILE = os.path.join(ROOT, "logs", "attack.log")

class RealModbusDefense:
    def __init__(self, listen_port=502, target_host='127.0.0.1', target_port=5020):
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.running = False
        self.attack_prevention_enabled = True
        
        # Statistics
        self.connections = 0
        self.blocked_attacks = 0
        self.suspicious_activities = 0
        self.blocked_ips = set()
        
        # Attack patterns
        self.malicious_function_codes = {90, 91, 92, 93, 94, 95, 96, 97, 98, 99}
        self.rapid_request_threshold = 10  # requests per second
        self.request_timestamps = defaultdict(list)

    def start_defense(self):
        """Start defense system as a transparent proxy"""
        self.running = True
        logging.info(f"🛡️ Starting REAL Modbus Defense on port {self.listen_port}")
        logging.info(f"🎯 Forwarding to: {self.target_host}:{self.target_port}")
        logging.info(f"🔒 Attack prevention: {'ENABLED' if self.attack_prevention_enabled else 'DISABLED'}")
        
        try:
            # Create listening socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', self.listen_port))
            server_socket.listen(10)
            server_socket.settimeout(1)
            
            logging.info(f"📡 Defense listening on 0.0.0.0:{self.listen_port}")
            
            # Start stats thread
            stats_thread = threading.Thread(target=self.log_stats, daemon=True)
            stats_thread.start()
            
            while self.running:
                try:
                    client_socket, client_addr = server_socket.accept()
                    client_ip = client_addr[0]
                    
                    # Check if IP is blocked
                    if client_ip in self.blocked_ips:
                        logging.warning(f"🚫 Blocked connection from {client_ip}")
                        client_socket.close()
                        continue
                    
                    self.connections += 1
                    
                    # Handle client in new thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_ip),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logging.error(f"Accept error: {e}")
                    
        except Exception as e:
            logging.error(f"❌ Failed to start defense: {e}")
        finally:
            if 'server_socket' in locals():
                server_socket.close()

    def handle_client(self, client_socket, client_ip):
        """Handle client connection and forward to real server"""
        try:
            # Connect to real Modbus server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(5)
            server_socket.connect((self.target_host, self.target_port))
            
            # Forward traffic between client and server
            while self.running:
                try:
                    # Receive from client
                    client_socket.settimeout(1)
                    data = client_socket.recv(4096)
                    
                    if not data:
                        break
                    
                    # Analyze request before forwarding
                    if not self.analyze_request(data, client_ip):
                        self.blocked_attacks += 1
                        self.blocked_ips.add(client_ip)
                        self.log_attack(client_ip, "MALICIOUS_REQUEST", data.hex())
                        
                        if self.attack_prevention_enabled:
                            client_socket.close()
                            server_socket.close()
                            return
                    
                    # Forward to server
                    server_socket.send(data)
                    
                    # Get response from server
                    server_socket.settimeout(2)
                    response = server_socket.recv(4096)
                    
                    if response:
                        # Forward response to client
                        client_socket.send(response)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    break
                    
        except Exception as e:
            logging.debug(f"Client handling error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            try:
                server_socket.close()
            except:
                pass

    def analyze_request(self, data, client_ip):
        """Analyze Modbus request for malicious content"""
        if len(data) < 8:
            self.suspicious_activities += 1
            return False
        
        try:
            # Parse Modbus TCP header
            trans_id, proto_id, length, unit_id = struct.unpack('>HHHB', data[:7])
            
            if proto_id != 0:
                self.suspicious_activities += 1
                return False
            
            if len(data) < length + 6:
                self.suspicious_activities += 1
                return False
            
            # Get function code
            function_code = data[7]
            
            # Check for malicious function codes
            if function_code in self.malicious_function_codes:
                self.log_attack(client_ip, f"MALICIOUS_FUNCTION_CODE_{function_code}", data.hex())
                return False
            
            # Check for rapid requests
            current_time = time.time()
            self.request_timestamps[client_ip].append(current_time)
            
            # Clean old timestamps
            self.request_timestamps[client_ip] = [
                ts for ts in self.request_timestamps[client_ip] 
                if current_time - ts < 5
            ]
            
            # Check rate limit
            if len(self.request_timestamps[client_ip]) > self.rapid_request_threshold:
                self.log_attack(client_ip, "RAPID_REQUEST_ATTACK", f"{len(self.request_timestamps[client_ip])} requests in 5s")
                return False
            
            # Check for suspicious payload patterns
            if self.detect_suspicious_payload(data):
                self.log_attack(client_ip, "SUSPICIOUS_PAYLOAD", data.hex())
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Analysis error: {e}")
            return True

    def detect_suspicious_payload(self, data):
        """Detect suspicious payload patterns"""
        suspicious_patterns = [
            b'\x00' * 20,  # Large null padding
            b'\xff' * 20,  # Large FF padding
            b'\x41' * 50,  # Large A padding (potential buffer overflow)
        ]
        
        for pattern in suspicious_patterns:
            if pattern in data:
                return True
        return False

    def log_attack(self, client_ip, attack_type, details=""):
        """Log attack detection"""
        attack_message = f"🚨 {attack_type} from {client_ip}"
        if details:
            attack_message += f" - {details[:100]}"
        
        logging.error("=" * 70)
        logging.error(attack_message)
        if self.attack_prevention_enabled:
            logging.error(f"🛡️ DEFENSE ACTION: Blocked {client_ip}")
        else:
            logging.error("⚠️ DEFENSE WARNING: Attack detected but prevention is DISABLED")
        logging.error("=" * 70)
        
        # Save to attack log
        self.save_attack_alert(client_ip, attack_type, attack_message)

    def save_attack_alert(self, client_ip, attack_type, message):
        """Save attack alert to file"""
        try:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'source_ip': client_ip,
                'attack_type': attack_type,
                'message': message,
                'defense_prevention': self.attack_prevention_enabled
            }
            
            with open(ALERT_FILE, 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
        except Exception as e:
            logging.error(f"Error saving attack alert: {e}")

    def log_stats(self):
        """Periodically log statistics"""
        while self.running:
            try:
                logging.info(f"🛡️ Defense Stats - Connections: {self.connections}, "
                           f"Blocked Attacks: {self.blocked_attacks}, "
                           f"Suspicious: {self.suspicious_activities}, "
                           f"Blocked IPs: {len(self.blocked_ips)}")
                time.sleep(30)
            except Exception as e:
                logging.error(f"Stats error: {e}")
                time.sleep(30)

    def stop_defense(self):
        """Stop defense system"""
        self.running = False
        logging.info("🛑 Stopping Modbus Defense System")

def main():
    print("=" * 70)
    print("🛡️  REAL Modbus Defense System Starting...")
    print("📡 Listening on port 8502 (transparent proxy)")
    print("🎯 Forwarding to: 127.0.0.1:502")
    print("🔒 Automatic attack blocking: ENABLED")
    print("=" * 70)
    
    # Create defense system that listens on 502 and forwards to 5020
    defense_system = RealModbusDefense(
        listen_port=502,           # Listen on standard Modbus port
        target_host='127.0.0.1',   # Forward to
        target_port=5020           # Different port for real server
    )
    
    try:
        defense_system.start_defense()
    except KeyboardInterrupt:
        defense_system.stop_defense()
        print("\n🛑 Defense system stopped")

if __name__ == "__main__":
    main()