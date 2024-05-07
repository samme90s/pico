import machine
import ujson
import utime
from dht import DHT11
from network import STA_IF, WLAN
from ubinascii import hexlify

from config import ADA_SECRET, ADA_USER, HOST, PORT, SSID, SSID_SECRET
from umqttsimple import MQTTClient, MQTTException


class WLANController:
    def __init__(self, ssid: str, ssid_secret: str, name="WLAN"):
        if ssid is None or ssid_secret is None:
            raise ValueError("Service set -identifier (network name) or -secret (password) is incorrect")

        # In wireless networking (specifically the IEEE 802.11 standards that
        # define Wi-Fi), a station (STA) interface (IF) refers to any device
        # that can connect to a wireless network.
        self.sta_if = WLAN(STA_IF)
        self.ssid = ssid
        self.ssid_secret = ssid_secret
        self.name = name
        self.__connect()

    def __connect(self):
        if not self.sta_if.isconnected():
            print(f"{self.name} :: Connecting to router...")
            self.sta_if.active(True)
            self.sta_if.connect(self.ssid, self.ssid_secret)

            while not self.sta_if.isconnected():
                print(f"{self.name} :: Waiting for connection...")
                utime.sleep(5)

        print(f"{self.name} :: Connected :: Config<{self.sta_if.ifconfig()}>")

    def disconnect(self):
        if self.sta_if.isconnected():
            print(f"{self.name} :: Disconnecting from router...")
            self.sta_if.disconnect()
            print(f"{self.name} :: Disconnected")
        else:
            print(f"{self.name} :: No active connection to disconnect")


class MQTTController:
    def __init__(self, client_id: bytes, host: str, port: int, user: str, secret: str, name="MQTT"):
        self.client = MQTTClient(
            client_id,
            host,
            port,
            user,
            secret,
            keepalive=60)
        self.info = f"{client_id.decode()}@{host}:{port}"
        self.name = name
        self.__connect()

    def __connect(self):
        try:
            print(f"{self.name} :: Connecting :: {self.info}")
            self.client.connect()
            print(f"{self.name} :: Connection established")
        except Exception as e:
            if isinstance(e, MQTTException):
                print(f"{self.info} :: MQTTException :: {str(e)}")
            elif isinstance(e, OSError):
                print(f"{self.info} :: OSError :: {str(e)}")
            else:
                print(f"{self.info} :: Exception :: {str(e)}")
            self.__reset()

    def __reset(self, seconds=5):
        print(f"Resetting in: {seconds}s")
        utime.sleep(seconds)
        machine.reset()

    def publish(self, topic: bytes, msg: bytes):
        self.client.publish(topic=topic, msg=msg)
        print(f"{self.name} :: Published data")


class DHTController:
    def __init__(self, pin: str | int, name="DHT11"):
        self.sensor = DHT11(machine.Pin(pin, machine.Pin.OUT))
        self.name = name

    def measure(self):
        try:
            self.sensor.measure()
            return self
        except Exception as e:
            if isinstance(e, OSError) and e.args[0] == 110:
                print(f"{self.name} :: Timed out")
            else:
                print(f"{self.name} :: Exception :: {str(e)}")
            machine.reset()

    def get_temperature(self):
        return self.sensor.temperature()

    def get_humidity(self):
        return self.sensor.humidity()


def main():
    WLANController(ssid=SSID, ssid_secret=SSID_SECRET)
    client = MQTTController(client_id=hexlify(machine.unique_id()),
                            host=HOST,
                            port=PORT,
                            user=ADA_USER,
                            secret=ADA_SECRET)
    sensor = DHTController(pin=28)

    while True:
        sensor.measure()
        data = ujson.dumps({
            "temperature": sensor.get_temperature(),
            "humidity": sensor.get_humidity()
        })

        client.publish(
            topic=f"{ADA_USER}/f/picow".encode(),
            msg=data.encode())
        utime.sleep(10)


main()
