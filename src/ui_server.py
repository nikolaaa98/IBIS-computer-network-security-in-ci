# src/ui_server.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pyModbusTCP.client import ModbusClient
import subprocess, logging, json, os, argparse, time

# === Konfiguracija logovanja ===
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# === Putanje ===
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT, "templates")
CONTROL_FILE = os.path.join(ROOT, "control.json")
LOG_DIR = os.path.join(ROOT, "logs")
MANIPULATOR_SCRIPT = os.path.join(ROOT, "src", "mitm_modbus_manipulator.py")

# === Flask aplikacija ===
app = Flask(__name__, template_folder=TEMPLATES_DIR)


# === Funkcije pomoćne ===
def read_register(proxy_host, proxy_port):
    """Čita Modbus registar preko proxy-ja."""
    client = ModbusClient(host=proxy_host, port=proxy_port, auto_open=True, auto_close=True)
    try:
        if not client.open():
            return None
        regs = client.read_holding_registers(0, 1)
        return regs[0] if regs else None
    except Exception as e:
        logging.error(f"Greška pri čitanju registra: {e}")
        return None


def read_logs(n=200):
    """Vraća poslednjih n linija iz svih log fajlova."""
    files = ["modbus_server.log", "modbus_proxy.log", "modbus_client.log"]
    lines = []
    for fn in files:
        path = os.path.join(LOG_DIR, fn)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.readlines()
                prefix = fn.replace(".log", "")
                for l in content[-n:]:
                    lines.append(f"[{prefix}] {l.rstrip()}")
            except Exception as e:
                logging.warning(f"Ne mogu da pročitam {fn}: {e}")
    return lines[-n:]


def write_control(manipulate: bool):
    """Piše trenutni status manipulacije u control.json"""
    data = {"manipulate": bool(manipulate), "ts": int(time.time())}
    with open(CONTROL_FILE, "w") as f:
        json.dump(data, f)


def read_control():
    """Čita trenutni status manipulacije iz control.json"""
    if not os.path.exists(CONTROL_FILE):
        return {"manipulate": True}
    try:
        with open(CONTROL_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"manipulate": True}


# === Rute ===
@app.route("/")
def index():
    proxy_host = request.args.get("proxy_host", app.config["PROXY_HOST"])
    proxy_port = int(request.args.get("proxy_port", app.config["PROXY_PORT"]))
    value = read_register(proxy_host, proxy_port)
    control = read_control()
    logs = read_logs(200)
    return render_template(
        "index.html",
        value=value,
        control=control,
        logs=logs,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
    )


@app.route("/toggle", methods=["POST"])
def toggle():
    """Menja stanje manipulatora (ON/OFF)"""
    control = read_control()
    new_state = not control.get("manipulate", True)
    write_control(new_state)
    return redirect(url_for("index"))


@app.route("/write", methods=["POST"])
def write():
    """Pokreće mitm_modbus_manipulator.py da upiše novu vrednost"""
    host = request.form.get("host", app.config["PROXY_READ_HOST"])
    port = int(request.form.get("port", app.config["PROXY_READ_PORT"]))
    value = int(request.form.get("value", 0))
    try:
        subprocess.check_call(
            [
                app.config["PYTHON_BIN"],
                MANIPULATOR_SCRIPT,
                "--host", str(host),
                "--port", str(port),
                "--value", str(value),
            ]
        )
    except subprocess.CalledProcessError as e:
        logging.exception(f"Manipulator nije uspeo: {e}")
    return redirect(url_for("index"))


@app.route("/api/value")
def api_value():
    """API endpoint koji vraća trenutnu vrednost registra"""
    proxy_host = request.args.get("proxy_host", app.config["PROXY_HOST"])
    proxy_port = int(request.args.get("proxy_port", app.config["PROXY_PORT"]))
    v = read_register(proxy_host, proxy_port)
    return jsonify({"value": v})


# === Glavni ulaz ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy-host", default="127.0.0.1")
    parser.add_argument("--proxy-port", type=int, default=1502)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    # Podesi konfiguraciju aplikacije
    app.config["PROXY_HOST"] = args.proxy_host
    app.config["PROXY_PORT"] = args.proxy_port
    app.config["PROXY_READ_HOST"] = args.proxy_host
    app.config["PROXY_READ_PORT"] = args.proxy_port
    app.config["PYTHON_BIN"] = (
        os.path.join(ROOT, ".venv", "bin", "python")
        if os.path.exists(os.path.join(ROOT, ".venv"))
        else "python3"
    )

    # Uveri se da control.json postoji
    if not os.path.exists(CONTROL_FILE):
        write_control(True)

    logging.info(f"Pokrećem Flask UI na http://127.0.0.1:{args.port}")
    app.run(host=args.bind, port=args.port, debug=False)
