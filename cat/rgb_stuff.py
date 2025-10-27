from machine import Pin, PWM
from utime import ticks_ms as ticks

rgb_ds_max = 65535
rgb_freq = 1000
rgb_r_pin = Pin(11, Pin.OUT)
rgb_g_pin = Pin(12, Pin.OUT)
rgb_b_pin = Pin(13, Pin.OUT)
rgb_r = PWM(rgb_r_pin, freq=rgb_freq, duty_u16=rgb_ds_max)
rgb_g = PWM(rgb_g_pin, freq=rgb_freq, duty_u16=rgb_ds_max)
rgb_b = PWM(rgb_b_pin, freq=rgb_freq, duty_u16=rgb_ds_max)

rgb_r_val = 0
rgb_g_val = 0
rgb_b_val = 0
def last_rgb():
    global last_rgb
    if last_rgb > 0:
        return last_rgb
    return ticks()

def set_rgb(r, g, b, static=1) :
    global rgb_r_val,rgb_g_val, rgb_b_val
    if static == 0:
        rgb_r_val += r
        if rgb_r_val > 65535:
            rgb_r_val = r
        rgb_r.duty_u16(rgb_r_val)
        
        rgb_g_val += g
        if rgb_g_val > 65535:
            rgb_g_val = g
        rgb_g.duty_u16(rgb_g_val)

        rgb_b_val += b
        if rgb_b_val > 65535:
            rgb_b_val = b
        rgb_b.duty_u16(rgb_b_val)
    else:
        rgb_r.duty_u16(r)
        rgb_g.duty_u16(g)
        rgb_b.duty_u16(b)
    print("r=", r, "; g=", g, "; b=", b, "static=", static)

last_rgb = 1
set_rgb(0,0,0,1)

def rgb_loop (last_target, last_sw) :
    global last_rgb
    #timer rgb update
    if ticks() > 1000 + last_rgb:
        last_rgb = ticks()
        set_rgb(last_rgb % 65535, last_target % 65535,last_sw % 65535, 1)

