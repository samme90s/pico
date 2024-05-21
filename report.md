# Pico

Samuel Svensson

## Objective (1hr)

The objective of this project is to build a temperature and humidity sensor that can be used in a home environment. The sensor will be connected to the internet and send data to a cloud service. The data will be presented in a dashboard where the user can see the current temperature and humidity in real-time. The user can also see historical data and trends over time.

### Why

I chose to this the techniques and hardware because I wanted to learn more about how to build IoT (internet of thing) -devices and how to connect them to the internet.

### Insights

The project will give insights to the possibilites of internet of things and how to apply code to real world applications. Based on the data collected, the user can see trends over time, make decisions based on the data and present the data in a meaningful way, even though the DHT11 is fairly inaccurate. It also gave me a good understanding of how to build IoT-devices.

## Material

All the material can be picked up at Elektro:Kit (Sweden). Here are the minimum articles required:

| Type                        | Article                                                                        | Price  |
| --------------------------- | ------------------------------------------------------------------------------ | ------ |
| Microcontroller (PicoWH):   | [41019114](https://www.electrokit.com/raspberry-pi-pico-wh)                    | ~90SEK |
| Temperature sensor (DHT11): | [41015728](https://www.electrokit.com/digital-temperatur-och-fuktsensor-dht11) | ~50SEK |
| Wires (Female-to-Female):   | [41015695](https://www.electrokit.com/labsladd-1-pin-hona-hona-150mm-10-pack)  | ~30SEK |

Wires are needed to connect the sensor to the Pico.

### Optional

The Pico with headers (Raspberry PicoWH) is recommended. It makes it easier to connect the sensor to the Pico.

Depending on the version of DHT11, a resistor might be needed.

## Software and tools

### Flashing

1. Flash the microcontroller with MicroPython. The firmware can be downloaded from the official website. Ensure that the device corresponds correctly to the driver (in our case: [PicoW - MicroPython](https://micropython.org/download/RPI_PICO_W/))
2. Hold the **BOOTSEL** button on the Pico whilst connecting it to the computer.
3. Unzip the downloaded file and move it on to the device.
4. Wait a few seconds and then reconnect the device (**NOT** holding the **BOOTSEL** button).

### IDE

**Visual Studio Code** for its modularity and ease of use.

#### Plugins

| Plugin                                                                              | Description         |
| ----------------------------------------------------------------------------------- | ------------------- |
| [MicroPico](https://marketplace.visualstudio.com/items?itemName=paulober.pico-w-go) | MicroPython support |

### Software

[Python](https://www.python.org/downloads/)

## Construction

**IMPORTANT!** Make sure to not confuse `Pin` numbers with `GPIO` numbers. The Pico has both, and it is important to use the correct one.
The `GPIO` numbers are the ones used in the code and will therefore be used in this tutorial.

| Device | Diagram                                                                                                              |
| ------ | -------------------------------------------------------------------------------------------------------------------- |
| PicoW  | [PicoW](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#pinout-and-design-files-2) |
| DHT11  | [DHT11](https://www.electrokit.com/upload/product/41015/41015728/41015728_-_Digital_Temperature_Humidity_Sensor.pdf) |

### Wiring

| PicoW    | Wire  | DHT11        |
| -------- | ----- | ------------ |
| GP28     | Blue  | Data (Left)  |
| 3V3(OUT) | Red   | VCC (Center) |
| GND      | Black | GND (Right)  |

## Cloud

### Adafruit IO

Adafruit IO is a cloud service that allows you to send and receive data from your devices. It is easy to use and has a free tier that is sufficient for this project.

## Code

```py
# boot.py
class System:
    def __init__(self):
            # Could be used to display system uptime.
            self.interval_elapsed = utime.time()

            # Classes for the different components and services.
            self.device = PICOW()
            # Controls the internet connection.
            self.wlan = WLANController(SSID, SSID_SECRET, 30)
            # Controls the MQTT actions.
            # This is a wrapper for the umqtt.simple library that can be found in the MicroPython repository.
            # See: https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py
            self.mqtt = MQTTController(HOST, PORT, ADA_USER, ADA_SECRET)
            self.sensor = DHTController(28)
            # Strategy to pass to the mqtt subscription callback.
            self.callback = LEDCallbackStrategy(self.device)

            # Adafruit IO feeds for the different data.
            # We encode them to bytes to allow for faster transmission (this is a part of the MQTT protocol).
            self.f_led = f"{ADA_USER}/f/led".encode()
            self.f_humidity = f"{ADA_USER}/f/humidity".encode()
            self.f_temperature = f"{ADA_USER}/f/temperature".encode()

            # Initialize the different components and services.
            self.device.led_on()
            self.wlan.connect()
            self.mqtt.connect()
            self.mqtt.subscribe(self.f_led, self.callback)
            # This ensures that the cloud service is updated with the current state of the LED.
            self.mqtt.publish(self.f_led, b"ON")

    def run(self, interval=1, interval_measure=30):
        if interval < 1:
            raise ValueError("Interval must positive")

        if interval_measure < 30:
            raise ValueError("Measure interval must be greater than 30")

        while True:
            # Verifies the connection to the internet.
            self.wlan.check_connection()
            # Updates the MQTT controller (example checks for incoming messages).
            self.mqtt.update()

            # Prevents rate limiting on Adafruit IO.
            if self.interval_elapsed % interval_measure == 0:
                # Measures the temperature and humidity.
                self.sensor.measure()
                # Publishes the data to the cloud service.
                self.mqtt.publish(
                    feed=self.f_humidity,
                    msg=str(self.sensor.get_humidity()).encode())
                self.mqtt.publish(
                    feed=self.f_temperature,
                    msg=str(self.sensor.get_temperature()).encode())

            self.interval_elapsed = utime.time()
            utime.sleep(interval)
```

## Data flow / Connectivity

The system runs on a ~1 second interval, but the data is only sent every ~30 seconds to prevent rate limiting by the cloud service.

### Protocols

#### Wireless

The device (MCU) is connected to the internet via the WiFi protocol. This is done through the network library in MicroPython where we utilize the WLAN class to establish the connection.

This protocol suffices as the device is stationary and does not require a long range. Furthermore, the project does not use a LoRa-WAN component.

#### Transport

The data is sent through MQTT (Message Queuing Telemetry Transport) which is a lightweight messaging protocol. This is done through an extension from the MicroPython library ([umqtt.simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py)).

This protocol was chosen due to its simplicity and low bandwidth model. It is also supported by Adafruit IO.

### Information model

It uses a MQTT topic structure for sending sensor data. The topics are defined in the `System` class with the `f_led`, `f_humidity`, and `f_temperature` variables. The data sent to these topics is a byte string, either representing the state of the LED or the sensor readings.

## Adafruit IO

### Feeds

Feeds are the data points and stores the data sent from the device.

### Dashboards

Dashboards may be used to control a feed or display its data.

## Final thoughts

### Video

[Presentation](https://youtu.be/cJ6gIpHRpGc)

### Reflection

The project was fairly difficult at first as I had never worked with MicroPython before. Furthermore, understanding how I had to find libraries myself and clone these was not too obvious. However, after some time, I got the hang of it and was quite fun to work on.

I had some issues getting the `main.py` file to run after `boot.py` and therefore moved all code to the `boot.py` file. I tried setting `machine.main("main.py")` in the `boot.py` file, but it did not recognize this functionality. For more about this see PyCom's documentation.
