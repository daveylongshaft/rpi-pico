from machine import UART
import time, utime
import struct

ser = UART(1, 256000)
ser.init(256000, bits=8, parity=None, stop=1, tx=4, rx=5)
print("serial begin")
last_result = 0

class targets:
    def __init__(self, target_a, target_b, target_c):
        self.target_a = target_a
        self.target_b = target_b
        self.target_c = target_c

class target_data:
    def __init__(self, data):
        self.x = 0 - (struct.unpack('<B', data[0:1])[0] + ( struct.unpack('<B', data[1:2])[0] * 256))
        self.y = 0 + (struct.unpack('<B', data[2:3])[0] + (struct.unpack('<B', data[3:4])[0] * 256 ) - (2^15))
        self.speed = 0 - (struct.unpack('<B', data[4:5])[0] + ( struct.unpack('<B', data[5:6])[0] * 256))
        self.resolution = 0 + (struct.unpack('<B', data[6:7])[0] + ( struct.unpack('<B', data[7:8])[0] * 256))
        print("target_data initialized")

# Function to read data and process targets
def read_radar_data():
    header = bytes()
    header = ser.read(4)
    if header != 0:
        print("header:", header)
    if header == b'\xaa\xff\x03\x00':
        target_a = target_data(ser.read(8))
        target_b = target_data(ser.read(8))
        target_c = target_data(ser.read(8))
        footer = ser.read(2)
        if footer == b'\x55\xcc':
            print("footer correct.  ")
            print("frame begin")
            print("header: {", header, "}")
            print("target_a: {")
            print("x", target_a.x)
            print("y", target_a.y)
            print("s", target_a.speed)
            print("r", target_a.resolution, "}")
            
            print("target_b: {")
            print("x", target_b.x)
            print("y", target_b.y)
            print("s", target_b.speed)
            print("r", target_b.resolution, "}")

            print("target_c: {")
            print("x", target_c.x)
            print("y", target_c.y)
            print("s", target_c.speed)
            print("r", target_c.resolution, "}")

            print("footer: {", footer, "}")
            print("frame complete")
            time.sleep(1)
            if ser.any() > 0:
                ser.read(ser.any()) # Clear remaining data

def target_math():
    print("""
            target_ax1 = int(ser.read(1))
            target_ax2 = int(ser.read(1))
            target_ay1 = int(ser.read(1))
            target_ay2 = int(ser.read(1))
            target_as1 = int(ser.read(1))
            target_as2 = int(ser.read(1))            
            target_ar1 = int(ser.read(1))
            target_ar2 = int(ser.read(1))
            target_ax = 0 - ((target_ax1) + ((target_ax2) * 256))
            target_ay = 0 + (((target_ay1) + ((target_ay2) * 256)) - (2^15))
            target_as = 0 - ((target_as1) + ((target_as2) * 256))
            target_ar = 0 + ((target_ar1) + ((target_ar2) * 256))
            print("TargetA : X = ", target_ax, "; Y = ", target_ay, "; S = ", target_as, "; R = ", target_ar)
    """)
last_run = utime.ticks_ms()

try:
    while True:
        result_cnt = ser.any()
        if result_cnt != 0:
[-========================================================================================='/[================;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;=================================[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[            print(result_cnt)
        while (result_cnt > 0):
           # if utime.ticks_diff(utime.ticks_ms, last_run) < 5000:
           #     ser.read(result_cnt)
           #     continue
           # last_run = utime.ticks_ms()
           # print(last_run)
            read_radar_data()
           # result = ser.read(result_cnt)
           # if result != last_result:
           #     last_result = result
           #     print(result)    
        
        
except KeyboardInterrupt:
    print("Exiting...")
finally:
    pass
    print("done")
    
