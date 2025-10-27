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
import math
#import buzzer
#from buzzer import note, playNote, buzzer, BUZZER_PIN, is_buzzer_setup
#buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))

heater_pin = 10
grn_pin = 15
blu_pin = 16
en_clk_pin = 18
en_dt_pin = 19
en_sw_pin = 20
light_sensor_pin = 28 #ADC2
adcpin = 26
set_switch_pin = 14
builtin_temp_pin = 4


last_temp = 1
last_r = 1
last_sw = 1
last_target = 1
last_current = 1
current_temp = 1
target_temp = 1
ensw_status = 0
ensw_pressed_at = 0
heater_pause = 0
ensw_longpress = 0
ldr = Pin(light_sensor_pin, Pin.IN, Pin.PULL_UP)
light_sensor = ADC(light_sensor_pin)


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
sensor = ADC(adcpin)
set_switch = Pin(set_switch_pin, Pin.IN, Pin.PULL_DOWN)
switch = set_switch

grn = Pin(grn_pin, Pin.OUT)
blu = Pin(blu_pin,Pin.OUT)
heater = Pin(heater_pin, Pin.OUT)
grn.off()
blu.off()
heater.off()

last_print = utime.ticks_ms()

I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16
i2c = I2C(0, sda=machine.Pin(12), scl=machine.Pin(13), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)    
jsonData = {"setTemp": target_temp}


light_sensor_reading = light_sensor.read_u16()

BETA               = 3974
RESISTOR_ROOM_TEMP = 10000
builtin_temp = machine.ADC(builtin_temp_pin) 
BALANCE_RESISTOR = 1000
MAX_ADC = 65535

def room_temp() :
    global builtin_temp
    builtin_temp_voltage = builtin_temp.read_u16() * (3.3 / (65536))
    temperature_celcius = 27 - (builtin_temp_voltage - 0.706)/0.001721
    temp_fahrenheit=32+(1.8*temperature_celcius)
    #print("Temperature: {}°C {}°F".format(temperature_celcius,temp_fahrenheit))
    return temp_fahrenheit


def read_therm() :
    global BALANCE_RESISTOR, MAX_ADC
    adc_average = sensor.read_u16()
    ROOM_TEMP = room_temp()
    rThermistor = BALANCE_RESISTOR * ( (MAX_ADC / adc_average) - 1);
    tKelvin = (BETA * ROOM_TEMP) / (BETA + (ROOM_TEMP * math.log(rThermistor / RESISTOR_ROOM_TEMP)));
    tCelsius = tKelvin - 273.15;
    return tCelsius

    
def get_set_temp() :
    global start_temp, target_temp, old_temp, r, jsonData
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

def get_current_temp() :
    global last_temp, current_temp
    if utime.ticks_ms() < last_temp + 1000:
        return current_temp
    last_temp = utime.ticks_ms()
    adc = sensor.read_u16()
    vout = (3.3/65535)*adc
    tempc = thermistor.thermistorTemp(vout)
    current_temp = int(round((tempc *9/5)+32, 0))
    #current_temp = 273 + int(round(read_therm(),0))
    return current_temp

def save_set_temp(temp):
    global jsonData
    jsonData["setTemp"]=temp
    try:
        with open('savedata.json', 'w') as f:
            json.dump(jsonData, f)
    except:
        print("Could not save the button state variable.")

def lcd_setup():

    lcd.putstr("It Works!")
#

def lcd_status():
    
    get_current_temp()
    light_sensor_reading = light_sensor.read_u16()
#    if light_sensor.read_u16() > 10000:
#        if is_buzzer_setup():
#            playNote(buzzer, note, 1, .1)
#            print("beep")

    lcd_status_string = current_temp, target_temp, old_temp
    if heater_pause == 1:
        lcd_status_string1 = str(lcd_status_string)
        lcd_status_string2 =  "OFF " + str(light_sensor_reading)
    else:
        lcd_status_string1 = str(lcd_status_string)
        lcd_status_string2 =  "ON  " + str(light_sensor_reading)
        
    lcd.clear()
    lcd.move_to(0,0)
    lcd.putstr(lcd_status_string1)
    lcd.move_to(0,1)
    lcd.putstr(lcd_status_string2)

def show_status():
    get_current_temp()
    print("\n", utime.ticks_ms(), " - ", current_temp,":",target_temp,":",old_temp," ( current : target : setting )\n")

get_set_temp()

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
        get_current_temp()
        
    if utime.ticks_ms() > (last_print + 1000):
        #TIMER : PRINT CURRENT TEMP
        last_print = utime.ticks_ms()
        get_current_temp()
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
            blu.off()
            heater.off()
        
    sleep(.01)
    
    


