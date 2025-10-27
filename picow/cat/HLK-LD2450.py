from machine import UART, Pin
import time

uart1 = UART(1, baudrate=256000, tx=Pin(4), rx=Pin(5))

#uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

txData = b'hello world\n\r'
#uart1.write(txData)
while True:
    time.sleep(0.1)
    rxHeader = bytes()
    rxTarget1 = bytes()
    rxTarget2 = bytes()
    rxTarget3 = bytes()
    rxFooter = bytes()    
    rxData = bytes()
    while uart1.any() > 0:
        rxHeader += uart1.read(4)
        if rxHeader == b'\xaa\xff\x03\x00':
            rxTarget1 += uart1.read(8)
            rxTarget2 += uart1.read(8)
            rxTarget3 += uart1.read(8)
            rxFooter += uart1.read(2)
            while uart1.any() > 0:
                rxData += uart1.read(1)
        else:
            while uart1.any() > 0:
                rxData += uart1.read(1)

    if rxHeader == b'\xaa\xff\x03\x00':

        print("Header: ", rxHeader)
        
        print("Target1: ", rxTarget1)
        xCord = 0 - (rxTarget1[0] + rxTarget1[1] * 256)
     