# boot.py
def boot():
    return(True)

# Original UART setup is commented out to prevent REPL conflict
# from machine import UART
# import os
# uart = UART(0, 115200)
# os.dupterm(uart)

import machine
import socket
import math
import utime
import network
import time
# enable station interface and connect to WiFi access point
nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect('ANTEATER2', 'Juliaz13')
# now use sockets as usual
while not nic.isconnected():
    pass
print(nic.ifconfig())
wlan = nic
 
# Wait for connect or fail
wait = 10
while wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    wait -= 1
    print('waiting for connection...')
    time.sleep(1)
 
# Handle connection error
if wlan.status() != 3:
    raise RuntimeError('wifi connection failed')
else:
    print('connected')
    ip=wlan.ifconfig()[0]
    print('http://{}/'.format(ip))
                
