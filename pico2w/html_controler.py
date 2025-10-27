import machine
import socket
import utime
import network
import time
import ubluetooth as bluetooth
from micropython import const

# Global state for user input (shared between request parsing and app logic)
WEB_LAST_INPUT = None

# BLE Advertising Constants
ADV_FLAG_LE_GENERAL_DISCOVERABLE = const(0x02)
ADV_TYPE_NAME_COMPLETE = const(0x09)

def url_decode(s):
    """
    Minimal URL decoding function for MicroPython. 
    Decodes '+' to space and '%XX' hex sequences.
    """
    s = s.replace('+', ' ')
    parts = s.split('%')
    if len(parts) == 1:
        return s
    
    result = [parts[0]]
    for part in parts[1:]:
        if len(part) >= 2:
            try:
                # Decode the hex value (first two characters)
                hex_val = part[:2]
                char = chr(int(hex_val, 16))
                result.append(char)
                result.append(part[2:])
            except ValueError:
                # If hex conversion fails, treat as literal '%'
                result.append('%')
                result.append(part)
        else:
            result.append('%')
            result.append(part)
    return "".join(result)

class Html_controler:
    """
    Encapsulates all Pico W web server functionality, hardware control,
    and the HTML-based I/O abstraction. Class name matches filename, capitalized.
    """
    
    # State for console output
    WEB_DISPLAY_CONTENT = ["Web I/O Console Initializing..."]
    
    # Constants
    CONVERSION_FACTOR = 3.3 / 65535.0
    CONSOLE_MAX_LINES = 15
    BLE_DEVICE_NAME_DEFAULT = 'Pico-WebIO'

    def __init__(self, ssid, password):
        # Configuration state variables
        self.ssid = ssid
        self.password = password
        
        self.ip = None
        self.nic = None
        self.serving_client = False # Tracks if a connection is currently being served
        
        # Hardware Pins (GP13, GP14, GP15)
        self.red = machine.Pin(13, machine.Pin.OUT)
        self.green = machine.Pin(14, machine.Pin.OUT)
        self.blue = machine.Pin(15, machine.Pin.OUT)
        
        # Temperature Sensor (ADC4)
        self.sensor_temp = machine.ADC(4)
        
        # Bluetooth Setup
        self.ble = None
        self.ble_active = False
        self.ble_name = self.BLE_DEVICE_NAME_DEFAULT
        self.init_ble()
        
        self.connect_wifi()
        
    def init_ble(self):
        """Initializes the Bluetooth radio."""
        try:
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble_active = True
            self.start_ble_advertising()
            self.html_out(f"BLE initialized as '{self.ble_name}'.", element_tag='system')
        except Exception as e:
            self.html_out(f"BLE init failed: {e}. Check firmware.", element_tag='error')

    def _adv_encode(self, adv_type, value):
        """Helper to format advertising data payload sections."""
        return bytes([len(value) + 1, adv_type]) + value
        
    def start_ble_advertising(self):
        """Starts BLE advertising with the current device name."""
        if not self.ble:
            self.html_out("BLE radio not initialized.", element_tag='error')
            return
            
        # Simple advertising payload: Flags + Device Name
        adv_data = bytes([0x02, 0x01, ADV_FLAG_LE_GENERAL_DISCOVERABLE]) + \
                   self._adv_encode(ADV_TYPE_NAME_COMPLETE, self.ble_name.encode('utf-8'))
        
        self.ble.gap_advertise(100_000, adv_data=adv_data) # 100ms interval
        self.ble_active = True
        self.html_out(f"BLE advertising STARTED as '{self.ble_name}'.", element_tag='status')

    def stop_ble_advertising(self):
        """Stops BLE advertising."""
        if self.ble:
            self.ble.gap_advertise(None)
            self.ble_active = False
            self.html_out("BLE advertising STOPPED.", element_tag='status')

    def connect_wifi(self):
        """Connects the Pico W to the current Wi-Fi network credentials."""
        self.nic = network.WLAN(network.STA_IF)
        
        # Explicitly disconnect if already connected to ensure a clean attempt
        if self.nic.isconnected():
            self.html_out("Disconnecting from old Wi-Fi...", element_tag='system')
            self.nic.disconnect()
            utime.sleep_ms(500) 
            
        self.html_out(f"Connecting to SSID: {self.ssid}...", element_tag='system')
        self.nic.active(True)
        self.nic.connect(self.ssid, self.password)
        
        wait = 15
        while wait > 0 and not self.nic.isconnected():
            utime.sleep(1)
            wait -= 1
        
        if self.nic.isconnected():
            self.ip = self.nic.ifconfig()[0]
            self.html_out(f"Connected! IP: http://{self.ip}/", element_tag='system')
        else:
            self.ip = "0.0.0.0"
            self.html_out("ERROR: Wi-Fi connection failed. Check credentials and retry.", element_tag='error')
        
    # --- I/O ABSTRACTION METHODS ---
    
    def html_out(self, output_data, element_id='display', element_tag='p'):
        """
        Appends formatted content to the display buffer, mimicking print().
        """
        self.WEB_DISPLAY_CONTENT.append(f"[{element_tag.upper()}] {output_data}")
        
        # Keep buffer size manageable
        if len(self.WEB_DISPLAY_CONTENT) > self.CONSOLE_MAX_LINES:
            self.WEB_DISPLAY_CONTENT = self.WEB_DISPLAY_CONTENT[-self.CONSOLE_MAX_LINES:]

    def html_in(self, element_type='text'):
        """Retrieves the last command received from the user, mimicking input()."""
        global WEB_LAST_INPUT
        input_copy = WEB_LAST_INPUT
        WEB_LAST_INPUT = None  # Clear buffer after reading
        return input_copy
        
    # --- HARDWARE METHODS ---
    
    def temperature(self):
        """Reads the internal temperature sensor and returns Celsius."""
        temperature_value = self.sensor_temp.read_u16() * self.CONVERSION_FACTOR
        temperature_celcius = 27 - (temperature_value - 0.706) / 0.00172169 / 8 
        return temperature_celcius

    # --- APPLICATION LOGIC ---
    
    def app_loop(self):
        """The main application logic run on every HTTP request/page refresh."""
        temp_c = self.temperature()
        
        # 1. Process any pending user input (from html_in)
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
            if self.WEB_DISPLAY_CONTENT:
                # Overwrite the last line if it was a data update
                if self.WEB_DISPLAY_CONTENT[-1].startswith('[DATA] Temperature:'):
                    self.WEB_DISPLAY_CONTENT[-1] = f"[DATA] Temperature: {temp_c:.2f} °C (Last update: {utime.time()})"
                else:
                    self.WEB_DISPLAY_CONTENT.append(f"[DATA] Temperature: {temp_c:.2f} °C (Last update: {utime.time()})")


    # --- HTTP SERVER METHODS ---

    def webpage(self, temp_value):
        """Generates the HTML page with dynamic I/O elements and styling and system info."""
        
        console_output = '\n'.join(self.WEB_DISPLAY_CONTENT)
        wifi_status_data = self.nic.ifconfig() if self.nic and self.nic.isconnected() else ('0.0.0.0', '0.0.0.0', '0.0.0.0', '0.0.0.0')
        client_count_display = "1 (Busy)" if self.serving_client else "0 (Idle)" # Simple blocking server count
        ble_status_text = "Advertising" if self.ble_active else "Inactive"
        
        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Pico W System Controller</title>
                <style>
                    /* Styles optimized for mobile responsiveness and dark mode console */
                    body {{ font-family: 'Inter', sans-serif; background-color: #e6e6fa; color: #333; margin: 0; padding: 10px; }}
                    .container {{ max-width: 700px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2); }}
                    h1 {{ color: #4b0082; text-align: center; font-size: 1.8rem; margin-bottom: 5px; }}
                    h2 {{ font-size: 1.2rem; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 20px; color: #555;}}
                    .card {{ background: #f0f0ff; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: inset 0 1px 4px rgba(0,0,0,0.1); }}
                    .card-status {{ background: #e0f7fa; }}
                    form {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 5px; }}
                    input[type="submit"], button {{ background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; transition: background-color 0.3s, transform 0.1s; flex-grow: 1; }}
                    input[type="submit"]:hover, button:hover {{ background-color: #0056b3; transform: scale(1.02); }}
                    .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 15px; }}
                    .status-item {{ background: #fff; padding: 10px; border-radius: 6px; border-left: 5px solid #4b0082; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                    .status-label {{ font-size: 0.8em; color: #777; }}
                    .status-value {{ font-size: 1.1em; font-weight: bold; }}
                    
                    #display {{ 
                        white-space: pre-wrap; 
                        background-color: #1e1e1e; 
                        color: #00ff7f; 
                        padding: 15px; 
                        border-radius: 6px; 
                        height: 200px; 
                        overflow-y: scroll; 
                        margin-bottom: 20px; 
                        font-family: 'Consolas', monospace; 
                        font-size: 12px;
                        line-height: 1.4;
                    }}
                    .button-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;}}
                </style>
            </head>
            <body>
            <div class="container">
                <h1>Pico W System Console</h1>
                
                <!-- System Status Panel -->
                <div class="card card-status">
                    <h2>System Status</h2>
                    <div class="status-grid">
                        <div class="status-item"><div class="status-label">Internal Temp</div><div class="status-value">{temp_value} °C</div></div>
                        <div class="status-item"><div class="status-label">IP Address</div><div class="status-value">{wifi_status_data[0]}</div></div>
                        <div class="status-item"><div class="status-label">Netmask</div><div class="status-value">{wifi_status_data[1]}</div></div>
                        <div class="status-item"><div class="status-label">Gateway</div><div class="status-value">{wifi_status_data[2]}</div></div>
                        <div class="status-item"><div class="status-label">DNS</div><div class="status-value">{wifi_status_data[3]}</div></div>
                        <div class="status-item"><div class="status-label">Web Clients</div><div class="status-value">{client_count_display}</div></div>
                        <div class="status-item"><div class="status-label">BLE Status</div><div class="status-value">{ble_status_text}</div></div>
                        <div class="status-item"><div class="status-label">BLE Name</div><div class="status-value">{self.ble_name}</div></div>
                    </div>
                </div>

                <!-- Wi-Fi Configuration -->
                <div class="card">
                    <h2>Wi-Fi Configuration (Editable)</h2>
                    <form action="./config/set_wifi" method="get">
                        <label for="ssid" style="flex-basis: 100%;">SSID:</label>
                        <input type="text" id="ssid" name="ssid" value="{self.ssid}" required style="padding: 10px; border: 1px solid #ccc; border-radius: 6px; flex-grow: 10;"/>
                        
                        <label for="password" style="flex-basis: 100%;">Password:</label>
                        <input type="password" id="password" name="password" value="{self.password}" required style="padding: 10px; border: 1px solid #ccc; border-radius: 6px; flex-grow: 10;"/>
                        <input type="submit" value="Change & Reconnect" style="background-color: #007bff; flex-grow: 1; margin-top: 10px;"/>
                    </form>
                </div>

                <!-- BLE Configuration -->
                <div class="card">
                    <h2>BLE Configuration (Editable)</h2>
                    <form action="./config/set_ble_name" method="get">
                        <label for="ble_name" style="flex-basis: 100%;">Device Name (30 char max):</label>
                        <input type="text" id="ble_name" name="name" value="{self.ble_name}" maxlength="30" required style="padding: 10px; border: 1px solid #ccc; border-radius: 6px; flex-grow: 10;"/>
                        <input type="submit" value="Set Name" style="background-color: #ff6347; flex-grow: 1;"/>
                    </form>
                    <div class="button-grid" style="margin-top: 15px;">
                        <form action="./action/ble_start" method="get">
                            <input type="submit" value="Start BLE" style="background-color: #28a745;"/>
                        </form>
                        <form action="./action/ble_stop" method="get">
                            <input type="submit" value="Stop BLE" style="background-color: #dc3545;"/>
                        </form>
                    </div>
                </div>

                <!-- RGB LED Actions -->
                <div class="card">
                    <h2>RGB LED Control</h2>
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

                <!-- Console Output and Input -->
                <div class="card">
                    <div class="console-title">Console Output (html_out):</div>
                    <pre id="display">{console_output}</pre>
                    <h2>Console Input (html_in)</h2>
                    <form action="./command" method="get">
                        <label for="user_input">Enter Console Command:</label>
                        <input type="text" id="user_input" name="input" placeholder="Type 'help' for commands..." required style="padding: 10px; border: 1px solid #ccc; border-radius: 6px; flex-grow: 1;"/>
                        <input type="submit" value="Send Command" style="background-color: #17a2b8;"/>
                    </form>
                </div>
                
            </div>
            </body>
            </html>
            """
        return html
 
    def serve(self):
        """Starts the socket server and handles incoming HTTP requests."""
        address = (self.ip, 80)
        connection = socket.socket()
        
        try:
            connection.bind(address)
            connection.listen(1)
            self.html_out("Socket listening on port 80.", element_tag='system')
            print(f"Pico Web Console running at http://{self.ip}/")
            
            while True:
                client = None
                try:
                    self.serving_client = True # Client connected (for blocking server, this is 1)
                    client, addr = connection.accept()
                    # Decode request to handle UTF-8 characters
                    request = client.recv(1024).decode('utf-8')
                    request_line = request.split('\r\n')[0]
                    path = request_line.split()[1] if len(request_line.split()) > 1 else '/'
                    
                    global WEB_LAST_INPUT
                    
                    # --- 1. Handle Input (Command) Request and set WEB_LAST_INPUT ---
                    if path.startswith('/command?'):
                        query_string = path.split('?', 1)[1]
                        for pair in query_string.split('&'):
                            if pair.startswith('input='):
                                # Use local url_decode function to decode URL parameters
                                WEB_LAST_INPUT = url_decode(pair[6:])
                                break
                    
                    # --- 2. Handle Action Requests (LEDs AND BLE) ---
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
                        elif action == 'ble_start':
                            self.start_ble_advertising()
                        elif action == 'ble_stop':
                            self.stop_ble_advertising()

                    # --- 3. Handle Configuration Requests (BLE Name and Wi-Fi) ---
                    elif path.startswith('/config/set_ble_name?'):
                        query_string = path.split('?', 1)[1]
                        for pair in query_string.split('&'):
                            if pair.startswith('name='):
                                new_name = url_decode(pair[5:])
                                # Enforce 30-character limit for BLE name
                                self.ble_name = new_name[:30] 
                                self.html_out(f"BLE Name set to '{self.ble_name}'. Restarting advertising...", element_tag='config')
                                self.start_ble_advertising()
                                break
                    
                    elif path.startswith('/config/set_wifi?'):
                        query_string = path.split('?', 1)[1]
                        new_ssid = None
                        new_password = None
                        
                        # Parse SSID and Password from the query string
                        for pair in query_string.split('&'):
                            if pair.startswith('ssid='):
                                # Use url_decode to decode URL parameters
                                new_ssid = url_decode(pair[5:])
                            elif pair.startswith('password='):
                                new_password = url_decode(pair[9:])
                        
                        if new_ssid and new_password:
                            self.ssid = new_ssid
                            self.password = new_password
                            self.html_out(f"Wi-Fi credentials updated. Attempting reconnect to {self.ssid}...", element_tag='config')
                            self.connect_wifi() # Reconnect with new credentials
                    
                    # --- 4. Execute Application Logic and Respond ---
                    self.app_loop()
                    
                    # Generate the HTML response
                    temp_value = '%.2f' % self.temperature()
                    html = self.webpage(temp_value)
                    
                    # Send HTTP response
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    client.send(html)
                    
                except OSError as e:
                    # Catch connection closure errors gracefully
                    if client: client.close()
                except Exception as e:
                    self.html_out(f"CRITICAL SERVER ERROR: {e}", element_tag='error')
                    print(f"CRITICAL SERVER ERROR: {e}")
                    if client: client.close()
                finally:
                    self.serving_client = False # Client connection closed
                    if client:
                        client.close()

            except KeyboardInterrupt:
                self.html_out("Server stopped by KeyboardInterrupt.", element_tag='system')
                print("Server stopped by KeyboardInterrupt.")
            except Exception as e:
                self.html_out(f"FATAL SETUP ERROR: {e}", element_tag='error')
                print(f"FATAL SETUP ERROR: {e}")
