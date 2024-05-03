import dht
import utime
from machine import Pin

run = True
led = Pin("WL_GPIO0", Pin.OUT)
sensor = dht.DHT11(Pin(28, Pin.OUT))

while run:
    sensor.measure()

    utime.sleep(1)

    temp = sensor.temperature()
    humidity = sensor.humidity()
    print(f"Temperature: {temp}C")
    print(f"Humidity: {humidity}%")
