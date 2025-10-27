import machine
import socket
import utime
import network
import time
from urllib.parse import unquote

# Global state for user input (shared between request parsing and app logic)
WEB_LAST_INPUT = None

class PicoWebConsole:
    """
    Encapsulates all Pico W web server functionality, hardware control,
    and the HTML-based I/O abstraction.
    """
    
    # State for console output
    WEB_DISPLAY_CONTENT = ["Web I/O Console Initializing..."]
    
    # Constants
    CONVERSION_FACTOR = 3.3 / 65535.0
    CONSOLE_MAX_LINES = 15

    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.ip = None
        self.nic = None
        
        # Hardware Pins (GP13, GP14, GP15)
        self.red = machine.Pin(13, machine.Pin.OUT)
        self.green = machine.Pin(14, machine.Pin.OUT)
        self.blue = machine.Pin(15, machine.Pin.OUT)
        
        # Temperature Sensor (ADC4)
        self.sensor_temp = machine.ADC(4)
        
        self.connect_wifi()
        
    def connect_wifi(self):
        """Connects the Pico W to the specified Wi-Fi network."""
        self.nic = network.WLAN(network.STA_IF)
        
        if not self.nic.isconnected():
            self.html_out("Attempting Wi-Fi connection...", element_tag='system')
            self.nic.active(True)
            self.nic.connect(self.ssid, self.password)
            
            wait = 10
            while wait > 0 and not self.nic.isconnected():
                utime.sleep(1)
                wait -= 1
            
            if self.nic.isconnected():
                self.ip = self.nic.ifconfig()[0]
                self.html_out(f"Connected! IP: http://{self.ip}/", element_tag='system')
            else:
                self.html_out("ERROR: Wi-Fi connection failed.", element_tag='error')
                raise RuntimeError('Wi-Fi connection failed')
        else:
            self.ip = self.nic.ifconfig()[0]
            self.html_out(f"Already connected. IP: http://{self.ip}/", element_tag='system')
        
    # --- I/O ABSTRACTION METHODS ---
    
    def html_out(self, output_data, element_id='display', element_tag='p'):
        """
        Appends formatted content to the display buffer, mimicking print().
        
        Args:
            output_data (str): The content to display.
            element_id (str): The HTML ID of the target element (default 'display').
            element_tag (str): A tag to categorize the output (e.g., 'p', 'system', 'error').
        """
        # Note: The console uses a single <pre> element, so element_tag is used for style/context
        # in the console list, but the output rendering remains simple.
        self.WEB_DISPLAY_CONTENT.append(f"[{element_tag.upper()}] {output_data}")
        
        # Keep buffer size manageable
        if len(self.WEB_DISPLAY_CONTENT) > self.CONSOLE_MAX_LINES:
            self.WEB_DISPLAY_CONTENT = self.WEB_DISPLAY_CONTENT[-self.CONSOLE_MAX_LINES:]

    def html_in(self, element_type='text'):
        """
        Retrieves the last command received from the user, mimicking input().
        
        Args:
            element_type (str): Type of input expected (e.g., 'text', 'button').
            
        Returns:
            str: The user input, or None if no new input is available.
        """
        global WEB_LAST_INPUT
        input_copy = WEB_LAST_INPUT
        WEB_LAST_INPUT = None  # Clear buffer after reading
        return input_copy
        
    # --- HARDWARE METHODS ---
    
    def temperature(self):
        """Reads the internal temperature sensor and returns Celsius."""
        temperature_value = self.sensor_temp.read_u16() * self.CONVERSION_FACTOR
        # Using the original (possibly calibrated) formula from the previous version
        temperature_celcius = 27 - (temperature_value - 0.706) / 0.00172169 / 8 
        return temperature_celcius

    # --- APPLICATION LOGIC ---
    
    def app_loop(self):
        """
        The main application logic run on every HTTP request/page refresh.
        This is where you integrate your program using html_in and html_out.
        """
        temp_c = self.temperature()
        
        # 1. Process any pending user input
        command = self.html_in()
        if command:
            self.html_out(f" > Command: '{command}'", element_tag='input')
            if command.lower() == 'temp':
                self.html_out(f"Pico Temp: {temp_c:.2f} °C", element_tag='data')
            elif command.lower() == 'red':
                self.red.high()
                self.green.low()
                self.blue.low()
                self.html_out("RGB LED set to RED.", element_tag='status')
            elif command.lower() == 'off':
                self.red.low()
                self.green.low()
                self.blue.low()
                self.html_out("RGB LED turned OFF.", element_tag='status')
            elif command.lower() == 'help':
                self.html_out("Commands: 'temp', 'red', 'green', 'blue', 'off', 'clear'", element_tag='info')
            elif command.lower() == 'clear':
                self.WEB_DISPLAY_CONTENT = ["Console cleared."]
            else:
                self.html_out("Unknown command. Type 'help'.", element_tag='error')
        else:
             # If no command, just update the status line.
             self.WEB_DISPLAY_CONTENT[-1] = f"[DATA] Temperature: {temp_c:.2f} °C (Last update: {utime.time()})"

    # --- HTTP SERVER METHODS ---

    def webpage(self, temp_value):
        """Generates the HTML page with dynamic I/O elements and styling."""
        
        # Format the display content as simple paragraphs/lines for the HTML pre element
        console_output = '\n'.join(self.WEB_DISPLAY_CONTENT)
        
        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Pico W Web Shell</title>
                <style>
                    /* Styles optimized for mobile responsiveness and dark mode console */
                    body {{ font-family: 'Arial', sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 10px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
                    h1 {{ color: #007bff; text-align: center; font-size: 1.5rem; }}
                    h2 {{ font-size: 1.2rem; margin-top: 15px; }}
                    .card {{ background: #e9ecef; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); }}
                    form {{ display: flex; flex-direction: column; gap: 10px; margin-bottom: 5px; }}
                    input[type="submit"], button {{ background-color: #007bff; color: white; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; transition: background-color 0.3s; }}
                    input[type="submit"]:hover, button:hover {{ background-color: #0056b3; }}
                    .console-title {{ font-weight: bold; margin-bottom: 5px; color: #007bff; }}
                    #display {{ 
                        white-space: pre-wrap; 
                        background-color: #1e1e1e; 
                        color: #00ff7f; /* Green text for console */
                        padding: 15px; 
                        border-radius: 6px; 
                        height: 250px; 
                        overflow-y: scroll; 
                        margin-bottom: 20px; 
                        font-family: 'Consolas', monospace; 
                        font-size: 12px;
                        line-height: 1.4;
                    }}
                    .temp-status {{ text-align: center; font-size: 1.1em; padding: 10px; background: #ffc107; border-radius: 8px; font-weight: bold; margin-bottom: 15px; color: #333;}}
                    .button-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;}}
                </style>
            </head>
            <body>
            <div class="container">
                <h1>Pico W Web Console</h1>
                <p>Status: Running on {self.ip}</p>
                
                <div class="temp-status">
                    Pico Temperature: {temp_value} °C
                </div>
                
                <!-- Display Area -->
                <div class="console-title">Pico Output (html_out):</div>
                <pre id="display">{console_output}</pre>

                <!-- Action Buttons (Trigger I/O & Refresh) -->
                <div class="card">
                    <h2>RGB LED Actions</h2>
                    <div class="button-grid">
                        <form action="./action/red_on" method="get">
                            <input type="submit" value="Red ON" style="background-color: #dc3545;" />
                        </form>
                        <form action="./action/green_on" method="get">
                            <input type="submit" value="Green ON" style="background-color: #28a745;" />
                        </form>
                        <form action="./action/blue_on" method="get">
                            <input type="submit" value="Blue ON" style="background-color: #007bff;" />
                        </form>
                        <form action="./action/off" method="get">
                            <input type="submit" value="All OFF" style="background-color: #6c757d;" />
                        </form>
                    </div>
                </div>

                <!-- User Input Form (html_in mimic) -->
                <div class="card">
                    <h2>Console Input</h2>
                    <form action="./command" method="get">
                        <label for="user_input">Type command (e.g., 'temp', 'red'):</label>
                        <input type="text" id="user_input" name="input" placeholder="Enter command..." required style="padding: 10px; border: 1px solid #ccc; border-radius: 6px;"/>
                        <input type="submit" value="Send Command & Refresh" style="background-color: #17a2b8;"/>
                    </form>
                </div>
                
            </div>
            </body>
            </html>
            """
        return html
 
    def serve(self):
        """Starts the socket server and handles incoming HTTP requests."""
        # Open a socket
        address = (self.ip, 80)
        connection = socket.socket()
        
        try:
            connection.bind(address)
            connection.listen(1)
            self.html_out("Socket listening on port 80.", element_tag='system')
            print(f"Pico Web Console running at http://{self.ip}/")
            
            # Run the server loop indefinitely
            while True:
                client = None
                try:
                    client, addr = connection.accept()
                    # Receive up to 1024 bytes of the request header
                    request = client.recv(1024).decode('utf-8')
                    
                    # Extract path from request line
                    request_line = request.split('\r\n')[0]
                    try:
                        path = request_line.split()[1]
                    except IndexError:
                        path = '/'
                    
                    # print(f"Raw Request: {path}") # Debug line

                    # --- 1. Handle Input (Command) Request and set WEB_LAST_INPUT ---
                    if path.startswith('/command?'):
                        query_string = path.split('?', 1)[1]
                        for pair in query_string.split('&'):
                            if pair.startswith('input='):
                                global WEB_LAST_INPUT
                                WEB_LAST_INPUT = unquote(pair[6:])
                                break
                    
                    # --- 2. Handle Action Requests (LEDs) ---
                    if path.startswith('/action/'):
                        action = path.split('/')[2].split('?')[0]
                        
                        if action == 'off':
                            self.red.low(); self.green.low(); self.blue.low()
                            self.html_out("Action: All OFF.", element_tag='status')
                        elif action == 'red_on':
                            self.red.high(); self.green.low(); self.blue.low()
                            self.html_out("Action: Red ON.", element_tag='status')
                        elif action == 'green_on':
                            self.red.low(); self.green.high(); self.blue.low()
                            self.html_out("Action: Green ON.", element_tag='status')
                        elif action == 'blue_on':
                            self.red.low(); self.green.low(); self.blue.high()
                            self.html_out("Action: Blue ON.", element_tag='status')
                    
                    # --- 3. Execute Application Logic and Respond ---
                    
                    # Run the class's application logic, which uses html_in/out
                    self.app_loop()
                    
                    # Generate the HTML response
                    temp_value = '%.2f' % self.temperature()
                    html = self.webpage(temp_value)
                    
                    # Send HTTP response
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    client.send(html)
                    
                except OSError as e:
                    if client: client.close()
                    # print('Connection closed or OS Error:', e) # Suppress common closed socket errors
                except Exception as e:
                    self.html_out(f"CRITICAL SERVER ERROR: {e}", element_tag='error')
                    print(f"CRITICAL SERVER ERROR: {e}")
                    if client: client.close()
                finally:
                    if client:
                        client.close()

        except KeyboardInterrupt:
            self.html_out("Server stopped by KeyboardInterrupt.", element_tag='system')
            print("Server stopped by KeyboardInterrupt.")
        except Exception as e:
            self.html_out(f"FATAL SETUP ERROR: {e}", element_tag='error')
            print(f"FATAL SETUP ERROR: {e}")
            
# --- MAIN EXECUTION ENTRY POINT ---

# Ensure 'boot' is available if not run as main.py
try:
    if 'boot' not in globals() and 'boot' not in locals():
        import boot
except:
    import boot

# Use the credentials you provided previously
APP_SSID = 'ANTEATER2' 
APP_PASSWORD = 'Juliaz13'

# Create and run the console instance
if __name__ == '__main__':
    try:
        console = PicoWebConsole(APP_SSID, APP_PASSWORD)
        console.serve()
    except RuntimeError as e:
        print(f"Startup Failed: {e}")
    except Exception as e:
        print(f"Application Error: {e}")
        # Note: If running this via Thonny, Thonny handles the soft-reboot (machine.reset()) 
        # on unhandled exceptions.
