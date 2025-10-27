import machine
from machine import Pin, ADC
import utime
light_sensor_pin = 27
ldr = Pin(light_sensor_pin, Pin.IN, Pin.PULL_UP)
light_sensor = ADC(light_sensor_pin)
lamp = Pin(2, Pin.OUT)
lamp.off()
pot_pin = 26
dial = ADC(pot_pin)
button_pin = 14
button = Pin(button_pin, Pin.IN, Pin.PULL_UP)
mode = 0 #auto
lastbutton = 0 #off
while True :
    if button.off():
        lastbutton = 1
    if button.on():
        if lastbutton == 1:
            if mode == 0:
                mode = 1
            else:
                mode = 0
        lastbutton = 0
    if mode == 1:
        lamp.on()
    else:
        
        threshold = dial.read_u16()
        sensor = light_sensor.read_u16()
        print("threshold:",threshold)
        print("sensor:",sensor)
        if sensor > threshold:
            lamp.on()
        else:
            lamp.off()
        utime.sleep(.1)
    
