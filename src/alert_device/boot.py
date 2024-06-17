import machine
import utime

from config import ADA_USER
from scripts import MQTT, WIFI, CallbackStrategy


class LED(CallbackStrategy):
    def __init__(self):
        """
        Initializes the LED controller with input and output pins set to GP15.
        """
        self.input = machine.Pin("GP15", machine.Pin.IN, machine.Pin.PULL_UP)
        self.output = machine.Pin("GP15", machine.Pin.OUT)

    def execute(self, topic: bytes, msg: bytes):
        """
        Executes the LED control logic based on the message received.
        Below 2 or above 8: Turn on the LED.
        """
        reading = int(msg.decode())

        if reading < 2 or reading > 8:
            if not self.input.value():
                self.output.on()
        elif self.input.value():
            self.output.off()


class App:
    def __init__(self):
        """
        Initializes the application, setting up WIFI and MQTT connections and
        subscribing to the temperature topic.
        """
        self.wlan = WIFI(timeout=30)
        self.mqtt = MQTT()

        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.wlan.connect()
        self.mqtt.connect()
        self.mqtt.subscribe(self.f_temperature, LED())

    def run(self, interval=1):
        """
        Runs the main application loop, updating MQTT messages at the specified
        interval.
        Raises ValueError: If the interval is not positive.
        """
        try:
            if interval < 1:
                raise ValueError("Interval must positive")

            while True:
                self.mqtt.update()
                utime.sleep(interval)
        finally:
            self.mqtt.disconnect()
            self.wlan.disconnect()


App().run()
