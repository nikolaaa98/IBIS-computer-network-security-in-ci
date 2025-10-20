from flask import Flask, render_template, request, jsonify
import logging
import json
import os
import time
import subprocess
import psutil
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT, "templates")
CONTROL_FILE = os.path.join(ROOT, "control.json")
LOG_DIR = os.path.join(ROOT, "logs")

app = Flask(__name__, template_folder=TEMPLATES_DIR)

active_attacks = []
defense_enabled = False
defense_process = None

def read_control():
    if not os.path.exists(CONTROL_FILE):
        return {"manipulate": True}
    try:
        with open(CONTROL_FILE, "r") as f:
            return json.load(f)
    except:
        return {"manipulate": True}

def write_control(manipulate):
    data = {"manipulate": bool(manipulate), "ts": int(time.time())}
    try:
        with open(CONTROL_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

def read_all_values():
    """Čita vrednosti SA SERVERA i SA PROXY-ja sa DELAY"""
    server_values = {}
    client_values = {}
    
    try:
        # Čitanje direktno sa servera (prave vrednosti)
        server_client = ModbusClient(host='127.0.0.1', port=5020, timeout=1)
        if server_client.open():
            server_regs = server_client.read_holding_registers(0, 3)
            server_client.close()
            if server_regs and len(server_regs) >= 3:
                server_values = {
                    'temperature': server_regs[0],
                    'humidity': server_regs[1],
                    'pressure': server_regs[2],
                    'source': 'SERVER'
                }
    except Exception as e:
        logging.error(f"Error reading server values: {e}")
        pass
    
    # DELAY između čitanja servera i klijenta
    time.sleep(0.1)
    
    try:
        # Čitanje preko proxy-ja (ono što klijent vidi)
        proxy_client = ModbusClient(host='127.0.0.1', port=1502, timeout=1)
        if proxy_client.open():
            client_regs = proxy_client.read_holding_registers(0, 3)
            proxy_client.close()
            if client_regs and len(client_regs) >= 3:
                client_values = {
                    'temperature': client_regs[0],
                    'humidity': client_regs[1],
                    'pressure': client_regs[2],
                    'source': 'CLIENT'
                }
    except Exception as e:
        logging.error(f"Error reading client values: {e}")
        pass
    
    # Ako nema podataka, vrati default
    if not server_values:
        server_values = {'temperature': 25, 'humidity': 50, 'pressure': 1013, 'source': 'SERVER'}
    if not client_values:
        client_values = {'temperature': 25, 'humidity': 50, 'pressure': 1013, 'source': 'CLIENT'}
    
    return {
        'server': server_values,
        'client': client_values,
        'manipulation_active': read_control().get('manipulate', True)
    }

def detect_manipulation(server_vals, client_vals):
    """Poboljšana detekcija manipulacije"""
    if not server_vals or not client_vals:
        return False
    
    control = read_control()
    manipulation_enabled = control.get('manipulate', False)
    
    # Ako je manipulacija isključena, nemoj detektovati
    if not manipulation_enabled:
        return False
    
    # Proveri da li su vrednosti uopšte različite
    temp_diff = abs(server_vals.get('temperature', 0) - client_vals.get('temperature', 0))
    humidity_diff = abs(server_vals.get('humidity', 0) - client_vals.get('humidity', 0))
    pressure_diff = abs(server_vals.get('pressure', 0) - client_vals.get('pressure', 0))
    
    # MITM pattern: +10°C, +5%, +20hPa
    expected_manipulation = (
        temp_diff >= 8 and temp_diff <= 12 and      # ~10°C
        humidity_diff >= 3 and humidity_diff <= 7 and # ~5%
        pressure_diff >= 15 and pressure_diff <= 25  # ~20hPa
    )
    
    # Ili bilo koja velika razlika
    large_differences = (
        temp_diff >= 15 or
        humidity_diff >= 20 or  
        pressure_diff >= 50 or
        temp_diff < 0 or        # Negativne temperature
        humidity_diff < 0 or    # Negativna vlažnost
        pressure_diff < 0       # Negativan pritisak
    )
    
    return expected_manipulation or large_differences

def read_logs(n=50):
    files = ["modbus_server.log", "modbus_proxy.log", "modbus_client.log", "attack.log", "ui_server.log", "defense.log"]
    lines = []
    
    for fn in files:
        path = os.path.join(LOG_DIR, fn)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.readlines()
                
                colors = {
                    "modbus_server": "#4CAF50",
                    "modbus_proxy": "#FF9800", 
                    "modbus_client": "#2196F3",
                    "attack": "#F44336",
                    "ui_server": "#9C27B0",
                    "defense": "#FFC107"
                }
                
                icons = {
                    "modbus_server": "🔧",
                    "modbus_proxy": "🔄",
                    "modbus_client": "📊",
                    "attack": "🚨",
                    "ui_server": "🌐",
                    "defense": "🛡️"
                }
                
                prefix = fn.replace(".log", "")
                icon = icons.get(prefix, "📝")
                color = colors.get(prefix, "#666666")
                
                for l in content[-n:]:
                    if l.strip():
                        formatted_line = f'<span style="color: {color}; font-weight: bold;">{icon} [{prefix.upper()}]</span> {l.strip()}'
                        lines.append(formatted_line)
            except Exception as e:
                logging.error(f"Error reading log {fn}: {e}")
                pass
    
    lines.sort(key=lambda x: x.split(']')[0] if ']' in x else x)
    return lines[-n:]

def read_attack_alerts():
    alerts = []
    path = os.path.join(LOG_DIR, "attack.log")
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f.readlines()[-20:]:
                    line = line.strip()
                    if line:
                        if line.startswith('{'):
                            try:
                                alert_data = json.loads(line)
                                alerts.append(alert_data)
                            except:
                                alerts.append({'message': line, 'timestamp': datetime.now().isoformat()})
                        else:
                            alerts.append({'message': line, 'timestamp': datetime.now().isoformat()})
        except Exception as e:
            logging.error(f"Error reading attack alerts: {e}")
            pass
    
    return alerts[-10:]

def log_attack(attack_type, message):
    try:
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'type': attack_type,
            'message': message,
            'source': 'UI_SYSTEM'
        }
        
        with open(os.path.join(LOG_DIR, "attack.log"), "a") as f:
            f.write(json.dumps(alert_data) + '\n')
    except Exception as e:
        logging.error(f"Error logging attack: {e}")
        pass

