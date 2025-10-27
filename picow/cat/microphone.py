#pins
# 4            builtin_temp_sensor
# 18,19,20     rotary encoder
# 12,13        i2c lcd
# 27           adc2 microphone
#
#

from machine import ADC,PWM,Pin
import time
builtin_temp_pin = 4



#end config file support 
import ujson as json
jsonData = {"config_key": "config_value"}  #default_value

def get_config() :
    global jsonData
    try:
        with open('savedata.json', 'r') as f:
            data = json.load(f)
            config_key = data["config_key"]
    except:
        config_key = 1 #default value
        print("config_key not found.")

    jsonData = {"config_key": config_key}

def put_config():
    global jsonData 
    jsonData = {"config_key":"config_value"}
    try:
        with open('savedata.json', 'w') as f:
            json.dump(jsonData, f)
    except:
        print("Could not save the button state variable.")
        
#end config file support section


#rotary encoder w/ switch support
import rotary
import rotary_irq_rp2
from rotary_irq_rp2 import RotaryIRQ
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
#end rotary encoder w/ switch support section

#lcd support 16x2
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16
i2c_sda_pin = 12
i2c_scl_pin = 13

i2c = I2C(0, sda=machine.Pin(i2c_sda_pin), scl=machine.Pin(i2c_scl_pin), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

def lcd_setup():
    lcd.putstr("lcd setup")
    
def lcd_status(str1="", str2=""):
    
    lcd_status_string1 = str(str1) #("                ")
    lcd_status_string2 = str(str2) #("                ")
        
    lcd.clear()
    lcd.move_to(0,0)
    lcd.putstr(lcd_status_string1)
    lcd.move_to(0,1)
    lcd.putstr(lcd_status_string2)

lcd_setup()
#end lcd support section



mic_pin = 27 #adc1
mic = Pin(mic_pin, Pin.IN, Pin.PULL_UP)
mic_sensor = ADC(mic_pin)
mic_reading = mic_sensor.read_u16()


#main loop
while True:

    mic_reading = mic_sensor.read_u16()
    lcd_status("mic_reading:", mic_reading)
    time.sleep(.1)