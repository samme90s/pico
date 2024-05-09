import machine
import utime
from dht import DHT11
from network import (STA_IF, STAT_CONNECT_FAIL, STAT_CONNECTING, STAT_GOT_IP,
                     STAT_IDLE, STAT_NO_AP_FOUND, STAT_WRONG_PASSWORD, WLAN)
from ubinascii import hexlify

from config import ADA_SECRET, ADA_USER, HOST, PORT, SSID, SSID_SECRET
from umqttsimple import MQTTClient


class PICOW:
    def __init__(self, name="PICO"):
        self.name = name
        self.id = machine.unique_id()
        self.id_hex = hexlify(self.id)
        self.led = machine.Pin("WL_GPIO0", machine.Pin.OUT)

    def led_on(self):
        self.led.on()
        self.__print("LED<On>")

    def led_off(self):
        self.led.off()
        self.__print("LED<Off>")

    def __print(self, msg: str):
        print(f"{self.name} :: {msg}")

    def __handle_exc(self, exc: Exception, timeout=1):
        if timeout < 1:
            raise ValueError("Timeout must be greater than 1")

        print(f"{self.name} :: {str(exc.__class__.__name__)}<{str(exc)}>")
        utime.sleep(timeout)

        self.__print("MACHINE<Resetting>")
        self.led_off()
        utime.sleep(timeout)

        machine.reset()


# Workaround for MicroPython due to ABC not working
# Should perhaps be placed in a seperate file named abc.py
def abstractmethod(f):
    return f


class CallbackStrategy:
    @abstractmethod
    def execute(self, feed: bytes, msg: bytes):
        pass


class LEDCallbackStrategy(CallbackStrategy):
    def __init__(self, device: PICOW):
        self.device = device

    def execute(self, feed: bytes, msg: bytes):
        if msg == b"ON":
            self.device.led_on()
        elif msg == b"OFF":
            self.device.led_off()


class WLANController(PICOW):
    def __init__(self, ssid: str, ssid_secret: str, timeout=30, name="WLAN"):
        super().__init__(name=name)

        if ssid is None or ssid_secret is None:
            raise ValueError("Service set -identifier (network name) or -secret (password) is incorrect")

        if timeout < 30:
            raise ValueError("Timeout must be greater than 30")

        # In wireless networking (specifically the IEEE 802.11 standards that
        # define Wi-Fi), a station (STA) interface (IF) refers to any device
        # that can connect to a wireless network.
        self.sta_if = WLAN(STA_IF)
        self.ssid = ssid
        self.ssid_secret = ssid_secret
        self.timeout = timeout
        self.stat_map = {
            STAT_IDLE: "No connection and no activity",
            STAT_CONNECTING: "Connecting in progress",
            STAT_WRONG_PASSWORD: "Failed due to incorrect password",
            STAT_NO_AP_FOUND: "Failed because no access point replied",
            STAT_CONNECT_FAIL: "Failed due to other problems",
            STAT_GOT_IP: "Connection successful"}

    def __status(self):
        return self.__status_message(self.sta_if.status())

    def __status_message(self, status: int):
        return self.stat_map.get(status, f"Unknown status: {status}")

    def connect(self):
        try:
            self.__print(self.__status())
            if not self.sta_if.isconnected():
                self.sta_if.active(True)
                self.sta_if.connect(self.ssid, self.ssid_secret)
                self.__print(self.__status())

                elapsed = 0
                while not self.sta_if.isconnected():
                    utime.sleep(1)
                    if (elapsed := elapsed + 1) > self.timeout:
                        raise Exception(self.__status())

            if self.sta_if.isconnected():
                self.__print(self.__status())
                self.__print(f"Connected<{self.sta_if.ifconfig()}>")
        except Exception as e:
            self.__handle_exc(e)

    def check_connection(self):
        if not self.sta_if.isconnected():
            self.connect()


class MQTTController(PICOW):
    def __init__(self, host: str, port: int, user: str, secret: str, name="MQTT"):
        super().__init__(name=name)

        self.client = MQTTClient(
            self.id_hex,
            host,
            port,
            user,
            secret,
            keepalive=60)
        self.info = f"{self.id_hex}@{host}:{port}"
        self.connected = False

    def connect(self):
        try:
            self.__print(f"Connecting<{self.info}>")
            self.client.connect()
            self.connected = True
            self.__print("Connected")
        except Exception as e:
            self.__handle_exc(e)

    def update(self):
        '''
        Asynchronous method that checks the latest message.
        '''
        self.__check_connection()

        self.client.check_msg()

    def subscribe(self, feed: bytes, callback: CallbackStrategy):
        self.__check_connection()

        self.client.set_callback(f=callback.execute)
        self.client.subscribe(topic=feed)
        self.__print("Subscribed")

    def publish(self, feed: bytes, msg: bytes):
        self.__check_connection()

        self.client.publish(topic=feed, msg=msg)
        self.__print(f"Published<\"{feed.decode()}\": \"{msg.decode()}\">")

    def __check_connection(self):
        if not self.connected:
            self.__handle_exc(Exception("Not connected"))


class DHTController(PICOW):
    def __init__(self, pin: str | int, name="DHT11"):
        super().__init__(name=name)

        self.sensor = DHT11(machine.Pin(pin, machine.Pin.OUT))

    def measure(self):
        try:
            self.sensor.measure()
            return self
        except Exception as e:
            self.__handle_exc(e)

    def get_temperature(self):
        return self.sensor.temperature()

    def get_humidity(self):
        return self.sensor.humidity()


class System:
    def __init__(self):
        # Could be used to display system uptime.
        self.interval_elapsed = utime.time()

        self.device = PICOW()
        self.wlan = WLANController(SSID, SSID_SECRET, 30)
        self.mqtt = MQTTController(HOST, PORT, ADA_USER, ADA_SECRET)
        self.sensor = DHTController(28)
        self.callback = LEDCallbackStrategy(self.device)

        self.f_led = f"{ADA_USER}/f/led".encode()
        self.f_humidity = f"{ADA_USER}/f/humidity".encode()
        self.f_temperature = f"{ADA_USER}/f/temperature".encode()

        self.device.led_on()
        self.wlan.connect()
        self.mqtt.connect()
        self.mqtt.subscribe(self.f_led, self.callback)
        self.mqtt.publish(self.f_led, b"ON")

    def run(self, interval=1, interval_measure=30):
        if interval < 1:
            raise ValueError("Interval must positive")

        if interval_measure < 30:
            raise ValueError("Measure interval must be greater than 30")

        while True:
            self.wlan.check_connection()
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


System().run()
