from pyModbusTCP.server import ModbusServer, DataBank
import time, random, logging, argparse

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def run_server(host='0.0.0.0', port=5020, interval=3):
    server = ModbusServer(host=host, port=port, no_block=True)
    try:
        server.start()
        logging.info(f'Modbus server started on {host}:{port}')
        while True:
            temperature = random.randint(18, 35)
            humidity = random.randint(40, 80)
            pressure = random.randint(1000, 1025)
            DataBank.set_words(0, [temperature, humidity, pressure])
            logging.info(f'[SERVER] Temp: {temperature}°C, Humidity: {humidity}%, Pressure: {pressure}hPa')
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info('Stopping server...')
        server.stop()
    except Exception as e:
        logging.error(f'Server error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=502)
    parser.add_argument('--interval', type=float, default=3.0)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, interval=args.interval)