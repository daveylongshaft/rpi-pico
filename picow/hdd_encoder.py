from machine import ADC, Pin
import time

# Initialize ADC on pin 26 (ADC0)
A = ADC(Pin(28))
B = ADC(Pin(27))
C = ADC(Pin(26))

last_set = [0,0,0]
last_value = 0
this_value = 0
current_value = 0

while True:
    # Read the ADC value (0-65535)
    a_value = A.read_u16()
    b_value = B.read_u16()
    c_value = C.read_u16()
    
    # Convert the ADC value to a voltage (assuming 3.3V reference)
    a_voltage =  (a_value * 3.3 / 65535)
    b_voltage =  (b_value * 3.3 / 65535)
    c_voltage =  (c_value * 3.3 / 65535)

    this_set = [a_voltage, b_voltage, c_voltage]
    if this_set != last_set :     
        last_set = this_set
        if a_voltage > 0:
            this_value = 1
            if last_value == 2:
                current_value -= 1
                print("REV:", current_value)
            elif last_value == 4:
                current_value += 1
                print("FWD:", current_value)
        elif b_voltage > 0:
            this_value = 2
            if last_value == 4:
                current_value -= 1
                print("REV:", current_value)
            elif last_value == 1:
                current_value += 1
                print("FWD:", current_value)                
        elif c_voltage > 0:
            this_value = 4
            if last_value == 1:
                current_value -= 1
                print("REV:", current_value)
            elif last_value == 2:
                current_value += 1
                print("FWD:", current_value)
            
        last_value = this_value            
        
    # Wait for a short period before reading again
    time.sleep(.1)
    
    #RPi pico W pinout
def pinout():
    print("""
                             ---usb---
                    GP0   1  |o     o| 40  VBUS
                    GP1   2  |o     o| 39  VSYS
                    GND   3  |o     o| 38  GND
                    GP2   4  |o     o| 37  3V3_EN
                    GP3   5  |o     o| 36  3V3(OUT)
                    GP4   6  |o     o| 35           ADC_VREF    [center]
                    GP5   7  |o     o| 34  GP28     ADC2        [A]
                    GND   8  |o     o| 33  GND      AGND
                    GP6   9  |o     o| 32  GP27     ADC1        [B]
                    GP7   10 |o     o| 31  GP26     ADC0        [C]
                    GP8   11 |o     o| 30  RUN
                    GP9   12 |o     o| 29  GP22
                    GND   13 |o     o| 28  GND
                    GP10  14 |o     o| 27  GP21
                    GP11  15 |o     o| 26  GP20
                    GP12  16 |o     o| 25  GP19
                    GP13  17 |o     o| 24  GP18
                    GND   18 |o     o| 23  GND
                    GP14  19 |o     o| 22  GP17
                    GP15  20 |o     o| 21  GP16
                             ---------
    """)
pinout()
