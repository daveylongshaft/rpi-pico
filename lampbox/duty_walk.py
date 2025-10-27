from machine import Pin, ADC, PWM
from time import sleep


b = Pin(14,Pin.IN, Pin.PULL_DOWN)
m = PWM(Pin(21, Pin.OUT))    # create output pin on GPIO0
m.freq(1000)
pot = ADC(0)
print("pin26 value: ")
print(pot.read_u16())
print("pin14 value: ")

print(b.value())

bval = b.value()
bval_was = bval
x = 0
pval = 0
pstep = 1000
pause = 0
pmin = 25000
pmax = 65000
pboost = 5000
while True:
    bval = b.value()
    if bval != bval_was:
        bval_was = bval
        if bval == 0:
            print("button released")
            if pause == 0:
                pause = 1
                print("pause")
            else:
                pause = 0
                print("play")
    if pause == 0:
        pval = pval + pstep
        if pval > pmax:
            if pstep > 0:
                pstep = pstep * -1
            pval = pval + pstep
            print("counting down")
        if pval < pmin:
            if pstep < 0:
                pstep = pstep * -1
            pval = pmin + pstep
            print("counting up")
            m.duty_u16(pmin + pboost)
            sleep(.2)       
        print("pval == ", pval)
        m.duty_u16(pval)
        sleep(.5)
