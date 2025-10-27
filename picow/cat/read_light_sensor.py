import machine
from machine import Pin, ADC
import utime
light_sensor_pin = 28 #ADC2
ldr = Pin(light_sensor_pin, Pin.IN, Pin.PULL_UP)
light_sensor = ADC(light_sensor_pin)

while True :
    print(light_sensor.read_u16())
    utime.sleep(1)
    
