import utime
delay = utime.sleep

grn_led_pin = 15
blu_led_pin = 10
import machine
P = machine.Pin

grn = P(grn_led_pin, P.OUT)
grn.init()
grn.on()
delay(2)
grn.off()
delay(2)

blu = P(blu_led_pin, P.OUT)
blu.init()
blu.on()
delay(2)
blu.off()
delay(2)

Dimmer = machine.PWM
grn_led = Dimmer(grn)
grn_led.freq(1000)
grn_led.duty_u16(0)


blu_led = Dimmer(blu)
blu_led.freq(1000)
blu_led.duty_u16(0)

x=1
while x==1:
    x=2
    #do nothing

#delay(1000)
import random

from machine import Pin
from machine import Pin as P
from machine import PWM
from machine import PWM as Dimmer
from utime import sleep as delay



from utime import sleep
import random

# Set GPIO pin for audio output    
buzzer_pin = 16
buzzer = PWM(Pin(buzzer_pin))
#buzzer = Dimmer(buzzer_pin)

def play_tone(frequency):

    # Set maximum volume
    buzzer.duty_u16(1000)
    # Play tone
    buzzer.freq(frequency)

def be_quiet():
    # Set minimum volume
    buzzer.duty_u16(0)

## Set GPIO pins to use for switches
switch_1 = Pin(2, Pin.IN, Pin.PULL_DOWN)
switch_2 = Pin(3, Pin.IN, Pin.PULL_DOWN)
switch_3 = Pin(4, Pin.IN, Pin.PULL_DOWN)

grn = P(15, P.OUT, Pin.PULL_DOWN)

pause = P(14, P.IN, P.PULL_DOWN)


grn.on()
delay(.5)
grn.off()
delay(.5)

pIN =  0xFE
i=0
pOUT = 0
#pbyte = slice(pIN)
while i < 8:
  pOUT += \0b00000001
  print ("while ",i, " < 8: {")
  print ("pOUT(", pOUT, ") += pbyte(", pbyte, ")[", i, "]")
  print ("(", pbyte[i], ") ;")
  i+=1
  
    
while True:
    while pause.value() == False:
        grn.on()
        blu.off()
        delay(.5)
        grn.off()
        blu.on()
        delay(.5)
        
    grn.off()
    blu.off()
    
    