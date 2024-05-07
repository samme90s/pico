import machine
import ujson
import utime
from dht import DHT11
from network import STA_IF, WLAN
from ubinascii import hexlify

from config import ADA_SECRET, ADA_USER, HOST, PORT, SSID, SSID_SECRET
from umqttsimple import MQTTClient


class Controller:
    def __init__(self, name="Controller"):
        self.name = name

    def __print(self, msg: str):
        print(f"{self.name} :: {msg}")

    def __handle_exc(self, exc: Exception, timeout=1):
        if timeout < 1:
            raise ValueError("Timeout must be greater than 1")

        print(f"{self.name} :: {str(exc.__class__.__name__)}<{str(exc)}>")
        utime.sleep(timeout)

        self.__print("MACHINE<Resetting>")
        utime.sleep(timeout)

        machine.reset()


class WLANController(Controller):
    def __init__(self, ssid: str, ssid_secret: str, timeout=30, name="WLAN"):
        super().__init__(name=name)

        if ssid is None or ssid_secret is None:
            raise ValueError("Service set -identifier (network name) or -secret (password) is incorrect")

        # In wireless networking (specifically the IEEE 802.11 standards that
        # define Wi-Fi), a station (STA) interface (IF) refers to any device
        # that can connect to a wireless network.
        self.sta_if = WLAN(STA_IF)
        self.ssid = ssid
        self.ssid_secret = ssid_secret
        self.timeout = timeout
        self.__connect()

    def __connect(self):
        try:
            if not self.sta_if.isconnected():
                self.__print("Connecting")
                self.sta_if.active(True)
                self.sta_if.connect(self.ssid, self.ssid_secret)

                elapsed = 0
                while not self.sta_if.isconnected():
                    utime.sleep(1)
                    if (elapsed := elapsed + 1) > self.timeout:
                        raise Exception("Timed out")

                self.__print(f"Connected<{self.sta_if.ifconfig()}>")
        except Exception as e:
            self.__handle_exc(e)


class MQTTController(Controller):
    def __init__(self, client_id: bytes, host: str, port: int, user: str, secret: str, name="MQTT"):
        super().__init__(name=name)

        self.client = MQTTClient(
            client_id,
            host,
            port,
            user,
            secret,
            keepalive=60)
        self.info = f"{client_id.decode()}@{host}:{port}"

        self.__connect()

    def __connect(self):
        try:
            self.__print(f"Connecting<{self.info}>")
            self.client.connect()
            self.__print("Connected")
        except Exception as e:
            self.__handle_exc(e)

    def update(self):
        self.client.check_msg()
        self.__print("Updated")

    def subscribe(self, feed: bytes, callback):
        self.client.set_callback(f=callback)
        self.client.subscribe(topic=feed)
        self.__print("Subscribed")

    def publish(self, feed: bytes, msg: bytes):
        self.client.publish(topic=feed, msg=msg)
        self.__print("Published data")


class DHTController(Controller):
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


class App:
    def __init__(self):
        self.wlan = WLANController(SSID, SSID_SECRET, 5)
        self.mqtt = MQTTController(hexlify(machine.unique_id()), HOST, PORT, ADA_USER, ADA_SECRET)
        self.sensor = DHTController(28)
        self.sensor_feed = f"{ADA_USER}/f/sensor".encode()
        self.led = machine.Pin("WL_GPIO0", machine.Pin.OUT)
        self.led_feed = f"{ADA_USER}/f/led".encode()

        self.mqtt.subscribe(self.led_feed, self.sub_callback)

    def sub_callback(self, feed: bytes, msg: bytes):
        if msg == b"ON":
            self.led.on()
        elif msg == b"OFF":
            self.led.off()

    def run(self, interval=3):
        while True:
            self.mqtt.update()

            self.sensor.measure()
            data = ujson.dumps({
                "temperature": self.sensor.get_temperature(),
                "humidity": self.sensor.get_humidity()
            })
            self.mqtt.publish(
                feed=self.sensor_feed,
                msg=data.encode())

            utime.sleep(interval)


App().run()
