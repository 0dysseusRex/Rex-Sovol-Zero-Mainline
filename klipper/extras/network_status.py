# Klipper extra: expose host network info to display menus and macros.
# Original: https://github.com/JeremyRuhland/klipper_network_status
# (maintained fork: https://github.com/goopypanther/klipper_network_status)
import logging
import os


def _read_wifi_signal():
    """Return (rssi_dbm, quality_percent, bar_string) from /proc/net/wireless."""
    try:
        with open('/proc/net/wireless', encoding='ascii') as wireless:
            for line in wireless:
                line = line.lstrip()
                if not line.startswith('wlan0:'):
                    continue
                parts = line.split()
                quality = float(parts[2].rstrip('.'))
                rssi = int(float(parts[3].rstrip('.')))
                pct = max(0, min(100, round(quality * 100 / 70)))
                filled = round(pct * 8 / 100)
                bars = '#' * filled + '-' * (8 - filled)
                return rssi, pct, bars
    except (IndexError, OSError, ValueError):
        pass
    return None, None, "N/A"


class network_status:
    def __init__(self, config):
        self.interval = config.getint('interval', 60, minval=10)
        self.ethip = "N/A"
        self.wifiip = "N/A"
        self.wifissid = "N/A"
        self.wifisignal = "N/A"
        self.wifiquality = -1
        self.wifibars = "N/A"
        self.mdns = "N/A"
        self.last_eventtime = 0

    def get_status(self, eventtime):
        if eventtime - self.last_eventtime > self.interval:
            self.last_eventtime = eventtime
            logging.info("network_status refresh at %.0f", eventtime)
            try:
                self.ethip = os.popen('ip addr show eth0').read().split("inet ")[1].split("/")[0]
            except IndexError:
                self.ethip = "N/A"

            try:
                self.wifiip = os.popen('ip addr show wlan0').read().split("inet ")[1].split("/")[0]
                self.wifissid = os.popen('iwgetid -r').read().strip()
            except IndexError:
                self.wifiip = "N/A"
                self.wifissid = "N/A"

            rssi, pct, bars = _read_wifi_signal()
            if rssi is None:
                self.wifisignal = "N/A"
                self.wifiquality = -1
                self.wifibars = "N/A"
            else:
                self.wifisignal = str(rssi)
                self.wifiquality = pct
                self.wifibars = bars

            self.mdns = os.popen('hostname').read().strip() + '.local'

        return {
            'ethip': self.ethip,
            'wifiip': self.wifiip,
            'wifissid': self.wifissid,
            'wifisignal': self.wifisignal,
            'wifiquality': self.wifiquality,
            'wifibars': self.wifibars,
            'mdns': self.mdns,
        }


def load_config(config):
    return network_status(config)
