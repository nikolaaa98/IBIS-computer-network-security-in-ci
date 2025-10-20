# mitm_modbus_manipulator.py
# Simple script that connects as a Modbus client and writes values to registers.
# Use only in test environments where you control the server.
from pyModbusTCP.client import ModbusClient
import argparse, logging, time

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def write_register(host, port, temp=None, humidity=None, pressure=None):
    client = ModbusClient(host=host, port=port, auto_open=True, auto_close=True)
    logging.info('Connecting to Modbus server %s:%s', host, port)
    if not client.open():
        logging.error('Failed to connect to server')
        return False
    
    success = True
    try:
        if temp is not None and temp != '':
            temp_int = int(temp)
            if not (0 <= temp_int <= 100):  # Validate temperature range
                logging.error('Temperature must be between 0 and 100 °C')
                success = False
            else:
                ok = client.write_single_register(0, temp_int)
                if ok:
                    logging.info('Wrote temperature %s °C to register 0', temp_int)
                else:
                    logging.error('Failed to write temperature to register 0')
                    success = False

        if humidity is not None and humidity != '':
            humidity_int = int(humidity)
            if not (0 <= humidity_int <= 100): 
                logging.error('Humidity must be between 0 and 100%')
                success = False
            else:
                ok = client.write_single_register(1, humidity_int)
                if ok:
                    logging.info('Wrote humidity %s%% to register 1', humidity_int)
                else:
                    logging.error('Failed to write humidity to register 1')
                    success = False

        if pressure is not None and pressure != '':
            pressure_int = int(pressure)
            if not (900 <= pressure_int <= 1100):
                logging.error('Pressure must be between 900 and 1100 hPa')
                success = False
            else:
                ok = client.write_single_register(2, pressure_int)
                if ok:
                    logging.info('Wrote pressure %s hPa to register 2', pressure_int)
                else:
                    logging.error('Failed to write pressure to register 2')
                    success = False

    except ValueError as e:
        logging.error('Invalid value provided: %s', e)
        success = False
    except Exception as e:
        logging.exception('Error writing register: %s', e)
        success = False
    finally:
        try:
            client.close()
        except:
            pass
    
    return success

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Write registers on a Modbus server (test only)')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=502, help='Server port')
    parser.add_argument('--temp', type=int, help='Temperature value to write to register 0 (°C)')
    parser.add_argument('--humidity', type=int, help='Humidity value to write to register 1 (%)')
    parser.add_argument('--pressure', type=int, help='Pressure value to write to register 2 (hPa)')
    args = parser.parse_args()

    write_register(args.host, args.port, args.temp, args.humidity, args.pressure)