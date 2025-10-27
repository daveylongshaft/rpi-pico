#@ i2c lcd important files and data

lcd_enabled = True

def lcd_pinout() :
    print("""
              ---usb---
 SDA   GP0   1  |o     o| 40  VBUS
 SCL   GP1   2  |o     o| 39  VSYS
       GND   3  |o     o| 38  GND
       GP2   4  |o     o| 37  3V3_EN
       GP3   5  |o     o| 36  3V3(OUT)
       GP4   6  |o     o| 35           ADC_VREF
       GP5   7  |o     o| 34  GP28     ADC2
       GND   8  |o     o| 33  GND      AGND
       GP6   9  |o     o| 32  GP27     ADC1
       GP7   10 |o     o| 31  GP26     ADC0
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
             -______-""")


if lcd_enabled :
    from machine import Pin
    from machine import I2C
    from lcd_api import LcdApi
    from pico_i2c_lcd import I2cLcd
    
    I2C_ADDR     = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16
    
    lcd_sda_pin = 0 #sda
    lcd_scl_pin = 1  #scl

    i2c = I2C(0, sda=Pin(lcd_sda_pin), scl=Pin(lcd_scl_pin), freq=400000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)


def lcd_blank():
    lcd.move_to(0,0)
    lcd.putstr("                ")
    lcd.move_to(0,1)
    lcd.putstr("                ")
    
def lcd_setup():
    lcd_blank()
    
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

#lcd_setup()
#end lcd support section
