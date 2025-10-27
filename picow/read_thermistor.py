
import utime
from machine import ADC,PWM,Pin
from time import sleep
import thermistor
import rotary
import rotary_irq_rp2
from rotary_irq_rp2 import RotaryIRQ
en_clk = 18
en_dt = 19
en_sw = 20
last_print = utime.ticks_ms()
r = RotaryIRQ(
    pin_num_clk=en_clk,
    pin_num_dt=en_dt,
    reverse=True,
    incr=1,
    range_mode=RotaryIRQ.RANGE_UNBOUNDED,
    pull_up=True,
    half_step=False,
)
sw = Pin(en_sw, Pin.IN, Pin.PULL_UP)
val_old = r.value() + 35
target_val = val_old

BUZZER_PIN = 16 # Piezo buzzer + is connected to GP6, - is connected to the GND right beside GP6
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))

note = 784

adcpin = 4
sensor = ADC(adcpin)
 
adcpin = 26
sensor = ADC(adcpin)
grn = Pin(15, Pin.OUT)
switch = Pin(14, Pin.IN, Pin.PULL_DOWN)


def playNote(frequency, duration, pause) :
    global buzzer
    buzzer.duty_u16(5000)  # adjust loudness: smaller number is quieter.
    buzzer.freq(frequency)
    time.sleep(duration)
    buzzer.duty_u16(0) # loudness set to 0 = sound off
    time.sleep(pause)
last_r = 1
last_sw = 1
last_target = 1
last_current = 1
current_temp = 1
last_temp = 1
while True:
      
    if switch.value():
        if utime.ticks_ms() >  1000 + last_target:
            last_target = utime.ticks_ms()
            target_val = r.value() + 35
            print(" set target = ", target_val)

    if not sw.value():
        if utime.ticks_ms() > 1000 + last_sw:
            last_sw = utime.ticks_ms()
            #en_sw pressed
            val_old = r.value() + 35
            print(" renc.value = ", val_old)
            print(" target_val = ", target_val)
            
    if r.value() + 35 != val_old:
        if utime.ticks_ms() > 1000 + last_r:
            last_r = utime.ticks_ms()
            val_old = r.value() + 35
            print(" renc.value = ", val_old)
        
    if utime.ticks_ms() > (last_temp + 100):
        last_temp = utime.ticks_ms()
        adc = sensor.read_u16()
        Vout = (3.3/65535)*adc
        TempC = thermistor.thermistorTemp(Vout)
        current_temp = int(round(TempC, 0))
    
    if utime.ticks_ms() > (last_print + 10000):
        last_print = utime.ticks_ms()
        if last_current != current_temp:
            last_current = current_temp
            print("current temp: ", current_temp)

    if current_temp >= target_val:
        grn.on()
    else:
        grn.off()
    sleep(.01)
    
