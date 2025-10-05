# defense_module.py
# Simple ARP anomaly detector - listens for gratuitous ARP or MAC changes
from scapy.all import sniff, ARP
import logging, argparse

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
observed = {}

def arp_monitor(pkt):
    if ARP in pkt and pkt[ARP].op in (1, 2):  # who-has or is-at
        ip = pkt[ARP].psrc
        mac = pkt[ARP].hwsrc
        if ip in observed and observed[ip] != mac:
            logging.warning(f'ARP anomaly: IP {ip} changed MAC {observed[ip]} -> {mac}')
        else:
            observed[ip] = mac
            logging.info(f'Observed ARP: {ip} => {mac}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ARP anomaly detector (run on networks you control)')
    parser.add_argument('--iface', default=None, help='Interface to sniff (default: all)')
    args = parser.parse_args()
    logging.info('Starting ARP monitor (CTRL+C to stop). Run only in networks you control.')
    try:
        sniff(prn=arp_monitor, store=0, iface=args.iface)
    except KeyboardInterrupt:
        logging.info('Stopping monitor')
