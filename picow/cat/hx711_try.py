# Example for Pycom device, gpio mode
# Connections:
# Pin # | HX711
# ------|-----------
# P9    | data_pin
# P8   | clock_pin
#

from hx711 import HX711
from machine import Pin

pin_OUT = Pin(9, Pin.IN, pull=Pin.PULL_DOWN)
pin_SCK = Pin(10, Pin.OUT)

hx711 = HX711(pin_SCK, pin_OUT)

hx711.tare()
value = hx711.read()
value = hx711.get_value()