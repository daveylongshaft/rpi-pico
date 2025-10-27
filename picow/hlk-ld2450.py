#import serial
import struct
from machine import UART

ser = UART(1, 256000)                         # init with given baudrate
ser.init(256000, bits=8, parity=None, stop=1, tx=4, rx=5) # init with given parameters


# Configure the serial port
#ser = serial.Serial(

#    port='/dev/ttyUSB0',  # Replace with your serial port
#    baudrate=256000,
#    parity=serial.PARITY_NONE,
#    stopbits=serial.STOPBITS_1,
#    bytesize=serial.EIGHTBITS,
#    timeout=0.1
#)
#

# Data structure for radar target
class RadarTarget:
    def __init__(self, data):
        self.id = data[0]
        self.x = struct.unpack('<h', data[1:3])[0]
        self.y = struct.unpack('<h', data[3:5])[0]
        self.speed = struct.unpack('<h', data[5:7])[0]
        self.resolution = struct.unpack('<H', data[7:9])[0]
        self.distance = struct.unpack('<H', data[9:11])[0]
        self.valid = self.resolution != 0

# Function to read data and process targets
def read_radar_data():
    while True:
        header = ser.read(2)
        if header == b'\x55\xaa':
            data_type = ser.read(1)
            if data_type == b'\x01':
                data_len = struct.unpack('<B', ser.read(1))[0]
                data = ser.read(data_len)
                checksum = ser.read(1)

                if len(data) == 33: # Check for full data package
                    num_targets = data[0]
                    for i in range(num_targets):
                        target_data = data[1 + i * 11:12 + i * 11]
                        target = RadarTarget(target_data)
                        print(f"Target {target.id}: X={target.x}mm, Y={target.y}mm, Speed={target.speed/100}m/s, Distance={target.distance}mm, Valid={target.valid}")
            
            elif data_type == b'\x02':
                data_len = struct.unpack('<B', ser.read(1))[0]
                data = ser.read(data_len)
                checksum = ser.read(1)
                
                print("Configuration data received but not parsed")
            else:
                ser.read(ser.in_waiting) # Clear remaining data
                print("Unknown data type")
        
#        if ser.in_waiting > 200:
#            ser.read(ser.in_waiting) # Clear remaining data
#            print("Buffer overflow, clearing")

# Main loop
try:
    while True:
        read_radar_data()
except KeyboardInterrupt:
    print("Exiting...")
finally:
    #ser.close()
    print("done")