#pins
# 4            builtin_temp_sensor
# 18,19,20     rotary encoder
# 0,1       i2c lcd
# 28,27,26     adc2 adc1 adc0
#
#
import pinout
pinout.pinout()

#config modules

rotary_enabled = True
lcd_enabled = True

from machine import ADC,PWM,Pin
import time
builtin_temp_pin = 4


#rotary encoder w/ switch support
if rotary_enabled :
    import rotary
    import rotary_irq_rp2
    from rotary_irq_rp2 import RotaryIRQ
    en_clk_pin = 18
    en_dt_pin = 19
    en_sw_pin = 20
    en_sw = Pin(en_sw_pin, Pin.IN, Pin.PULL_DOWN)
    last_en_sw = en_sw.value()
    
    r = RotaryIRQ(
        pin_num_clk=en_clk_pin,
        pin_num_dt=en_dt_pin,
        reverse=True,
        incr=1,
        range_mode=RotaryIRQ.RANGE_UNBOUNDED,
        pull_up=True,
        half_step=False,
    )
    last_rval = r.value()

#end rotary encoder w/ switch support section

#lcd support 16x2
if lcd_enabled :
    from machine import I2C 
    from lcd_api import LcdApi
    from pico_i2c_lcd import I2cLcd
    I2C_ADDR = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16
    i2c_sda_pin = 0
    i2c_scl_pin = 1
    i2c = I2C(0, sda=machine.Pin(i2c_sda_pin), scl=machine.Pin(i2c_scl_pin), freq=400000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

def lcd_setup():
    lcd_status("   lcd          ","      ready     ")
    time.sleep(1)
    lcd_clear()

def lcd_clear():
    lcd_status("                ","                ")    
    
def lcd_status(str1="", str2=""):
    
    lcd_status_string1 = str(str1) #("                ")
    lcd_status_string2 = str(str2) #("                ")
        
    if len(lcd_status_string1) > 0:
        lcd.move_to(0,0)
        lcd.putstr("                ")
        lcd.move_to(0,0)
        lcd.putstr(lcd_status_string1)
        print(lcd_status_string1)
    if len(lcd_status_string2) > 0:
        lcd.move_to(0,1)
        lcd.putstr("                ")
        lcd.move_to(0,1)
        lcd.putstr(lcd_status_string2)
        print(lcd_status_string2)

lcd_setup()
#end lcd support section


#main loop
while True:

    if rotary_enabled :
        if en_sw.value() == 0:
            if last_en_sw == 1:
                if lcd_enabled:
                    lcd_status("", "pressed")
                last_en_sw = en_sw.value()
                
        if en_sw.value() == 1:
            if last_en_sw == 0:
                if lcd_enabled:
                    lcd_status("", "released")
                last_en_sw = en_sw.value()
        if last_rval != r.value():
            last_rval = r.value()
            if lcd_enabled:
                lcd_status("", r.value())

    time.sleep(.1)