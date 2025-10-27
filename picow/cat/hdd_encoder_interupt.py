from machine import ADC, Pin, PWM
import utime
import lcd_support
from lcd_support import lcd_status
from rgb import rgb_loop, set_rgb

last_count = -1
last_coil = ""
max_count = 65535
min_count = 0
step_count = 10
#start_count = 32767
start_count = 65535
count = start_count

#led = PWM(Pin(14))
#led.freq(65535)



# Define the ADC pin (e.g., ADC0 on GP26)
a_pin = ADC(Pin(28))
b_pin = ADC(Pin(27))
c_pin = ADC(Pin(26))

# Define the threshold value for the interrupt
threshold = 50  # 12-bit ADC (0-4095)

# Define the interrupt handler function
def a_interrupt_handler(pin):
    global last_coil, count, step_count
    if last_coil == "A":
        return
    value = a_pin.read_u16()  # Read the ADC value
    if value < threshold:
        return
    factor = int(value / threshold)
    if last_coil == "B":
        count += step_count * factor
    elif last_coil == "C":
        count -= step_count * factor
    last_coil = "A"
            
# Define the interrupt handler function
def b_interrupt_handler(pin):
    global last_coil, count
    if last_coil == "B":
        return
    value = b_pin.read_u16()  # Read the ADC value
    if value < threshold:
        return
    factor = int(value / threshold)
    if last_coil == "C":
        count += step_count * factor
    elif last_coil == "A":
        count -= step_count * factor
    last_coil = "B"

# Define the interrupt handler function
def c_interrupt_handler(pin):
    global last_coil, count
    if last_coil == "C":
        return
    value = c_pin.read_u16()  # Read the ADC value
    if value < threshold:
        return
    factor = int(value / threshold)
    if last_coil == "A":
        count += step_count * factor
    elif last_coil == "B":
        count -= step_count * factor
    last_coil = "C"
    
# Set up a timer to periodically check the ADC value
a_timer = machine.Timer()
b_timer = machine.Timer()
c_timer = machine.Timer()

# Define the timer callback function
def a_timer_callback(a_timer):
    a_interrupt_handler(None)
def b_timer_callback(b_timer):
    b_interrupt_handler(None)
def c_timer_callback(c_timer):
    c_interrupt_handler(None)

# Initialize the timer to call the callback function every 10ms
a_timer.init(period=10, mode=machine.Timer.PERIODIC, callback=a_timer_callback)
b_timer.init(period=10, mode=machine.Timer.PERIODIC, callback=b_timer_callback)
c_timer.init(period=10, mode=machine.Timer.PERIODIC, callback=c_timer_callback)

# Main loop
try:
    while True:
        #utime.sleep(.1)  # Sleep to keep the main loop running
        if last_count != count:
            if count < min_count:
                count = min_count
            if count > max_count:
                count = max_count
            last_count = count
            lcd_status("", count)
            #set_rgb(count, count, count, 1)
#            led.duty_u16(count)
            #rgb_loop()
            
except KeyboardInterrupt:
    print("Program interrupted by user")
    a_timer.deinit()  # Deinitialize the timer
    b_timer.deinit()  # Deinitialize the timer
    c_timer.deinit()  # Deinitialize the timer
    print("Timer deinitialized")
    