def is_process_running(pid_file):
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        return psutil.pid_exists(pid)
    except:
        return False

def start_defense_system():
    """Pokreće defense sistem na portu 8502"""
    global defense_process, defense_enabled
    
    try:
        # Pokreni defense sistem kao poseban proces
        defense_process = subprocess.Popen([
            'python3', 'src/defense_module.py'
        ], cwd=ROOT)
        
        defense_enabled = True
        log_attack("DEFENSE", "Defense system started on port 8502")
        logging.info("✅ Defense system started on port 8502")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error starting defense system: {e}")
        return False

def stop_defense_system():
    """Zaustavlja defense sistem"""
    global defense_process, defense_enabled
    
    try:
        if defense_process:
            defense_process.terminate()
            defense_process.wait(timeout=5)
        
        defense_enabled = False
        defense_process = None
        log_attack("DEFENSE", "Defense system stopped")
        logging.info("🛑 Defense system stopped")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error stopping defense system: {e}")
        return False

def start_real_attack(attack_type):
    """Pokreće stvarni napad u pozadini - POBOLJŠANA VERZIJA"""
    try:
        if attack_type == 'dos':
            # Pokreni REAL DoS napad u pozadini
            subprocess.Popen([
                'python3', 'src/modbus_dos_attack.py', 
                '--target', '127.0.0.1',
                '--port', '502',
                '--attack', 'malformed',
                '--threads', '5',
                '--duration', '25',
                '--auto-confirm'
            ], cwd=ROOT)
            
        elif attack_type == 'recon':
            # Pokreni Recon napad u pozadini
            subprocess.Popen([
                'python3', 'src/modbus_recon_inject.py',
                '--target', '127.0.0.1',
                '--mode', 'scan',
                '--auto-confirm'
            ], cwd=ROOT)
            
        elif attack_type == 'inject':
            # Pokreni Injection napad u pozadini
            subprocess.Popen([
                'python3', 'src/modbus_recon_inject.py',
                '--target', '127.0.0.1', 
                '--mode', 'inject',
                '--auto-confirm'
            ], cwd=ROOT)
            
        elif attack_type == 'all':
            # Pokreni kombinovani REAL napad
            subprocess.Popen([
                'python3', 'src/modbus_dos_attack.py',
                '--target', '127.0.0.1',
                '--port', '502', 
                '--attack', 'all',
                '--threads', '8',
                '--duration', '30',
                '--auto-confirm'
            ], cwd=ROOT)
            
        logging.info(f"✅ Started REAL {attack_type} attack")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error starting real attack: {e}")
        return False

