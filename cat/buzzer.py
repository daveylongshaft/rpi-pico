from machine import Pin, PWM
import utime

BUZZER_PIN = 16 # Piezo buzzer + is connected to GP6, - is connected to the GND right beside GP6
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))
note = 784

def playNote(frequency, duration, pause) :
    global buzzer
    buzzer.duty_u16(5000)  # adjust loudness: smaller number is quieter.
    buzzer.freq(frequency)
    utime.sleep(duration)
    buzzer.duty_u16(0) # loudness set to 0 = sound off
    utime.sleep(pause)
    
def is_buzzer_setup():
    global is_buzzer_setup_flag
    if is_buzzer_setup_flag == True:
        return is_buzzer_setup_flag
    else:
        is_buzzer_setup_flag = True
        global buzzer, BUZZER_PIN
        buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))
        return is_buzzer_setup_flag

playNote(note,1,.01)
notes = [{'a2':110},{'b2':123.471},{'c2':64.4064},{'d2':73.4162},{'e2':82.4096},{'f2':87.3071},{'g2':97.9989}]

for f in notes:
    #print(n)
    playNote(f,1,.02)