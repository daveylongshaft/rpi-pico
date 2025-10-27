from machine import Pin
import utime

A = Pin(7, Pin.OUT)
B = Pin(8, Pin.OUT)
C = Pin(9, Pin.OUT)
A.low()
B.low()
C.low()
print("start")
run = True
try:
    while run == True:
        print("A")
        B.low()
        C.low()
        A.high()
        utime.sleep(1)
        print("B")
        A.low()
        C.low()
        B.high()
        utime.sleep(1)
        print("C")
        A.low()
        B.low()
        C.high()
        utime.sleep(1)

except KeyboardInterrupt as theInterrupt:
    print('interrupt')
    run = False
finally:
    A.low()
    B.low()
    C.low()
    print("done")


