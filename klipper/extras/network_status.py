# Klipper extra: expose host network info to display menus and macros.
# Original: https://github.com/JeremyRuhland/klipper_network_status
# (maintained fork: https://github.com/goopypanther/klipper_network_status)
import logging
import os


class network_status:
    def __init__(self, config):
        self.interval = config.getint('interval', 60, minval=10)
        self.ethip = "N/A"
        self.wifiip = "N/A"
        self.wifissid = "N/A"
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

            self.mdns = os.popen('hostname').read().strip() + '.local'

        return {
            'ethip': self.ethip,
            'wifiip': self.wifiip,
            'wifissid': self.wifissid,
            'mdns': self.mdns,
        }


def load_config(config):
    return network_status(config)
