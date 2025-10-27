# boot.py
class boot():
    def boot(self):
        return(True)
    def __init__(self):
        self.wlan = wlan
        return self
    
    
from machine import UART
import os
uart = UART(0, 115200)
os.dupterm(uart)

import machine
import socket
import math
import utime
import network
import time
# enable station interface and connect to WiFi access point
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('ATT-WIFI-4869', 'mFjYjRj7')
# now use sockets as usual
while not wlan.isconnected():
    pass
print(wlan.ifconfig())
print('connected')

ip=wlan.ifconfig()[0]
print('http://{}/'.format(ip))
                