# === Rute ===
@app.route("/")
def index():
    control = read_control()
    logs = read_logs(30)
    values = read_all_values()
    attack_alerts = read_attack_alerts()
    
    return render_template(
        "index.html",
        control=control,
        logs=logs,
        defense_enabled=defense_enabled,
        values=values,
        proxy_host="127.0.0.1",
        proxy_port=1502,
        attack_alerts=attack_alerts
    )

@app.route("/toggle", methods=["POST"])
def toggle():
    """Menja stanje manipulatora (ON/OFF)"""
    control = read_control()
    new_state = not control.get("manipulate", True)
    write_control(new_state)
    
    status = "ENABLED" if new_state else "DISABLED"
    log_attack("MANIPULATION", f"Data manipulation {status}")
    
    return jsonify({"success": True, "manipulate": new_state})

@app.route("/write", methods=["POST"])
def write_values():
    """Ručno upisuje vrednosti preko proxy-ja"""
    try:
        temp = request.form.get('temp')
        humidity = request.form.get('humidity')
        pressure = request.form.get('pressure')
        host = request.form.get('host', '127.0.0.1')
        port = int(request.form.get('port', 1502))
        
        from mitm_modbus_manipulator import write_register
        success = write_register(host, port, temp, humidity, pressure)
        
        if success:
            log_attack("MANUAL_WRITE", f"Written values - Temp: {temp}, Humidity: {humidity}, Pressure: {pressure}")
            return jsonify({"success": True, "message": "Values written successfully"})
        else:
            return jsonify({"success": False, "message": "Error writing values"})
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route("/api/values")
def api_values():
    values = read_all_values()
    control = read_control()
    
    # Detektuj manipulaciju sa tolerancijom
    manipulation_detected = detect_manipulation(values['server'], values['client'])
    
    return jsonify({
        "values": values,
        "control": control,
        "manipulation_detected": manipulation_detected
    })

@app.route("/api/status")
def api_status():
    # Proveri status svih servisa
    server_running = is_process_running('pids/modbus_server.pid')
    client_running = is_process_running('pids/modbus_client.pid') 
    proxy_running = is_process_running('pids/modbus_proxy.pid')
    
    attacks_info = []
    for attack in active_attacks:
        elapsed = time.time() - attack['start_time']
        attacks_info.append({
            'type': attack['type'],
            'duration': f"{elapsed:.1f}s",
            'active': elapsed < 30
        })
    
    # Proveri defense status
    defense_running = defense_enabled and (defense_process and defense_process.poll() is None)
    
    return jsonify({
        "server": server_running,
        "client": client_running,
        "proxy": proxy_running,
        "defense": defense_running,
        "attacks": attacks_info
    })

@app.route("/api/logs")
def api_logs():
    logs = read_logs(30)
    return jsonify({"logs": logs})

@app.route("/api/attack-alerts")
def api_attack_alerts():
    alerts = read_attack_alerts()
    return jsonify({"alerts": alerts})

@app.route("/api/start-attack", methods=["POST"])
def api_start_attack():
    data = request.get_json()
    attack_type = data.get("type", "recon")
    
    # Zaustavi prethodne napade istog tipa
    active_attacks[:] = [a for a in active_attacks if a['type'] != attack_type]
    
    # Dodaj novi napad
    attack_info = {
        "type": attack_type, 
        "start_time": time.time(),
        "description": get_attack_description(attack_type)
    }
    active_attacks.append(attack_info)
    
    log_attack(attack_type.upper(), f"Starting REAL {attack_type} attack")
    
    # Pokreni STVARNI napad u pozadini
    success = start_real_attack(attack_type)
    
    if success:
        return jsonify({
            "success": True, 
            "message": f"REAL {attack_type} attack started",
            "attack": attack_info
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Failed to start {attack_type} attack"
        })

