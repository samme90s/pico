import utime

# Relative imports does not work with MicroPython.
# Otherwise it would be wise to use "from .config import ..." instead.
from config import ADA_USER
from scripts import DHT, MQTT, WIFI, LEDCallbackStrategy


class System:
    def __init__(self):
        # Could be used to display system uptime.
        self.interval_elapsed = utime.time()

        self.wifi = WIFI(timeout=30)
        self.mqtt = MQTT()
        self.sensor = DHT(pin="GP28")

        self.f_humidity = f"{ADA_USER}/f/humidity".encode()
        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.wifi.connect()
        self.mqtt.connect()
        self.mqtt.subscribe(self.f_temperature, LEDCallbackStrategy())

    def run(self, interval=1, interval_measure=30):
        try:
            if interval < 1:
                raise ValueError("Interval must positive")

            if interval_measure < 30:
                raise ValueError("Measure interval must be greater than 30")

            while True:
                self.wifi.check_connection()
                self.mqtt.update()

                # Prevents rate limiting on Adafruit IO.
                if self.interval_elapsed % interval_measure == 0:
                    self.sensor.measure()
                    self.mqtt.publish(
                        feed=self.f_humidity,
                        msg=str(self.sensor.get_humidity()).encode())
                    self.mqtt.publish(
                        feed=self.f_temperature,
                        msg=str(self.sensor.get_temperature()).encode())

                self.interval_elapsed = utime.time()
                utime.sleep(interval)
        finally:
            self.mqtt.disconnect()
            self.wifi.disconnect()


System().run()
