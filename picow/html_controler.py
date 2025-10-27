import machine
import socket
import math
import utime
import network
import time

class html_controler():
    def __init__(self):
        self.boot = boot
        self.html_request = html_request
        return self
    def html_controler():
        return(True)


try:
    if boot() == True:
        pass
except:
    import boot

# enable station interface and connect to WiFi access point
# is done in boot.py
#start here after boot.py using wlan object for network access

# rgb led
red=machine.Pin(13,machine.Pin.OUT)
green=machine.Pin(14,machine.Pin.OUT)
blue=machine.Pin(15,machine.Pin.OUT)

# Temperature Sensor

conversion_factor = 3.3 / (65535)
 
def temperature():
    sensor_temp = machine.ADC(4)
    temperature_value = sensor_temp.read_u16() * conversion_factor 
    temperature_Celcius = 27 - (temperature_value - 0.706)/0.00172169/ 8 
    print(temperature_Celcius)
    utime.sleep(2)
    return temperature_Celcius
 
def webpage(value):
    html = f"""
            <!DOCTYPE html>
            <html>
            <body>
            <form action="./red">
            <input type="submit" value="red " />
            </form>
            <form action="./green">
            <input type="submit" value="green" />
            </form>
            <form action="./blue">
            <input type="submit" value="blue" />
            </form>
            <form action="./off">
            <input type="submit" value="off" />
            </form>
            <p>Temperature is {value} degrees Celsius</p>
            </body>
            </html>
            """
    return html

def html_result() :
    global html_request
    return(html_controler.html_request)

def serve(connection):
    global html_request
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            split_request = request.split()[1]
            split2_request = split_request.split('/')
            print(split2_request)
        except:
            pass
        if request.find('/led/') == 6:
            split_request = request.split()[1]
            split2_request = split_request.split('/')
            print(split2_request)
        #print(request)    
        request = split_request
        print(request)
        html_request = request
        lcd_status("", request)
        if request == '/off?':
            red.low()
            green.low()
            blue.low()
            lcd_status("", request)
        elif request == '/red?':
            red.high()
            green.low()
            blue.low()
        elif request == '/green?':
            red.low()
            green.high()
            blue.low()
        elif request == '/blue?':
            red.low()
            green.low()
            blue.high()
 
        value='%.2f'%temperature()    
        html=webpage(value)
        client.send(html)
        client.close()
 
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    try:
        connection.bind(address)
        connection.listen(1)
        print(connection)
        return(connection)
    except :
        machine.reset()
 

