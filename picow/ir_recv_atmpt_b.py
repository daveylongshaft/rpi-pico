import machine
import utime
from machine import Pin


ir_out_pin = 14
ir_out = Pin(ir_out_pin, Pin.OUT)

ir_in_pin = 15
ir_in = Pin(ir_in_pin, Pin.IN, Pin.PULL_DOWN)
act = {"off": "HHHHLLLHLLLLHHHLHHHHLHHHHLLLLLLLLH",
       "1": "LLLLLLLLHHHHHHHHLHHLHLLLHLLHLHHH","2": "LLLLLLLLHHHHHHHHHLLHHLLLLHHLLHHH","3": "LLLLLLLLHHHHHHHHHLHHLLLLLHLLHHHH",
       "4": "LLLLLLLLHHHHHHHHLLHHLLLLHHLLHHHH","5": "LLLLLLLLHHHHHHHHLLLHHLLLHHHLLHHH","6": "LLLLLLLLHHHHHHHHLHHHHLHLHLLLLHLH",
       "7": "LLLLLLLLHHHHHHHHLLLHLLLLHHHLHHHH","8": "LLLLLLLLHHHHHHHHLLHHHLLLHHLLLHHH","9": "LLLLLLLLHHHHHHHHLHLHHLHLHLHLLHLH",
       "0": "LLLLLLLLHHHHHHHHLHLLHLHLHLHHLHLH","Up": "LLLLLLLLHHHHHHHHLHHLLLHLHLLHHHLH","Down": "LLLLLLLLHHHHHHHHHLHLHLLLLHLHLHHH",
       "Left": "LLLLLLLLHHHHHHHHLLHLLLHLHHLHHHLH","Right": "LLLLLLLLHHHHHHHHHHLLLLHLLLHHHHLH","Ok": "LLLLLLLLHHHHHHHHLLLLLLHLHHHHHHLH",
       "*": "LLLLLLLLHHHHHHHHLHLLLLHLHLHHHHLH","#": "LLLLLLLLHHHHHHHHLHLHLLHLHLHLHHLH"}

def read_ircode(ird):
    length = 0
    wait = 1
    complete = 0
    offseq0 = []
    onseq1 = []
    oldval = 0
    #print("BEGIN: read_ircode(); wait = 1")
    start = utime.ticks_us()
    while wait == 1:
        ms0 = utime.ticks_us()
        diff = utime.ticks_diff(ms0,start)
        ir_out.value(1)
        if diff > 10000:
            wait = 0
            complete = 1
            ir_out.value(0)
            #print("ir_rx timeout")
        newval = ird.value()
        if newval != oldval:
            oldval = newval
            #print(newval)
            ir_out.value(1)
        if newval == 1:
            wait = 0
    while wait == 0 and complete == 0:
        start = utime.ticks_us()
        #print("start:", start)
        while newval == 1:
            newval = ird.value()
            if newval != oldval:
                oldval = newval
                #print(newval)
            ms1 = utime.ticks_us()
        diff = utime.ticks_diff(ms1,start)
        offseq0.append(diff)
        while newval == 0 and complete == 0:
            newval = ird.value()
            if newval != oldval:
                oldval = newval
                #print(newval)            
            ms2 = utime.ticks_us()
            diff = utime.ticks_diff(ms2,ms1)
            if diff > 10000:
                complete = 1
        onseq1.append(diff)
        length += 1
        if length > 27:
            complete = 1
            print("complete")

    code = ""
    if length > 9:
        print("length = ", length)
        for off_dur in offseq0 :
            on_dur = onseq1.pop()
            print(off_dur, on_dur)
            if off_dur < 100:
                #code += "l"
                pass
            else:
                if off_dur > 2000:
                    complete = 1
                    #print("timeout - off step.  length = ", length)
                else:
                    #code += "h"
                    pass
            if on_dur < 700:
                code += "L"
            else:
                if on_dur > 2000:
                    complete = 1
                    #print("timeout - on step.  length = ", length)
                else:
                    code += "H"
        if len(code) > 1:
            print("code:", code)

    if False:
        for val in onseq1:
            if val < 2000:
                if val < 700:
                    code += "L"
                else:
                    code += "H"
        if len(code) > 1:
            print("ir_rx 1 code:", code)


    command = ""
    for k,v in act.items():
        if code == v:
            command = k
    if command == "":
        command = code
    if len(command) > 0:
        print("command: ", command)
    return command
    
try:
    while True:
        read_ircode(ir_in)
        #utime.sleep_ms(50)
except KeyboardInterrupt:
    print("end")
    

