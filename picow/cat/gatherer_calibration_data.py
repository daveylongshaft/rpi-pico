import machine
import math
import utime

# Constants for ADC and the circuit
VCC = 3.3  # Pico's supply voltage (3.3V)
R_known = 1000  # Known resistor value in ohms (e.g., 10k)

# Setup the ADC (using GPIO 26 / ADC0 pin)
adc = machine.ADC(26)

# Function to read the ADC value and convert to voltage
def read_voltage():
    # The ADC value ranges from 0 to 65535, corresponding to 0-3.3V
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * VCC
    return voltage

# Function to calculate thermistor resistance
def calculate_resistance(voltage):
    # Voltage divider equation: Vout = Vcc * (R_therm / (R_known + R_therm))
    # Rearranging to solve for R_therm:
    if voltage == 0:
        return None  # Avoid division by zero
    R_therm = R_known * (VCC / voltage - 1)
    return R_therm

# Function to log the data
def log_data():
    while True:
        voltage = read_voltage()
        resistance = calculate_resistance(voltage)
        if resistance is not None:
            print(f"Voltage: {voltage:.3f} V, Thermistor Resistance: {resistance:.2f} Ohms")
        else:
            print("Error reading thermistor resistance (voltage = 0).")
        
        # Wait for a bit before taking the next reading
        utime.sleep(1)

# Main loop to gather data
log_data()