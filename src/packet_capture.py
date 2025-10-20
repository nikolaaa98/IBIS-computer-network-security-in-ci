#!/usr/bin/env python3
"""
Simple packet capture using raw sockets - works on macOS/Linux/Windows
No external dependencies required
"""

import socket
import struct
import time
import logging
import threading
from datetime import datetime
import os
import select

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class SimplePacketCapture:
    def __init__(self, capture_dir="wireshark_captures"):
        self.capture_dir = capture_dir
        self.capture_file = None
        self.running = False
        self.capture_thread = None
        self.packets_captured = 0
        self.socket = None
        
        os.makedirs(capture_dir, exist_ok=True)
        
    def start_capture(self):
        """Start packet capture using raw sockets"""
        if self.running:
            logging.warning("Packet capture already running")
            return True
            
        try:
            # Create capture file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.capture_file = os.path.join(self.capture_dir, f"modbus_traffic_{timestamp}.pcap")
            
            logging.info(f"Starting packet capture using raw sockets")
            logging.info(f"Capture file: {self.capture_file}")
            
            # Create raw socket
            try:
                # Try different socket types for different OS
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                self.socket.settimeout(1)
            except PermissionError:
                logging.error("Permission denied for raw sockets. Running without packet capture.")
                logging.info("Packet capture requires administrator/root privileges")
                return False
            except OSError as e:
                logging.error(f"Raw sockets not available: {e}")
                logging.info("Falling back to TCP socket monitoring")
                # Fallback to regular TCP socket
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(1)
            
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start packet capture: {e}")
            return False
    
    def _capture_loop(self):
        """Main capture loop"""
        try:
            # Write pcap file header
            self._write_pcap_header()
            
            logging.info("Packet capture started. Monitoring Modbus traffic...")
            
            while self.running:
                try:
                    # Try to receive data (non-blocking)
                    ready = select.select([self.socket], [], [], 1.0)
                    if ready[0]:
                        packet, addr = self.socket.recvfrom(65535)
                        self._process_packet(time.time(), packet, addr)
                        self.packets_captured += 1
                        
                        if self.packets_captured % 10 == 0:
                            logging.debug(f"Captured {self.packets_captured} packets...")
                            
                except socket.timeout:
                    continue
                except BlockingIOError:
                    continue
                except Exception as e:
                    if self.running:  # Only log if we're supposed to be running
                        logging.debug(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            logging.error(f"Capture loop error: {e}")
        finally:
            if self.socket:
                self.socket.close()
            self.running = False
            logging.info(f"Packet capture stopped. Total packets: {self.packets_captured}")
    
    def _write_pcap_header(self):
        """Write PCAP file header"""
        try:
            with open(self.capture_file, 'wb') as f:
                # PCAP global header
                f.write(struct.pack('=IHHIIII', 
                    0xa1b2c3d4,  # magic number
                    2,           # version major
                    4,           # version minor
                    0,           # timezone
                    0,           # sigfigs
                    65535,       # snaplen
                    1            # network (Ethernet)
                ))
        except Exception as e:
            logging.error(f"Error writing PCAP header: {e}")
    
    def _process_packet(self, timestamp, packet, addr):
        """Process and save a single packet"""
        try:
            # Simple filter for Modbus traffic (port 502, 1502, 5020, 8502)
            if self._is_modbus_packet(packet):
                # Calculate timestamp for pcap
                ts_sec = int(timestamp)
                ts_usec = int((timestamp - ts_sec) * 1000000)
                
                # Create a simple Ethernet-like frame for pcap format
                # This is a simplified version - real pcap would have proper headers
                pcap_packet = self._create_pcap_packet(packet)
                
                # Write packet to file
                with open(self.capture_file, 'ab') as f:
                    # PCAP packet header
                    f.write(struct.pack('=IIII', 
                        ts_sec,              # timestamp seconds
                        ts_usec,             # timestamp microseconds
                        len(pcap_packet),    # captured length
                        len(pcap_packet)     # original length
                    ))
                    # Packet data
                    f.write(pcap_packet)
                    
        except Exception as e:
            logging.debug(f"Error processing packet: {e}")
    
    def _is_modbus_packet(self, packet):
        """Check if packet contains Modbus traffic"""
        try:
            if len(packet) < 20:  # Minimum IP header size
                return False
            
            # Parse IP header
            ip_header = packet[:20]
            ip_proto = ip_header[9]
            
            # Check for TCP
            if ip_proto != 6:
                return False
            
            # Parse TCP header
            tcp_header_start = 20
            if len(packet) < tcp_header_start + 20:
                return False
            
            src_port = struct.unpack('!H', packet[tcp_header_start:tcp_header_start+2])[0]
            dst_port = struct.unpack('!H', packet[tcp_header_start+2:tcp_header_start+4])[0]
            
            # Check for Modbus ports
            modbus_ports = {502, 1502, 5020, 8502}
            return src_port in modbus_ports or dst_port in modbus_ports
            
        except:
            return False
    
    def _create_pcap_packet(self, ip_packet):
        """Create a simplified Ethernet frame for pcap format"""
        try:
            # Create a simple Ethernet frame (14 bytes) + IP packet
            # This is a simplified version for demonstration
            eth_frame = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00'  # Fake Ethernet header
            return eth_frame + ip_packet
        except:
            return ip_packet  # Fallback to just the IP packet
    
    def stop_capture(self):
        """Stop packet capture"""
        if self.running:
            logging.info("Stopping packet capture...")
            self.running = False
            if self.capture_thread:
                self.capture_thread.join(timeout=5)
            if self.socket:
                self.socket.close()
            logging.info(f"Packet capture stopped. Total packets: {self.packets_captured}")
            return True
        return False
    
    def get_stats(self):
        """Get capture statistics"""
        return {
            'running': self.running,
            'packets_captured': self.packets_captured,
            'capture_file': self.capture_file
        }

# Alternative: TCP connection monitoring (works without root privileges)
class TCPConnectionMonitor:
    def __init__(self, capture_dir="wireshark_captures"):
        self.capture_dir = capture_dir
        self.capture_file = None
        self.running = False
        self.monitor_thread = None
        self.connections_monitored = 0
        
        os.makedirs(capture_dir, exist_ok=True)
    
    def start_monitoring(self):
        """Start TCP connection monitoring"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.capture_file = os.path.join(self.capture_dir, f"tcp_connections_{timestamp}.log")
            
            logging.info("Starting TCP connection monitoring")
            logging.info(f"Log file: {self.capture_file}")
            
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            return True
        except Exception as e:
            logging.error(f"Failed to start TCP monitoring: {e}")
            return False
    
    def _monitor_loop(self):
        """Monitor TCP connections"""
        try:
            with open(self.capture_file, 'w') as f:
                f.write("TCP Connection Monitor - Modbus Traffic\n")
                f.write("=" * 50 + "\n")
                f.write(f"Started: {datetime.now()}\n\n")
            
            while self.running:
                try:
                    # Monitor network connections using netstat (cross-platform)
                    self._log_connections()
                    time.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    logging.debug(f"Monitoring error: {e}")
                    time.sleep(10)
                    
        except Exception as e:
            logging.error(f"Monitor loop error: {e}")
        finally:
            self.running = False
    
    def _log_connections(self):
        """Log current TCP connections"""
        try:
            import subprocess
            import sys
            
            if sys.platform == "win32":
                # Windows
                result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=10)
            else:
                # Unix/Linux/macOS
                result = subprocess.run(['netstat', '-an', '-p', 'tcp'], capture_output=True, text=True, timeout=10)
            
            modbus_connections = []
            for line in result.stdout.split('\n'):
                if any(port in line for port in [':502 ', ':1502 ', ':5020 ', ':8502 ']):
                    modbus_connections.append(line.strip())
            
            if modbus_connections:
                with open(self.capture_file, 'a') as f:
                    f.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] Modbus connections:\n")
                    for conn in modbus_connections:
                        f.write(f"  {conn}\n")
                    self.connections_monitored += len(modbus_connections)
                    
        except Exception as e:
            logging.debug(f"Connection logging error: {e}")
    
    def stop_monitoring(self):
        """Stop TCP monitoring"""
        if self.running:
            logging.info("Stopping TCP connection monitoring...")
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            # Write summary
            try:
                with open(self.capture_file, 'a') as f:
                    f.write(f"\n\nMonitoring stopped: {datetime.now()}\n")
                    f.write(f"Total connections monitored: {self.connections_monitored}\n")
            except:
                pass
            
            logging.info(f"TCP monitoring stopped. Connections: {self.connections_monitored}")
            return True
        return False
    
    def get_stats(self):
        return {
            'running': self.running,
            'connections_monitored': self.connections_monitored,
            'capture_file': self.capture_file
        }

# Global instances
_packet_capture = None
_tcp_monitor = None

def start_global_capture(capture_dir="wireshark_captures"):
    """Start global packet capture (try raw sockets, fallback to TCP monitoring)"""
    global _packet_capture, _tcp_monitor
    
    # First try packet capture with raw sockets
    _packet_capture = SimplePacketCapture(capture_dir)
    if _packet_capture.start_capture():
        logging.info("Packet capture started successfully")
        return True
    else:
        logging.info("Falling back to TCP connection monitoring")
        _tcp_monitor = TCPConnectionMonitor(capture_dir)
        return _tcp_monitor.start_monitoring()

def stop_global_capture():
    """Stop global capture/monitoring"""
    global _packet_capture, _tcp_monitor
    
    success = False
    if _packet_capture:
        success = _packet_capture.stop_capture()
        _packet_capture = None
    
    if _tcp_monitor:
        success = _tcp_monitor.stop_monitoring() or success
        _tcp_monitor = None
    
    return success

def get_capture_stats():
    """Get global capture statistics"""
    global _packet_capture, _tcp_monitor
    
    if _packet_capture:
        return _packet_capture.get_stats()
    elif _tcp_monitor:
        return _tcp_monitor.get_stats()
    else:
        return {'running': False, 'packets_captured': 0, 'connections_monitored': 0}

if __name__ == "__main__":
    # Test the packet capture
    print("Testing Packet Capture...")
    
    print("1. Testing raw socket capture (requires root)...")
    capture = SimplePacketCapture()
    try:
        print("Starting capture for 5 seconds...")
        if capture.start_capture():
            time.sleep(5)
        else:
            print("Raw socket capture failed, trying TCP monitoring...")
            monitor = TCPConnectionMonitor()
            monitor.start_monitoring()
            time.sleep(5)
            monitor.stop_monitoring()
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop_capture()
        stats = capture.get_stats()
        print(f"Capture completed: {stats}")