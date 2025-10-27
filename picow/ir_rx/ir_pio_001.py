
# sny_ir_receiver.py - A Pi Pico MicroPython based SNY IR receiver
# rev 1 - shabaz - October 2023

import time
from machine import Pin
from servo import Servo
from rp2 import asm_pio, PIO, StateMachine

# IR sensor pin
ir_pin = Pin(15, Pin.IN, Pin.PULL_UP)

# Servo object
servo1 = Servo(16)

# some button defs
LEFT_NAV = 62
RIGHT_NAV = 63
UP_NAV = 58
DOWN_NAV = 59
CENTER_NAV = 57
RED_BTN = 72
RED_BTN2 = 45
TRASH_BTN = 61

# sny_ir_rx PIO code
@asm_pio(autopush=True, push_thresh=21, in_shiftdir=PIO.SHIFT_RIGHT, fifo_join=PIO.JOIN_RX)
def sny_ir_rx():
    wrap_target()
    label("idle_start")
    mov(isr, null) # clear isr
    # determine if the idle length is long, to identify new button presses
    set(y, 31)     # set y to 31 (outer loop counter)
    label("outer_long_idle_loop")
    set(x, 31)     # set x to 31 (inner loop counter)
    label("inner_long_idle_loop")
    jmp(pin, "still_idle_loop")  # if pin is still high, we are still in idle state
    set(x, 0)     # the pin has gone low. set the idle value to 0 
    jmp("possible_burst_started")
    label("still_idle_loop")
    jmp(x_dec, "inner_long_idle_loop")  # loop until the timer expires
    jmp(y_dec, "outer_long_idle_loop")
    # ok if we are here then the idle state is long, and the start burst has not begun
    label("long_idle")
    set(x, 1)  # set the idle value to 1
    wait(0, pin, 0)  # wait for IDLE->START_BURST to occue (i.e. logic low)
    label("possible_burst_started")
    in_(x, 1)  # put the idle delay length indication into the Input Shift Register
    set(x, 27) # BURST_LOOP_COUNTER is 27
    label("burst_test")
    jmp(pin, "idle_start")  # if the START_BURST ends too soon then go back!
    jmp(x_dec, "burst_test")  # loop until the timer expires
    label("burst_confirmed")
    #  ok the burst is long enough, so now wait for the end of the start burst
    set(y, 19) # NUM_BITS is 19 (20 bits in the SNY protocol)
    wait(1, pin, 0)  # wait for the start burst to finish, i.e. pin to go high
    label("bit_start")
    nop().delay(15) # BIT_WIDTH_UNIT-1 = 15. Wait for the bit high period to finish
    label("bit_start_subsequent")
    nop().delay(6) # BIT_WIDTH_HALF_UNIT-2 = 6. Wait for window to see bit value
    set(x, 8)  # BIT_WIDTH_HALF_UNIT (300usec, multiplied by 2 clock cycles per loop)
    label("bit_wait_to_sample")
    jmp(pin, "bit_value_0")  # if pin goes high during loop, then bit is value 0
    jmp(x_dec, "bit_wait_to_sample")  # loop until the window expires
    # ok the window expired so the bit value is 1
    label("bit_value_1")
    set(x, 1)  # set the bit value to 1
    in_(x, 1)  # put the bit value into the ISR
    wait(1, pin, 0)  # wait for the next bit to start
    nop().delay(13)  # BIT_WIDTH_UNIT-3 = 13 (wait for bit high period to finish)
    jmp("ready_for_next_bit")
    label("bit_value_0")
    set(x, 0)  # set the bit value to 0
    in_(x, 1)  # put the bit value into the ISR
    nop().delay(12)  # BIT_WIDTH_UNIT-4 = 12 (wait for bit high period to finish)
    label("ready_for_next_bit")
    jmp(y_dec, "bit_start_subsequent")  # now read the next bit!
    jmp("idle_start")  # Y is zero, so 20 bits have completed. We are done!
    wrap()


# set up and start the PIO state machine
# freq is 26.667kHz, GPIO base pin is 15
sm = StateMachine(0, sny_ir_rx, freq=26667, in_base=ir_pin, jmp_pin=ir_pin)
sm.active(1)

def decode_frame(frame):
    extended_device = (frame >> 24) & 0xff
    sny_device = (frame >> 19) & 0x1f
    sny_command = (frame >> 12) & 0x7f
    first_press = (frame >> 11) & 0x01
    return (first_press, sny_device, sny_command, extended_device)

def print_frame(frame):
    (first_press, device, command, extdevice) = decode_frame(frame)
    if first_press:
        print(f"rx 0x{frame:08x}: {device}.{extdevice}, command={command}")
    else:
        print(f"    repeat 0x{frame:08x}: {device}.{extdevice}, command={command}")

def get_frame(wait_for_frame):
    frame = 0
    if wait_for_frame:
        frame = sm.get()
    else:
        if sm.rx_fifo()>0:
            frame = sm.get()
        else:
            frame = 0  # nothing in the FIFO yet
    return frame

def servo_app():
    pos = 0
    step = 10
    servo1.move(pos)
    while True:
        f = get_frame(False)
        if (f > 0):
            (first_press, dev, cmd, extdev) = decode_frame(f)
            if dev==26 and extdev == 241:
                if cmd==LEFT_NAV:
                    pos = pos - step
                    if pos < -90:
                        pos = -90
                if cmd == RIGHT_NAV:
                    pos = pos + step
                    if pos > 90:
                        pos = 90
                if cmd == CENTER_NAV:
                    pos = 0
                servo1.move(pos)
        time.sleep(0.01)


servo_app()