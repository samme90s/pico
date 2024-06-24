import utime

# Relative imports does not work with MicroPython.
# Otherwise it would be wise to use "from .config import ..." instead.
from config import ADA_USER
from scripts import DHT, MQTT, WIFI


class App:
    def __init__(self):
        """
        Initializes the application, setting up WIFI and MQTT connections, and
        preparing the DHT sensor. It also prepares the topics for humidity and
        temperature to publish to.
        """
        self.wifi = WIFI(timeout=30)
        self.mqtt = MQTT()
        self.sensor = DHT(pin="GP28")

        self.f_humidity = f"{ADA_USER}/f/humidity".encode()
        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.wifi.connect()
        self.mqtt.connect()

    def run(self, interval=1, interval_measure=30):
        """
        Runs the main application loop, publishing sensor data at specified
        intervals and updating MQTT messages.
        Raises ValueError: If the interval is not positive or if
        interval_measure is less than 30.
        """
        try:
            if interval < 1:
                raise ValueError("Interval must positive")

            if interval_measure < 30:
                raise ValueError("Measure interval must be greater than 30")

            while True:
                self.mqtt.update()

                # Prevents rate limiting on Adafruit IO.
                if utime.time() % interval_measure == 0:
                    self.sensor.measure()
                    self.mqtt.publish(
                        topic=self.f_humidity,
                        msg=str(self.sensor.get_humidity()).encode())
                    self.mqtt.publish(
                        topic=self.f_temperature,
                        msg=str(self.sensor.get_temperature()).encode())

                utime.sleep(interval)
        finally:
            self.mqtt.disconnect()
            self.wifi.disconnect()


App().run()
