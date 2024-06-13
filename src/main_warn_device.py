import machine
import utime

from config import ADA_USER
from scripts import MQTT, WIFI, CallbackStrategy


class LED(CallbackStrategy):
    def __init__(self):
        self.input = machine.Pin("GP15", machine.Pin.IN, machine.Pin.PULL_UP)
        self.output = machine.Pin("GP15", machine.Pin.OUT)

    def execute(self, feed: bytes, msg: bytes):
        reading = int(msg.decode())

        if reading < 7 or reading > 9:
            if not self.input.value():
                self.output.on()
        elif self.input.value():
            self.output.off()


class App:
    def __init__(self):
        self.wlan = WIFI(timeout=30)
        self.mqtt = MQTT()

        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.wlan.connect()
        self.mqtt.connect()
        self.mqtt.subscribe(self.f_temperature, LED())

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


App().run()
