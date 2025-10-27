
from machine import ADC, Pin, PWM
import lcd_support
from lcd_support import lcd_status

# Define the timer callback function
def a_timer_callback(a_timer):
    a_interrupt_handler(None)
def b_timer_callback(b_timer):
    b_interrupt_handler(None)
def c_timer_callback(c_timer):
    c_interrupt_handler(None)

last_count = -1
last_coil = ""
max_count = 32767
min_count = -32767
step_count = 1
start_count = 0
count = start_count
# Define the threshold value for the interrupt
threshold = 50  # 12-bit ADC (0-4095)

# Define the ADC pin (e.g., ADC0 on GP26)
a_pin = ADC(Pin(28))
b_pin = ADC(Pin(27))
c_pin = ADC(Pin(26))
    
# Set up a timer to periodically check the ADC value
a_timer = machine.Timer()
b_timer = machine.Timer()
c_timer = machine.Timer()

# Initialize the timer to call the callback function every 10ms
a_timer.init(period=10, mode=machine.Timer.PERIODIC, callback=a_timer_callback)
b_timer.init(perio=10, mode=machine.Timer.PERIODIC, callback=b_timer_callback)
c_timer.init(period=10, mode=machine.Timer.PERIODIC, callback=c_timer_callback)

        
def encoder_loop():
    if last_count != count:
        if count < min_count:
            count = min_count
        if count > max_count:
            count = max_count
        last_count = count
        lcd_status("", count)
    
#encoder exit code
def encoder_exit():
    a_timer.deinit()  # Deinitialize the timer
    b_timer.deinit()  # Deinitialize the timer
    c_timer.deinit()  # Deinitialize the timer
    print("Timer deinitialized")
    



# Define the interrupt handler function
def a_interrupt_handler(pin):
    global last_coil, count, step_count, a_pin
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
    global last_coil, count, b_pin
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
    global last_coil, count, c_pin
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




# Main loop
try:
    import utime
     
    while True:
        utime.sleep(.1)  # Sleep to keep the main loop running
        encoder_loop()

            
except KeyboardInterrupt:
    print("Program interrupted by user")
    encoder_exit()
    
    

