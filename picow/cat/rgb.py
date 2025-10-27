from random import randint as rand
from machine import Pin, PWM
from utime import ticks_ms
rgb_ds_max = 65535
rgb_freq = 1000

R_PIN = 11
G_PIN = 12
B_PIN = 13

rgb_r = PWM(Pin(R_PIN, Pin.OUT), freq=rgb_freq, duty_u16=rgb_ds_max)
rgb_g = PWM(Pin(G_PIN, Pin.OUT), freq=rgb_freq, duty_u16=rgb_ds_max)
rgb_b = PWM(Pin(B_PIN, Pin.OUT), freq=rgb_freq, duty_u16=rgb_ds_max)

rgb_r_val = 0
rgb_g_val = 0
rgb_b_val = 0

def set_rgb(r, g, b, static=1) :
    global rgb_r_val,rgb_g_val, rgb_b_val
    if static == 0:
        rgb_r_val += r
        if rgb_r_val > 65535:
            rgb_r_val = rgb_ds_max
        elif rgb_r_val < 1000:
            rgb_r_val = 1000
        
        rgb_g_val += g
        if rgb_g_val > 65535:
            rgb_g_val = rgb_ds_max
        elif rgb_g_val < 1000:
            rgb_g_val = 1000
        
        rgb_b_val += b
        if rgb_b_val > 65535:
            rgb_b_val = rgb_ds_max
        elif rgb_b_val < 1000:
            rgb_b_val = 1000
            
        rgb_r.duty_u16(rgb_r_val)
        rgb_g.duty_u16(rgb_g_val)
        rgb_b.duty_u16(rgb_b_val)
    else:
        rgb_r.duty_u16(r)
        rgb_g.duty_u16(g)
        rgb_b.duty_u16(b)
    print("r=", r, "; g=", g, "; b=", b, "static=", static)

last_rgb = 1
set_rgb(0,0,0,1)

def rgb_loop() :
    global last_rgb
    #timer rgb update
    if ticks_ms() > 1000 + last_rgb:
        last_rgb = ticks_ms()
        r = rand(1000,65535)
        g = rand(1000,65535)
        b = rand(1000,65535)
        set_rgb(r,g,b, 1)

