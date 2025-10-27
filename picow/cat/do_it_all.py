#import time
import utime
from time import sleep
import thermistor
import rotary
import rotary_irq_rp2
from rotary_irq_rp2 import RotaryIRQ
from machine import ADC,PWM,Pin

from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

import ujson as json

I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16


last_print = utime.ticks_ms()
heater_pin = 10
en_clk_pin = 18
en_dt_pin = 19
en_sw_pin = 20

r = RotaryIRQ(
    pin_num_clk=en_clk_pin,
    pin_num_dt=en_dt_pin,
    reverse=True,
    incr=1,
    range_mode=RotaryIRQ.RANGE_UNBOUNDED,
    pull_up=True,
    half_step=False,
)

en_sw = Pin(en_sw_pin, Pin.IN, Pin.PULL_UP)
sw = en_sw






adcpin = 26
sensor = ADC(adcpin)

set_switch = Pin(14, Pin.IN, Pin.PULL_DOWN)
switch = set_switch

grn = Pin(15, Pin.OUT)
blu = Pin(16,Pin.OUT)
heater = Pin(heater_pin, Pin.OUT)

grn.off()
blu.off()
heater.off()





    
    
last_temp = 1
last_r = 1
last_sw = 1
last_target = 1
last_current = 1
current_temp = 1

ensw_status = 0
ensw_pressed_at = 0
heater_pause = 0
ensw_longpress = 0

i2c = I2C(0, sda=machine.Pin(12), scl=machine.Pin(13), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)    

try:
    with open('savedata.json', 'r') as f:
        data = json.load(f)
        target_temp = data["setTemp"]
except:
    target_temp = 200
    print("target_temp not found.")
    
jsonData = {"setTemp": target_temp}
start_temp = target_temp

old_temp = r.value() + start_temp

def save_set_temp(temp):
    jsonData["setTemp"]=temp
    try:
        with open('savedata.json', 'w') as f:
            json.dump(jsonData, f)
    except:
        print("Could not save the button state variable.")

def lcd_setup():

    lcd.putstr("It Works!")

def lcd_status():
    #lcd.putstr(utime.ticks_ms(), " - ", current_temp,":",target_temp,":",old_temp," ( current : target : setting )")
    lcd.clear()
    lcd_status_string = current_temp, target_temp, old_temp
    if heater_pause == 1:
        lcd_status_string = str(lcd_status_string) + "OFF"
    else:
        lcd_status_string = str(lcd_status_string) + "ON"
        
    lcd.putstr(str(lcd_status_string))

def show_status():
    print("\n", utime.ticks_ms(), " - ", current_temp,":",target_temp,":",old_temp," ( current : target : setting )\n")

lcd_setup_run = 0
if lcd_setup_run == 0:
    lcd_setup_run = 1
    lcd_setup()
lcd_status()

while True:
        

   # rgb_stuff.rgb_loop(last_target, last_sw)
    
    if switch.value():
        #BUTTON PRESSED
        if utime.ticks_ms() >  1000 + last_target:
            last_target = utime.ticks_ms()
            target_temp = r.value() + start_temp
            save_set_temp(target_temp)
            print(" set target = ", target_temp)
            show_status()
            lcd_status()

    if not sw.value():
        #en_sw
        #SWITCH ON ENCODER PRESSED
        if ensw_status != 1:
            ensw_status = 1
            ensw_pressed_at = utime.ticks_ms()
            
        else:
            if utime.ticks_ms() - ensw_pressed_at > 500:
                #long press
                ensw_longpress = 1
                
        if utime.ticks_ms() > 500 + last_sw:
            # WAITED LONG ENOUGH TO DEBOUNCE BUTTON
            last_sw = utime.ticks_ms()
            old_temp = r.value() + start_temp
            show_status()
            lcd_status()
#            print("\n current:target:setting ", current_temp,":",target_temp,":",old_temp,"\n")
#            print(" target valu = ", target_temp)
#            print(" new setting = ", old_temp)
    else:
        if ensw_status == 1:
            ensw_status = 0
            ensw_pressed_at = 0
            if ensw_longpress == 1:
                ensw_longpress = 0
                # released after long press
                if heater_pause == 1:
                    heater_pause = 0
                    print("heater_pause == 0")
                else:
                    heater_pause = 1
                    heater.off()
                    print("heater_pause == 1")
                lcd_status()

    if r.value() + start_temp != old_temp:
        #THERMISTOR VALUE CHANGED
        if utime.ticks_ms() > 1000 + last_r:
            last_r = utime.ticks_ms()
            old_temp = r.value() + start_temp
            print(" renc.value = ", old_temp)
            show_status()
            lcd_status()
        
    if utime.ticks_ms() > (last_temp + 100):
        #TIMER : UPDATE CURRENT TEMP
        last_temp = utime.ticks_ms()
        adc = sensor.read_u16()
        vout = (3.3/65535)*adc
        tempc = thermistor.thermistorTemp(vout)
        current_temp = int(round(tempc, 0))
    
    if utime.ticks_ms() > (last_print + 10000):
        #TIMER : PRINT CURRENT TEMP
        last_print = utime.ticks_ms()
        if last_current != current_temp:
            last_current = current_temp
            #print("current temp: ", current_temp)
            show_status()
            lcd_status()


    if current_temp >= target_temp:
        grn.on()
        blu.off()
        heater.off()
    else:
        grn.off()
        if heater_pause == 0:
            blu.on()
            heater.on()
        else:
            #print("heater_pause == 1")
            blu.off()
            heater.off()
        
    sleep(.01)
    
    
