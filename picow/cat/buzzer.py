from machine import Pin, PWM
import utime

BUZZER_PIN = 16 # Piezo buzzer + is connected to GP6, - is connected to the GND right beside GP6
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))
note = 784

def playNote(buzzer, frequency, duration, pause) :
    #global buzzer
    buzzer.duty_u16(5000)  # adjust loudness: smaller number is quieter.
    buzzer.freq(frequency)
    utime.sleep(duration)
    buzzer.duty_u16(0) # loudness set to 0 = sound off
    utime.sleep(pause)
    
def is_buzzer_setup():
    global is_buzzer_setup_flag
    if is_buzzer_setup_flag == True:
        return True
    else:
        is_buzzer_setup_flag = True
        return is_buzzer_setup_flag

        buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT))
        return is_buzzer_setup_flag

#playNote(note,.1,.01)