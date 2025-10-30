# boot.py
# This file runs on boot, sets up Wi-Fi.

import machine
import socket
import utime
import network
import time

# --- DEBUG CONFIG ---
DEBUG = True # Keep debug on for boot sequence clarity
def DPRINT(s):
    if DEBUG:
        print(s)
# --- END DEBUG ---

DPRINT("--- boot.py: START ---")

# enable station interface and connect to WiFi access point
DPRINT("Boot: Initializing WLAN...")
nic = network.WLAN(network.STA_IF)
nic.active(True)
DPRINT("Boot: Connecting to ANTEATER2...")
nic.connect('ANTEATER2', 'Juliaz13') # Use your credentials

# now use sockets as usual
connect_start_time = utime.ticks_ms()
connect_timeout_ms = 20000 # 20 seconds
connected = False
while utime.ticks_diff(utime.ticks_ms(), connect_start_time) < connect_timeout_ms:
    if nic.isconnected():
        connected = True
        break
    DPRINT(f'Boot: waiting for connection... status={nic.status()}')
    time.sleep(1)

if connected:
    DPRINT("Boot: Wi-Fi connected. IP Config:")
    DPRINT(nic.ifconfig())
    # Make wlan object globally accessible for html_server.py
    # Use globals() dictionary for explicit global assignment
    globals()['wlan'] = nic
    DPRINT("Boot: 'wlan' object set globally.")
    DPRINT('Boot: Wi-Fi connection confirmed.')
    ip=nic.ifconfig()[0]
    DPRINT(f'Boot: Device IP: http://{ip}/')
else:
    DPRINT('Boot: FATAL: wifi connection failed or timed out')
    # Maybe try resetting or entering a safe mode? For now, just print.
    # Optionally deactivate WLAN to save power if connect fails?
    # nic.active(False)

DPRINT("--- boot.py: END ---")