def basic_script():
    return(True)

#pins
# 4            builtin_temp_sensor
# 14           button w/ grn led
# 15           red led
# 16           buzzer
# 18,19,20     rotary encoder
# 12,13        i2c lcd
# 28,27,26     adc2 adc1 adc0 microphone(s)
#
#

#config modules

buzzer_enabled = False 
rotary_enabled = True
lcd_enabled = True
mic1_enabled = False
mic2_enabled = False
ir_rx_enabled = False 
html_controler_enabled = False  

from machine import ADC,PWM,Pin
import time
builtin_temp_pin = 4

red_pin = 15
red = Pin(red_pin, Pin.OUT)

grn_pin = 14
grn_switch = Pin(grn_pin, Pin.IN, Pin.PULL_DOWN)


if html_controler_enabled == True:
    try:
        if html_controler() == True:
            pass
    except:
        import html_controler
        
    wlan = html_controler.boot.wlan
#    wlan = network.WLAN(network.STA_IF)
    ip=wlan.ifconfig()[0]

    # rgb led
    red=machine.Pin(13,machine.Pin.OUT)
    green=machine.Pin(14,machine.Pin.OUT)
    blue=machine.Pin(15,machine.Pin.OUT)

    # Temperature Sensor

    conversion_factor = 3.3 / (65535)
            
        
if ir_rx_enabled :
    # VS1838B ir reciever
    ir_rcv_pin = 2 # pico pin 4 = gpio pin 2
    """
    vs1838B pins:
    1: signal
    2: ground
    3: vcc
    """

    import utime
    from machine import Pin

    ird = Pin(ir_rcv_pin,Pin.IN)

    act = {"1": "LLLLLLLLHHHHHHHHLHHLHLLLHLLHLHHH","2": "LLLLLLLLHHHHHHHHHLLHHLLLLHHLLHHH","3": "LLLLLLLLHHHHHHHHHLHHLLLLLHLLHHHH",
           "4": "LLLLLLLLHHHHHHHHLLHHLLLLHHLLHHHH","5": "LLLLLLLLHHHHHHHHLLLHHLLLHHHLLHHH","6": "LLLLLLLLHHHHHHHHLHHHHLHLHLLLLHLH",
           "7": "LLLLLLLLHHHHHHHHLLLHLLLLHHHLHHHH","8": "LLLLLLLLHHHHHHHHLLHHHLLLHHLLLHHH","9": "LLLLLLLLHHHHHHHHLHLHHLHLHLHLLHLH",
           "0": "LLLLLLLLHHHHHHHHLHLLHLHLHLHHLHLH","Up": "LLLLLLLLHHHHHHHHLHHLLLHLHLLHHHLH","Down": "LLLLLLLLHHHHHHHHHLHLHLLLLHLHLHHH",
           "Left": "LLLLLLLLHHHHHHHHLLHLLLHLHHLHHHLH","Right": "LLLLLLLLHHHHHHHHHHLLLLHLLLHHHHLH","Ok": "LLLLLLLLHHHHHHHHLLLLLLHLHHHHHHLH",
           "*": "LLLLLLLLHHHHHHHHLHLLLLHLHLHHHHLH","#": "LLLLLLLLHHHHHHHHLHLHLLHLHLHLHHLH"}

    def read_ircode(ird):
        wait = 1
        complete = 0
        seq0 = []
        seq1 = []

        #print("read_ircode wait = 1")
        start = utime.ticks_us()
        while wait == 1:
            ms0 = utime.ticks_us()
            diff = utime.ticks_diff(ms0,start)
            if diff > 10000:
                wait = 0
                complete = 1
         #       print("ir_rx timeout")

            #print(ird.value())
            
            if ird.value() == 0:
                wait = 0
        while wait == 0 and complete == 0:
            start = utime.ticks_us()
          #  print("start:", start)
            while ird.value() == 0:
                ms1 = utime.ticks_us()
            diff = utime.ticks_diff(ms1,start)
            seq0.append(diff)
            while ird.value() == 1 and complete == 0:
                ms2 = utime.ticks_us()
                diff = utime.ticks_diff(ms2,ms1)
                if diff > 10000:
                    complete = 1
            seq1.append(diff)

        code = ""
        for val in seq1:
            if val < 2000:
                if val < 700:
                    code += "L"
                else:
                    code += "H"
        print("ir_rx code:", code)
        command = ""
        for k,v in act.items():
            if code == v:
                command = k
        if command == "":
            command = code
        return command
        
    
if buzzer_enabled :
    import buzzer
    #from buzzer import note, playNote, buzzer, BUZZER_PIN, is_buzzer_setup
    BUZZER_PIN = 16 # Piezo buzzer + is connected to GP6, - is connected to the GND right beside GP6
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))
    note = 784
    from buzzer import playNote
    playNote(buzzer, note,.1,.1)


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

lcd_setup()
#end lcd support section


if mic1_enabled :
    mic1_pin = 27 #adc1
    mic1 = Pin(mic1_pin, Pin.IN, Pin.PULL_DOWN)
    mic1_sensor = ADC(mic1_pin)
    mic1_reading = mic1_sensor.read_u16()
    mdata = mic1_reading
    print(mic1_reading)

if mic2_enabled :
    mic2_pin = 26 #adc0
    mic2_pin = Pin(mic2_pin, Pin.IN, Pin.PULL_DOWN)
    mic2_sensor = ADC(mic2_pin)
    mic2_reading = mic2_sensor.read_u16()
    mdata = mic2_reading

    print(mic2_reading)


#main loop
while True:

    if mic1_enabled :
        mic1_reading = mic1_sensor.read_u16()
        print(str(mic1_reading))
        if lcd_enabled:
            lcd_status(str(mic1_reading), "")
    if mic2_enabled :
        mic2_reading = mic2_sensor.read_u16()
        print(str(mic2_reading))
        if lcd_enabled:
            lcd_status("", str(mic2_reading))

    if rotary_enabled :
        if en_sw.value() == 0:
            if last_en_sw == 1:
                print("encoder switch pressed")
                if lcd_enabled:
                    lcd_status("", "pressed")
                last_en_sw = en_sw.value()
                
        if en_sw.value() == 1:
            if last_en_sw == 0:
                print("encoder switch released")
                if lcd_enabled:
                    lcd_status("", "released")
                last_en_sw = en_sw.value()
        if last_rval != r.value():
            last_rval = r.value()
            print("encoder value changed to ", r.value())        
            if lcd_enabled:
                lcd_status("", r.value())

    if ir_rx_enabled :
        command = read_ircode(ird)
        print(command)
        
    if html_controler_enabled == True:

        lcd_status("", html_controler.html_result())
        try:
            if ip is not None:
                connection=open_socket(ip)
                serve(connection)
        except KeyboardInterrupt:
            machine.reset()
            
    time.sleep(.1)