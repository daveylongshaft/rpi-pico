import machine
from machine import Pin, ADC
import utime
from utime import ticks_add, ticks_diff, ticks_ms, sleep

light_sensor_pin = 27
ldr = Pin(light_sensor_pin, Pin.IN, Pin.PULL_UP)
light_sensor = ADC(light_sensor_pin)

#lamp is a relay.  
lamp = Pin(2, Pin.OUT)
lamp.off()

pot_pin = 26
dial = ADC(pot_pin)

button_pin = 14
button = Pin(button_pin, Pin.IN, Pin.PULL_DOWN)

mode = 0 #0=auto; 1=on; 2=strobe/off;

strobe_enabled = False
strobe_adder = 5
strobe_max = 300
strobe_min = 100
strobe_rate = 100 #ms delay between toggles
last_strobe = ticks_ms()

lastbutton = 0 #off
button_start = 0
button_longpress = 300 # ms hold for longpress
button_is_longpressed = 0

def do_strobe() :
    global last_strobe,  strobe_rate
    if (strobe_enabled == True) :
        print("last_strobe",last_strobe)
        print("strobe_rate",strobe_rate)
        strobe_ms = ticks_add(last_strobe, strobe_rate)
        print("strobe_ms", strobe_ms)
        if ticks_diff(strobe_ms, ticks_ms()) < 0:
            print("strobe_toggle")
            if lamp.value() == 1:
                lamp.off()
            else :
                lamp.on()
            last_strobe = ticks_ms()
    else :
        lamp.off()
        print("lamp off")
        
def is_longpressed() :
    global button_start, button_longpress, button_is_longpressed
    button_is_longpressed = 0
    if button_start > 0 :
        if ticks_diff(ticks_ms(), button_start) >= button_longpress:
            button_is_longpressed = 1
    return button_is_longpressed

print("mode:",mode)
while True :
    if (button.value() == 1): #button is pressed
        if lastbutton == 0:#was not pressed
            lastbutton = 1 
            button_start = ticks_ms() # to check for longpress
        if is_longpressed() :
           #button was longpressed
            print("longpressed")
            if mode == 2: #strobe if enabled or else lamp.off()
                print("mode:",mode)
                if (strobe_enabled == True) :
                
                    strobe_rate += strobe_adder
                    if strobe_rate > strobe_max:
                        strobe_adder = strobe_adder * -1 #strobe_adder reversal
                        strobe_rate = strobe_max + strobe_adder #should be negative adder now
                        print("strobe_adder",strobe_adder)
                    elif strobe_rate < strobe_min:
                        strobe_adder = strobe_adder * -1 #strobe_adder reversal
                        strobe_rate = strobe_min + strobe_adder # should be positive adder now
                    
                    do_strobe()
                else:
                    lamp.off()
                    print("lamp off")
                   
    if button.value() == 0: # button is not pressed
        if lastbutton == 1:  # button was released after pressing
            lastbutton = 0                
            if button_is_longpressed == 1:
                button_is_longpressed = 0
                #take action for longpress
                if mode == 1: 
                    mode = 2 #turn on strobe
                if mode == 2:
                    print("mode:",mode)
                    if (strobe_enabled == True) :
                        do_strobe();
                    else:
                        lamp.off()
                        print("lamp off")
            else : #button is not longpressed               
                if mode == 0: #off
                    mode = 1  #turn on
                    lamp.on()
                    print("mode:",mode)
                else:
                    if mode == 1: #on
                        mode = 2 # turn strobe
                        print("mode:",mode)
                        if (strobe_enabled == True) :
                            do_strobe()
                        else :
                            lamp.off()                        
                            print("lamp off")
                    else :
                        mode = 0 #turn off
                        print("mode:",mode)
                        lamp.off()
                        print("lamp off")
        else:
            #button was not pressed
                        
            #nevermind buttons                
            if mode == 1:
                lamp.on()
                print("mode:",mode)
            else:
                if mode == 2:
                    print("mode:",mode)
                    if (strobe_enabled == True) :
                        print("strobe_rate:",strobe_rate)
                        do_strobe()
                    else:
                        lamp.off()
                        print("lamp off")
                else:
                    # mode == 0
                    # light sensitive on/off
                    print("mode:",mode)        
                    threshold = dial.read_u16()
                    print("threshold:",threshold)
                
                    sensor = light_sensor.read_u16()
                    print("sensor:",sensor)
                
                    if sensor > threshold:
                        lamp.on()
                        print("lamp on")
                    else:
                        lamp.off()
                        print("lamp off")
                
    sleep(.1)




#RPi pico W pinout
def pinout():
    print("""
                             ---usb---
                    GP0   1  |o     o| 40  VBUS
                    GP1   2  |o     o| 39  VSYS
                    GND   3  |o     o| 38  GND
[relay control NO]  GP2   4  |o     o| 37  3V3_EN
                    GP3   5  |o     o| 36  3V3(OUT)
                    GP4   6  |o     o| 35           ADC_VREF
                    GP5   7  |o     o| 34  GP28     ADC2
                    GND   8  |o     o| 33  GND      AGND
                    GP6   9  |o     o| 32  GP27     ADC1  [light_sensor_pin]
                    GP7   10 |o     o| 31  GP26     ADC0  [variable resistor]
                    GP8   11 |o     o| 30  RUN
                    GP9   12 |o     o| 29  GP22
                    GND   13 |o     o| 28  GND
                    GP10  14 |o     o| 27  GP21
                    GP11  15 |o     o| 26  GP20
                    GP12  16 |o     o| 25  GP19
                    GP13  17 |o     o| 24  GP18
                    GND   18 |o     o| 23  GND
         [button]   GP14  19 |o     o| 22  GP17
                    GP15  20 |o     o| 21  GP16
                             ---------
    """)
pinout()