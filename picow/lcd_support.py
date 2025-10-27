import machine
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16
i2c_sda_pin = 0
i2c_scl_pin = 1
i2c = I2C(0, sda=machine.Pin(i2c_sda_pin), scl=machine.Pin(i2c_scl_pin), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

def lcd_setup():
    lcd.move_to(0,0)
    lcd.putstr("                ")
    lcd.move_to(0,1)
    lcd.putstr("                ")
    
def lcd_status(str1="", str2=""):
    
    lcd_status_string1 = str(str1) #("                ")
    lcd_status_string2 = str(str2) #("                ")
        
    if len(lcd_status_string1) > 0:
        lcd.move_to(0,0)
        lcd.putstr("                ")
        lcd.move_to(0,0)
        lcd.putstr(lcd_status_string1)
    if len(lcd_status_string2) > 0:
        lcd.move_to(0,1)
        lcd.putstr("                ")
        lcd.move_to(0,1)
        lcd.putstr(lcd_status_string2)

#end lcd support section


