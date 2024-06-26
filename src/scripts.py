import machine
import ubinascii
import utime
from dht import DHT11
from network import (STA_IF, STAT_CONNECT_FAIL, STAT_CONNECTING, STAT_GOT_IP,
                     STAT_IDLE, STAT_NO_AP_FOUND, STAT_WRONG_PASSWORD, WLAN)

from config import ADA_SECRET, ADA_USER, HOST, PORT, SSID, SSID_SECRET
from umqttsimple import MQTTClient


# Workaround for MicroPython due to ABC not working
# Should perhaps be placed in a seperate file named abc.py
def abstractmethod(f):
    return f


class CallbackStrategy:
    @abstractmethod
    def execute(self, topic: bytes, msg: bytes):
        pass


class Controller:
    def __init__(self, name="CTRL"):
        """
        The name is used for debugging purposes
        and is added to the console whenever a message is printed.
        """
        self.name = name

        self._print("Initializing")

    def _print(self, msg: str):
        """
        Utilizes the name from the constructor and takes a message.
        """
        print(f"{self.name} :: {msg}")

    def _handle_exc(self, exc: Exception):
        """
        Handles exceptions and prints them to the console.
        The device is then reset after a second.
        """
        self._print(f"{str(exc.__class__.__name__)}<{str(exc)}>")
        utime.sleep(1)

        self._print("MACHINE<Resetting>")
        utime.sleep(1)

        machine.reset()


class WIFI(Controller):
    def __init__(self, timeout=30, name="WLAN"):
        """
        Initializes the WIFI controller with a specified timeout and name.
        Raises ValueError: If either SSID or SSID_SECRET is None, or if timeout
        is less than 30.
        """
        super().__init__(name=name)

        if timeout < 30:
            raise ValueError("Timeout must be greater than 30")

        if SSID is None or SSID_SECRET is None:
            raise ValueError("Service set -identifier (network name) or -secret (password) is incorrect")

        # In wireless networking (specifically the IEEE 802.11 standards that
        # define Wi-Fi), a station (STA) interface (IF) refers to any device
        # that can connect to a wireless network.
        self.sta_if = WLAN(STA_IF)
        self.timeout = timeout
        self.stat_map = {
            STAT_IDLE: "No connection and no activity",
            STAT_CONNECTING: "Connecting in progress",
            STAT_WRONG_PASSWORD: "Failed due to incorrect password",
            STAT_NO_AP_FOUND: "Failed because no access point replied",
            STAT_CONNECT_FAIL: "Failed due to other problems",
            STAT_GOT_IP: "Connection successful"}

    def __status(self):
        """
        Retrieves the current status message of the WIFI connection.
        """
        return self.__status_message(self.sta_if.status())

    def __status_message(self, status: int):
        """
        Converts a status code into a human-readable status message.
        """
        return self.stat_map.get(status, f"Unknown status: {status}")

    def connect(self):
        """
        Attempts to connect to the WIFI network using the SSID and SSID_SECRET.
        It will try to connect until the specified timeout is reached.
        Raises Exception: If unable to connect within the timeout period.
        """
        try:
            self._print(self.__status())
            if not self.sta_if.isconnected():
                self.sta_if.active(True)
                self.sta_if.connect(SSID, SSID_SECRET)
                self._print(self.__status())

                elapsed = 0
                while not self.sta_if.isconnected():
                    self._print("Connecting...")
                    utime.sleep(1)
                    if (elapsed := elapsed + 1) > self.timeout:
                        raise Exception(self.__status())

            if self.sta_if.isconnected():
                self._print(self.__status())
                self._print(f"Connected<{self.sta_if.ifconfig()}>")
        except Exception as e:
            self._handle_exc(e)

    def disconnect(self):
        """
        Disconnects from the WIFI network if currently connected.
        """
        try:
            if self.sta_if.isconnected():
                self._print("Disconnecting")
                self.sta_if.disconnect()
                self.sta_if.active(False)
                self._print(self.__status())
        except Exception as e:
            self._handle_exc(e)


class MQTT(Controller):
    def __init__(self, name="MQTT"):
        """
        Initializes the MQTT controller with a specified name.
        Raises ValueError: If HOST, PORT, ADA_USER, or ADA_SECRET is None.
        """
        super().__init__(name=name)

        if HOST is None:
            raise ValueError("Host is not set")

        if PORT is None:
            raise ValueError("Port is not set")

        if ADA_USER is None or ADA_SECRET is None:
            raise ValueError("user credentials are not set")

        self.client = MQTTClient(
            ubinascii.hexlify(machine.unique_id()),
            HOST,
            PORT,
            ADA_USER,
            ADA_SECRET,
            ssl=False)
        self.info = f"{self.client.client_id.decode()}@{self.client.server}:{self.client.port}"
        self.connected = False

    def connect(self):
        """
        Attempts to connect to the MQTT broker using the provided credentials.
        Raises Exception: If the connection attempt fails.
        """
        try:
            self._print(f"Connecting<{self.info}>")
            self.client.connect()
            self.connected = True
            self._print("Connected")
        except Exception as e:
            self._handle_exc(e)

    def disconnect(self):
        """
        Disconnects from the MQTT broker if currently connected.
        """
        try:
            if self.connected:
                self._print(f"Connecting<{self.info}>")
                self.client.disconnect()
                self.connected = False
                self._print("Disconnected")
        except Exception as e:
            self._handle_exc(e)

    def update(self):
        '''
        Asynchronous method that checks the latest message.
        '''
        self.__check_connection()

        # Getting a similar error after waiting for a while:
        # https://github.com/micropython/micropython/issues/5451
        self.client.check_msg()

    def subscribe(self, topic: bytes, callback: CallbackStrategy):
        """
        Subscribes to a specific topic on the MQTT broker.
        """
        self.__check_connection()

        self.client.set_callback(f=callback.execute)
        self.client.subscribe(topic=topic)
        self._print("Subscribed")

    def publish(self, topic: bytes, msg: bytes):
        """
        Publishes a message to a specific topic on the MQTT broker.
        """
        self.__check_connection()

        self.client.publish(topic=topic, msg=msg)
        self._print(f"Published<\"{topic.decode()}\": \"{msg.decode()}\">")

    def __check_connection(self):
        """
        Checks if there is a current connection to the MQTT broker.
        Raises Exception: If not currently connected to the MQTT broker.
        """
        if not self.connected:
            self._handle_exc(Exception("Not connected"))


class DHT(Controller):
    def __init__(self, pin: str | int, name="DHT11"):
        """
        Initializes the DHT sensor controller with a specified pin and name.
        """
        super().__init__(name=name)

        self.sensor = DHT11(machine.Pin(pin, machine.Pin.OUT))

    def measure(self):
        """
        Triggers a measurement on the DHT sensor.
        Returns: Self for chaining.
        Raises Exception: If the measurement fails.
        """
        try:
            self.sensor.measure()
            return self
        except Exception as e:
            self._handle_exc(e)

    def get_temperature(self):
        """
        Retrieves the last measured temperature from the DHT sensor.
        """
        return self.sensor.temperature()

    def get_humidity(self):
        """
        Retrieves the last measured humidity from the DHT sensor.
        """
        return self.sensor.humidity()
