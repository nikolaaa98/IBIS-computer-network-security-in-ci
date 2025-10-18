# mitm_modbus_manipulator.py
# Simple script that connects as a Modbus client and writes a value to register 0.
# Use only in test environments where you control the server.
from pyModbusTCP.client import ModbusClient
import argparse, logging, time

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def write_register(host, port, temp=None, humidity=None, pressure=None):
    client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)
    logging.info('Connecting to Modbus server %s:%s', host, port)
    if not client.open():
        logging.error('Failed to connect to server')
        return
    try:
        if temp is not None:
            if not (0 <= temp <= 100):  # Validate temperature range
                logging.error('Temperature must be between 0 and 100 °C')
                return
            ok = client.write_single_register(0, int(temp))
            if ok:
                logging.info('Wrote temperature %s °C to register 0', temp)
            else:
                logging.error('Failed to write temperature to register 0')

        if humidity is not None:
            if not (0 <= humidity <= 100):  # Validate humidity range
                logging.error('Humidity must be between 0 and 100%')
                return
            ok = client.write_single_register(1, int(humidity))
            if ok:
                logging.info('Wrote humidity %s%% to register 1', humidity)
            else:
                logging.error('Failed to write humidity to register 1')

        if pressure is not None:
            if not (900 <= pressure <= 1100):  # Validate pressure range
                logging.error('Pressure must be between 900 and 1100 hPa')
                return
            ok = client.write_single_register(2, int(pressure))
            if ok:
                logging.info('Wrote pressure %s hPa to register 2', pressure)
            else:
                logging.error('Failed to write pressure to register 2')

    except Exception as e:
        logging.exception('Error writing register: %s', e)
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Write one register on a Modbus server (test only)')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=502, help='Server port')
    parser.add_argument('--temp', type=int, help='Temperature value to write to register 0 (°C)')
    parser.add_argument('--humidity', type=int, help='Humidity value to write to register 1 (%)')
    parser.add_argument('--pressure', type=int, help='Pressure value to write to register 2 (hPa)')
    args = parser.parse_args()
    # if not any([args.temp is not None, args.humidity is not None, args.pressure is not None]):
    #     parser.error('At least one of --temp, --humidity, or --pressure must be specified')

    write_register(args.host, args.port, args.temp, args.humidity, args.pressure)