@app.route("/api/stop-attacks", methods=["POST"])
def api_stop_attacks():
    """Zaustavlja sve napade"""
    stopped_count = len(active_attacks)
    active_attacks.clear()
    
    # Ubij sve napad procese
    try:
        subprocess.run(['pkill', '-f', 'modbus_dos_attack.py'], check=False)
        subprocess.run(['pkill', '-f', 'modbus_recon_inject.py'], check=False)
        logging.info("✅ Stopped all attack processes")
    except:
        pass
    
    log_attack("SYSTEM", f"All attacks stopped ({stopped_count} total)")
    
    return jsonify({
        "success": True, 
        "message": f"All attacks stopped ({stopped_count} total)"
    })

@app.route("/api/toggle-defense", methods=["POST"])
def api_toggle_defense():
    global defense_enabled
    
    if defense_enabled:
        success = stop_defense_system()
        message = "Defense system stopped"
    else:
        success = start_defense_system()
        message = "Defense system started"
    
    if success:
        return jsonify({
            "success": True, 
            "message": message,
            "defense_enabled": defense_enabled
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to toggle defense system"
        })

@app.route("/api/start-services", methods=["POST"])
def api_start_services():
    """Pokreće sve servise"""
    try:
        # Pokreni server
        subprocess.Popen(['python3', 'src/modbus_server.py'], cwd=ROOT)
        time.sleep(1)
        
        # Pokreni proxy
        subprocess.Popen(['python3', 'src/mitm_proxy.py'], cwd=ROOT)
        time.sleep(1)
        
        # Pokreni client
        subprocess.Popen(['python3', 'src/modbus_client.py'], cwd=ROOT)
        
        log_attack("SYSTEM", "All services started")
        logging.info("✅ All services started")
        return jsonify({"success": True, "message": "Services started successfully"})
    except Exception as e:
        logging.error(f"❌ Error starting services: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route("/api/stop-services", methods=["POST"])
def api_stop_services():
    """Zaustavlja sve servise"""
    try:
        # Zaustavi sve procese
        subprocess.run(['pkill', '-f', 'modbus_server.py'], check=False)
        subprocess.run(['pkill', '-f', 'mitm_proxy.py'], check=False)
        subprocess.run(['pkill', '-f', 'modbus_client.py'], check=False)
        
        log_attack("SYSTEM", "All services stopped")
        logging.info("🛑 All services stopped")
        return jsonify({"success": True, "message": "Services stopped successfully"})
    except Exception as e:
        logging.error(f"❌ Error stopping services: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route("/api/clear-logs", methods=["POST"])
def api_clear_logs():
    """Briše log fajlove"""
    try:
        files = ["modbus_server.log", "modbus_proxy.log", "modbus_client.log", "attack.log", "ui_server.log", "defense.log"]
        for fn in files:
            path = os.path.join(LOG_DIR, fn)
            if os.path.exists(path):
                open(path, 'w').close()
        
        log_attack("SYSTEM", "Logs cleared")
        logging.info("🗑️ Logs cleared")
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"❌ Error clearing logs: {e}")
        return jsonify({"success": False, "error": str(e)})

def get_attack_description(attack_type):
    """Vraća opis napada za UI"""
    descriptions = {
        "recon": "Network scanning and reconnaissance - triggers defense with suspicious scans",
        "dos": "Denial of Service attack - flooding with malicious packets", 
        "inject": "Command injection and malicious writes - tries dangerous operations",
        "all": "Full attack chain (recon + dos + inject) - maximum defense trigger"
    }
    return descriptions.get(attack_type, "Unknown attack type")

if __name__ == "__main__":
    # Kreiraj direktorijume
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "pids"), exist_ok=True)
    
    # Uveri se da control.json postoji
    if not os.path.exists(CONTROL_FILE):
        write_control(True)

    print("=" * 60)
    print("🌐 IBIS Industrial Control System Security Demo")
    print("📊 Flask UI Server Starting...")
    print("📍 http://127.0.0.1:8080")
    print("=" * 60)
    
    try:
        app.run(host="0.0.0.0", port=8080, debug=False)
    except Exception as e:
        print(f"❌ Greška pri pokretanju Flask servera: {e}")
        raise