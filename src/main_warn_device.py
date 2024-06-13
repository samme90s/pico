import utime

from config import ADA_USER
from scripts import MQTT, WIFI, LEDCallbackStrategy


class System:
    def __init__(self):
        self.wlan = WIFI(timeout=30)
        self.mqtt = MQTT()

        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.wlan.connect()
        self.mqtt.connect()
        self.mqtt.subscribe(self.f_temperature, LEDCallbackStrategy())

    def run(self, interval=1):
        try:
            if interval < 1:
                raise ValueError("Interval must positive")

            while True:
                self.wlan.check_connection()
                self.mqtt.update()
                utime.sleep(interval)
        finally:
            self.mqtt.disconnect()
            self.wlan.disconnect()


System().run()
