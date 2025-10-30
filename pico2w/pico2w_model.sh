

cat >> boot.py <<'eof'
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
eof


cat >> config.py <<'eof'
# config.py
"""
Global configuration file for the Pico W Digital Twin project.
"""

# Set to True for verbose console output across all modules
# Set to False for production (silent) operation
DEBUG = True

def DPRINT(s):
    """Debug print helper function. Prints if config.DEBUG is True."""
    if config.DEBUG:
        print(s)
eof


cat >> html_controler.py <<'eof'
# html_controler.py (Corrected based on user feedback)
import machine
import socket
import utime
import network
import time
from micropython import const
import config
import uasyncio
import ujson
import gc # Import garbage collector
import sys # Import sys at the top

# Import models and the handler
try:
    from pico_board import Pico_board
    from pico_pin import Pico_pin
    from request_handler import Request_handler
except ImportError as e:
    # Use local print because config might not be loaded yet if this fails early
    print(f"Html_controler: FATAL Import Error: {e}")
    # Define dummy classes to prevent crashes later if imports fail
    class Pico_board: pass
    class Pico_pin: pass
    class Request_handler: # Dummy
        async def handle_request(self, path):
             return {"status":"error", "message":"Handler missing"}


def DPRINT(s):
    if config.DEBUG:
        print(s)

# url_decode (unchanged)
def url_decode(s):
    if not s:
        return ""
    try:
        s = s.replace('+', ' ')
        parts = s.split('%')
        if len(parts) == 1:
            return s
        result = [parts[0]]
        for part in parts[1:]:
            if len(part) >= 2:
                try:
                    hex_val = part[:2]
                    char = chr(int(hex_val, 16))
                    result.append(char)
                    result.append(part[2:])
                except ValueError:
                    DPRINT(f"url_decode: Invalid hex '%{part[:2]}'")
                    result.append('%')
                    result.append(part)
            else:
                result.append('%')
                result.append(part)
        return "".join(result)
    except Exception as e:
        DPRINT(f"url_decode: Error '{s}': {e}")
        return s

class Html_controler:
    """ Async Controller & View. Loads templates, runs server, serves API/HTML/CSS/JS. """
    WEB_DISPLAY_CONTENT = ["Web Console Log Initializing..."]
    CONSOLE_MAX_LINES = 20

    # --- Template cache variables ---
    template_parts = None
    template_vars = None
    css_content = None
    js_content = None # Cache for app.js
    templates_loaded = False
    # ---

    def __init__(self, wlan, ssid, password):
        DPRINT("Ctrl: Initializing Html_controler...")
        
        DPRINT("Ctrl: Instantiating Pico_board...")
        self.board = Pico_board(wlan, ssid, password)
        DPRINT("Ctrl: Pico_board instantiated.")
        
        DPRINT("Ctrl: Instantiating Request_handler...")
        self.handler = Request_handler(self.board) # Pass board to handler
        DPRINT("Ctrl: Request_handler instantiated.")
        
        # Add log_message method to board
        if not hasattr(self.board, 'log_message'):
            self.board.log_message = self.html_out
        DPRINT("Ctrl: Monkey-patched 'log_message' onto board instance.")

        self.ip = "0.0.0.0"
        if self.board.nic and self.board.nic.isconnected():
            self.ip = self.board.nic.ifconfig()[0]
            DPRINT(f"Ctrl: Wi-Fi OK. IP: {self.ip}. Attempting initial template load...")
            # Try loading templates initially.
            if self.load_templates():
                self.html_out(f"Board & Templates ready. IP: http://{self.ip}/", element_tag='system')
            else:
                 self.html_out(f"Board ready, but TEMPLATES FAILED TO LOAD. IP: http://{self.ip}/", element_tag='error')
            DPRINT(f"Ctrl: Init OK. IP: {self.ip}")
        else:
            self.html_out("Board init, Wi-Fi disconnected.", element_tag='error')
            DPRINT("Ctrl: Init complete, NO WIFI.")

    # --- Template Loading and Memory Management ---
    def load_templates(self):
        """ Reads HTML/CSS/JS files, parses HTML template, caches content. """
        DPRINT("Ctrl.load_templates: Loading template.html, style.css, app.js...")
        if self.templates_loaded:
             DPRINT("Ctrl.load_templates: Already loaded.")
             return True

        # Clear existing cache
        DPRINT("Ctrl.load_templates: Clearing old cache and running gc...")
        self.template_parts = None
        self.template_vars = None
        self.css_content = None
        self.js_content = None
        self.templates_loaded = False
        gc.collect()
        DPRINT(f"Ctrl.load_templates: Free RAM before load: {gc.mem_free()}")

        try:
            # --- Load HTML Template ---
            DPRINT("Ctrl.load_templates: Reading template.html...")
            with open('template.html', 'r') as f:
                template_content = f.read()
            DPRINT(f"Ctrl.load_templates: Read template.html ({len(template_content)} chars)")

            # --- Parse HTML Template ---
            DPRINT("Ctrl.load_templates: Parsing template.html...")
            parts = []
            var_names = []
            start_index = 0
            tag_start = '<EXTDATA name="'
            tag_end = '" />'
            placeholder_tag = '<EXTDATA'

            if placeholder_tag in template_content:
                while True:
                    tag_index = template_content.find(tag_start, start_index)
                    if tag_index == -1:
                        parts.append(template_content[start_index:])
                        break
                    parts.append(template_content[start_index:tag_index])
                    name_start = tag_index + len(tag_start)
                    name_end = template_content.find(tag_end, name_start)
                    if name_end == -1:
                        raise ValueError(f"Unclosed <EXTDATA> near index {name_start}")
                    var_name = template_content[name_start:name_end].strip()
                    if not var_name:
                        raise ValueError(f"Empty name in <EXTDATA> near index {name_start}")
                    var_names.append(var_name)
                    start_index = name_end + len(tag_end)
            else:
                 parts.append(template_content) # Whole template is static
                 DPRINT("Ctrl.load_templates: No <EXTDATA> tags found.")

            self.template_parts = parts
            self.template_vars = var_names
            DPRINT(f"Ctrl.load_templates: Parsed template ({len(parts)} parts, {len(var_names)} vars).")

            # --- Load CSS ---
            DPRINT("Ctrl.load_templates: Reading style.css...")
            with open('style.css', 'r') as f:
                self.css_content = f.read()
            DPRINT(f"Ctrl.load_templates: Read style.css ({len(self.css_content)} chars)")

            # --- Load JS ---
            DPRINT("Ctrl.load_templates: Reading app.js...")
            with open('app.js', 'r') as f:
                self.js_content = f.read()
            DPRINT(f"Ctrl.load_templates: Read app.js ({len(self.js_content)} chars)")

            self.templates_loaded = True
            self.html_out("Templates loaded.", 'mem')
            gc.collect()
            DPRINT(f"Ctrl.load_templates: SUCCESS. Free RAM after load: {gc.mem_free()}")
            return True

        except Exception as e:
            DPRINT(f"Ctrl.load_templates: ERROR: {e}")
            sys.print_exception(e)
            self.free_templates()
            return False

    def free_templates(self):
        """ Clears cached template/CSS/JS content and runs GC. """
        DPRINT("Ctrl.free_templates: Freeing templates from RAM...")
        self.template_parts = None
        self.template_vars = None
        self.css_content = None
        self.js_content = None
        self.templates_loaded = False
        gc.collect()
        self.html_out("Templates freed.", 'mem')
        DPRINT(f"Ctrl.free_templates: Free RAM: {gc.mem_free()}")
        return True

    # Server-side Logging
    def html_out(self, output_data, element_tag='p'):
        output_data_str = str(output_data)
        DPRINT(f"Ctrl.html_out: [{element_tag.upper()}] {output_data_str}")
        self.WEB_DISPLAY_CONTENT.append(f"[{element_tag.upper()}] {output_data_str}")
        if len(self.WEB_DISPLAY_CONTENT) > self.CONSOLE_MAX_LINES:
            self.WEB_DISPLAY_CONTENT = self.WEB_DISPLAY_CONTENT[-self.CONSOLE_MAX_LINES:]

    # --- HTML Generation Shells ---
    def _generate_pin_element_shell(self, pin, index):
        if pin is None:
             return f"<div class='pin-element pin-error' id='pin-{index}-shell'>Pin Error</div>"
        
        pin_id_val = pin._id if hasattr(pin, '_id') else f'fixed-{index}'
        pin_id = str(pin_id_val)
        is_gpio = hasattr(pin, '_pin') and pin._pin is not None 
        
        is_power = 'GND' in pin.name or 'VBUS' in pin.name or '3V3' in pin.name or 'VSYS' in pin.name
        is_special_func = 'EN' in pin.name or 'VREF' in pin.name or 'RUN' in pin.name
        
        pin_classes = "pin-element " 
        
        if not is_gpio: 
            pin_classes += "pin-fixed " 
            
        if is_power: 
            pin_classes += "pin-power " 
        elif is_special_func: 
            pin_classes += "pin-special " 
            
        val_display = f'<span id="pin-{pin_id}-value" class="pin-status">...</span>'
        controls_html = ""
        
        if is_gpio:
            js_pin_id = pin._id if isinstance(pin._id, int) and pin._id >= 0 else f"'{pin_id}'"
            mode_options = ['<option value="IN">IN</option>', '<option value="OUT">OUT</option>']
            if hasattr(pin, 'is_adc_capable') and pin.is_adc_capable:
                 mode_options.append('<option value="ADC">ADC</option>')
            mode_options.append('<option value="PWM">PWM</option>')
            mode_select = f'<select id="pin-{pin_id}-mode" onchange="setPinMode({js_pin_id}, this.value)">{"".join(mode_options)}</select>'
            pull_options = ['<option value="NONE">Pull:NONE</option>', '<option value="UP">Pull:UP</option>', '<option value="DOWN">Pull:DOWN</option>']
            pull_control = f'<select id="pin-{pin_id}-pull" style="display: none;" onchange="setPinPull({js_pin_id}, this.value)">{"".join(pull_options)}</select>'
            value_button = f'<button id="pin-{pin_id}-toggle" style="display: none;" class="pin-button" type="button" onclick="togglePinValue({js_pin_id})">Toggle</button>'
            controls_html = f'<div class="pin-controls">{mode_select}{pull_control}{value_button}</div>'
            
        pin_index_html = f'<span class="pin-index">{index}</span>'
        pin_label_html = f'<div class="pin-label">{pin.name}{val_display}</div>'
        element_id_attr = f'id="pin-{pin_id}-shell"'
        data_attr = f'data-pin-id="{pin_id}"'
        
        # Build the final element string and return it (assigned to variable first)
        element_html = ""
        if index <= 20: 
            element_html = f'<div {element_id_attr} class="{pin_classes.strip()}" {data_attr}>{pin_index_html}{pin_label_html}{controls_html}</div>'
        else: 
            element_html = f'<div {element_id_attr} class="{pin_classes.strip()}" {data_attr}>{controls_html}{pin_label_html}{pin_index_html}</div>'
        return element_html

    def _generate_pinout_html_content(self):
        DPRINT("Ctrl._generate_pinout_html_content...")
        if not hasattr(self.board, 'pins_left') or not hasattr(self.board, 'pins_right'):
             return "<p>Error: Board pins missing.</p>"
        
        # Pre-join the lists into strings FIRST
        left_pins_html = ''.join([self._generate_pin_element_shell(pin, i + 1) for i, pin in enumerate(self.board.pins_left)])
        right_pins_html = ''.join([self._generate_pin_element_shell(pin, 40 - i) for i, pin in enumerate(self.board.pins_right)])

        # Split the semicolon-separated assignments onto separate lines
        onboard_led = "" 
        onboard_led_shell_id = "pin-25-shell" 
        onboard_led_data_attr = 'data-pin-id="25"'

        if hasattr(self.board, 'onboard_led_pin') and self.board.onboard_led_pin and hasattr(self.board.onboard_led_pin, '_id'):
             onboard_led_id = self.board.onboard_led_pin._id
             onboard_led = self._generate_pin_element_shell(self.board.onboard_led_pin, onboard_led_id)
             # Ensure these variables use underscores, not hyphens
             onboard_led_shell_id = f"pin-{onboard_led_id}-shell" 
             onboard_led_data_attr = f'data-pin-id="{onboard_led_id}"'
             
        img_html = '<div style="width:250px; height:150px; border:1px solid #ccc; text-align:center; padding-top:50px; margin:auto; border-radius:8px;">Pico W Img</div>'
        
        # Assign to variable before returning
        pinout_html_content = f"""<div class="pinout-grid"><div class="pin-col-left">{left_pins_html}</div><div class="pico-graphic">{img_html}<div class="onboard-led-control" id="{onboard_led_shell_id}" {onboard_led_data_attr}>{onboard_led}</div></div><div class="pin-col-right">{right_pins_html}</div></div>"""
        return pinout_html_content


    # --- webpage method uses template ---
    def webpage(self):
        """ Generates HTML by loading template and replacing placeholders. """
        DPRINT("Ctrl.webpage: Generating HTML from template...")

        # --- Ensure templates are loaded ---
        if not self.templates_loaded:
             DPRINT("Ctrl.webpage: Templates not loaded, calling load_templates()...")
             if not self.load_templates():
                  DPRINT("Ctrl.webpage: ERROR - Template loading failed.")
                  return """<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Template Load Error</h1></body></html>"""
        DPRINT("Ctrl.webpage: Templates are loaded.")
        
        # --- Get current data ---
        DPRINT("Ctrl.webpage: Fetching current board state...")
        data_dict = {}
        try:
             state = self.board.export_state_dict() # Uses cached values mostly
             status = state.get("status", {})
             adcs = state.get("adc_volts", {})
             data_dict = { # Map state keys to <EXTDATA> names
                 "time": status.get("time", "--:--:--"), "temp_c": status.get("temp_c", "--.-"),
                 "ip": status.get("ip", "0.0.0.0"), "ble_status": status.get("ble_status", "Unknown"),
                 "ble_name": status.get("ble_name", "N/A"), "wifi_ssid": status.get("wifi_ssid", "N/A"),
                 "adc0_v": adcs.get("adc0", "-.---"), "adc1_v": adcs.get("adc1", "-.---"),
                 "adc2_v": adcs.get("adc2", "-.---"),
                 "console_log": "\n".join(self.WEB_DISPLAY_CONTENT),
                 "pinout_html": self._generate_pinout_html_content() # Generate pinout HTML structure
             }
             DPRINT("Ctrl.webpage: Board state fetched OK.")
        except Exception as e:
            DPRINT(f"Ctrl.webpage: ERROR getting board state: {e}")
            sys.print_exception(e)
            return """<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Board State Error</h1></body></html>"""

        # --- Build HTML using cached parts and vars ---
        DPRINT("Ctrl.webpage: Building HTML from parts...")
        result_html_list = [] # Changed name for clarity
        try:
            if not self.template_parts or self.template_vars is None:
                raise ValueError("Template not parsed.")
            num_vars = len(self.template_vars)
            num_parts = len(self.template_parts)
            if num_parts != num_vars + 1:
                raise ValueError(f"Template mismatch: {num_parts} parts, {num_vars} vars")
            DPRINT(f"Ctrl.webpage: Joining {num_parts} parts and {num_vars} vars...")
            
            for i in range(num_vars):
                result_html_list.append(self.template_parts[i]) # Static part
                var_name = self.template_vars[i]
                value = data_dict.get(var_name, f"[{var_name}?]") # Lookup value
                result_html_list.append(str(value)) # Append value
            result_html_list.append(self.template_parts[-1]) # Final static part
            
            # Assign final string to variable before returning
            final_html = "".join(result_html_list) 
            DPRINT(f"Ctrl.webpage: HTML built successfully ({len(final_html)} chars).")
            return final_html
        except Exception as e:
            DPRINT(f"Ctrl.webpage: ERROR during template join: {e}")
            sys.print_exception(e)
            return """<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Template Engine Error</h1></body></html>"""


    # --- ASYNC Server Loop (Serves HTML, CSS, JS, API) ---
    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        DPRINT(f"Ctrl.handle_client: Connect from {addr}")
        response_sent = False
        try:
            # Read request line with timeout
            DPRINT("Ctrl.handle_client: Awaiting request line...")
            request_line_bytes = b'' # Initialize
            try:
                request_line_bytes = await uasyncio.wait_for(reader.readline(), 5.0)
            except uasyncio.TimeoutError:
                DPRINT("Ctrl.handle_client: Timeout reading req line.")
                return # Exit cleanly on timeout
            except Exception as e:
                DPRINT(f"Ctrl.handle_client: Error reading req line: {e}")
                return # Exit on other read errors
            
            if not request_line_bytes:
                DPRINT("Ctrl.handle_client: Empty request line. Closing.")
                return
                
            request_line = request_line_bytes.decode('utf-8', 'ignore').strip()
            DPRINT(f"Ctrl.handle_client: Raw Request line: {request_line}")

            # Read/discard headers
            DPRINT("Ctrl.handle_client: Discarding headers...")
            while True:
                header_line = b'' # Initialize
                try:
                    header_line = await uasyncio.wait_for(reader.readline(), 1.0)
                except uasyncio.TimeoutError:
                    break # Assume end of headers on timeout
                except Exception:
                    break # Exit on other read errors
                if not header_line or header_line == b'\r\n':
                    break # Blank line signifies end of headers
                # DPRINT(f"Header: {header_line.decode().strip()}") # Optional: VERY verbose
            DPRINT("Ctrl.handle_client: Headers discarded.")

            method = "GET"
            full_path = "/"
            path = "/"
            try:
                parts = request_line.split()
                method = parts[0].upper()
                full_path = parts[1]
                path = full_path.split('?', 1)[0]
            except IndexError:
                pass # Use defaults if split fails
            DPRINT(f"Ctrl.handle_client: Parsed Method={method}, Path={path}")

            # --- ROUTING ---
            response_code = 200
            response_headers = {"Connection": "close"}
            response_body_bytes = b''
            DPRINT(f"Ctrl.handle_client: Routing path '{path}'...")

            # --- Ensure Templates Loaded for File Serving ---
            needs_files = path in ['/', '/style.css', '/app.js']
            if needs_files and not self.templates_loaded:
                 DPRINT(f"Ctrl.handle_client: Templates needed for '{path}', loading...")
                 if not self.load_templates():
                      DPRINT("Ctrl.handle_client: Template load FAILED.")
                      response_code = 500
                      response_headers["Content-Type"] = "text/plain"
                      response_body_bytes = b"Server Error: Could not load template files."
                 else:
                      DPRINT(f"Ctrl.handle_client: Templates loaded OK.")

            # --- Route Request (only if templates loaded ok or not needed) ---
            if response_code == 200: # Check if error occurred during template load
                DPRINT(f"Ctrl.handle_client: Processing route '{path}'...")
                if path == '/':
                    DPRINT("Ctrl.handle_client: Route matched '/'. Generating webpage...")
                    response_headers["Content-Type"] = "text/html"
                    response_headers["Cache-Control"] = "no-store"
                    html_content = self.webpage() # Generate from template
                    if html_content: 
                        response_body_bytes = html_content.encode('utf-8')
                        DPRINT(f"Ctrl.handle_client: HTML generated ({len(response_body_bytes)} bytes).")
                    else: 
                        DPRINT("Ctrl.handle_client: webpage() returned empty.")
                        response_code = 500
                        response_body_bytes = b"Template Error"

                elif path == '/style.css':
                     DPRINT("Ctrl.handle_client: Route matched '/style.css'.")
                     response_headers["Content-Type"] = "text/css"
                     response_headers["Cache-Control"] = "no-store"
                     if self.css_content: 
                         response_body_bytes = self.css_content.encode('utf-8')
                         DPRINT(f"Ctrl.handle_client: Serving CSS ({len(response_body_bytes)} bytes).")
                     else: 
                         DPRINT("Ctrl.handle_client: CSS content is missing.")
                         response_code = 404
                         response_body_bytes = b"/* CSS not found */"

                elif path == '/app.js':
                     DPRINT("Ctrl.handle_client: Route matched '/app.js'.")
                     response_headers["Content-Type"] = "application/javascript"
                     response_headers["Cache-Control"] = "no-store"
                     if self.js_content: 
                         response_body_bytes = self.js_content.encode('utf-8')
                         DPRINT(f"Ctrl.handle_client: Serving JS ({len(response_body_bytes)} bytes).")
                     else: 
                         DPRINT("Ctrl.handle_client: JS content is missing.")
                         response_code = 404
                         response_body_bytes = b"// JS not found"

                elif path == '/favicon.ico':
                     DPRINT("Ctrl.handle_client: Route matched '/favicon.ico'. Sending 404.")
                     response_code = 404
                     response_headers["Content-Type"] = "text/plain"

                elif path == '/api/board_state':
                    DPRINT("Ctrl.handle_client: Route matched '/api/board_state'.")
                    response_headers["Content-Type"] = "application/json"
                    state_obj = self.board.export_state_dict()
                    state_obj['server_log'] = self.WEB_DISPLAY_CONTENT # Add server log
                    DPRINT("Ctrl.handle_client: State exported. Serializing JSON...")
                    try: 
                        response_body_bytes = ujson.dumps(state_obj).encode('utf-8')
                        DPRINT(f"Ctrl.handle_client: JSON state serialized ({len(response_body_bytes)} bytes).")
                    except Exception as json_err: 
                        DPRINT(f"JSON dump error: {json_err}")
                        response_code=500
                        response_body_bytes=b'{"status":"error","message":"JSON state error"}'

                elif path == '/control/load_templates':
                     DPRINT("Ctrl.handle_client: Route matched '/control/load_templates'.")
                     response_headers["Content-Type"] = "application/json"
                     success = self.load_templates()
                     response_body_bytes = ujson.dumps({"status": "success" if success else "error", "message": "Templates loaded." if success else "Failed."}).encode('utf-8')

                elif path == '/control/free_templates':
                     DPRINT("Ctrl.handle_client: Route matched '/control/free_templates'.")
                     response_headers["Content-Type"] = "application/json"
                     success = self.free_templates()
                     response_body_bytes = ujson.dumps({"status": "success" if success else "error", "message": "Templates freed." if success else "Failed."}).encode('utf-8')

                elif path.startswith(('/pin/', '/pwm/', '/ble/', '/wifi/', '/console/')):
                    DPRINT(f"Ctrl.handle_client: Route matched API '{path}'. Passing to handler...")
                    response_headers["Content-Type"] = "application/json"
                    result_obj = await self.handler.handle_request(path)
                    DPRINT(f"Ctrl.handle_client: Handler returned. Serializing JSON...")
                    try: 
                        response_body_bytes = ujson.dumps(result_obj).encode('utf-8')
                        DPRINT(f"Ctrl.handle_client: JSON result serialized ({len(response_body_bytes)} bytes).")
                    except Exception as json_err: 
                        DPRINT(f"JSON dump error (handler): {json_err}")
                        response_code=500
                        response_body_bytes=b'{"status":"error","message":"JSON result error"}'

                else: # Unknown path
                     DPRINT(f"Ctrl.handle_client: Unknown path '{path}', sending 404.")
                     response_code = 404
                     response_headers["Content-Type"] = "text/plain"
                     response_body_bytes = b"Not Found"
            
            else:
                 DPRINT(f"Ctrl.handle_client: Skipping routing due to earlier error (Code {response_code}).")

            # --- Send Response ---
            DPRINT(f"Ctrl.handle_client: Sending Status {response_code}...")
            writer.write(f"HTTP/1.1 {response_code} OK\r\n".encode('utf-8')) # Simplified status
            
            DPRINT("Ctrl.handle_client: Sending Headers...")
            for key, value in response_headers.items(): 
                writer.write(f"{key}: {value}\r\n".encode('utf-8'))
            writer.write(f"Content-Length: {len(response_body_bytes)}\r\n\r\n".encode('utf-8')) # Blank line needed
            
            DPRINT("Ctrl.handle_client: Draining headers...")
            await writer.drain() # Ensure headers sent
            DPRINT("Ctrl.handle_client: Headers drained.")

            if response_body_bytes:
                DPRINT(f"Ctrl.handle_client: Sending body ({len(response_body_bytes)} bytes)...")
                await writer.awrite(response_body_bytes)
                DPRINT("Ctrl.handle_client: Draining body...")
                await writer.drain()
                DPRINT("Ctrl.handle_client: Body drained.")
            else:
                DPRINT("Ctrl.handle_client: No body to send.")
                
            response_sent = True
            DPRINT(f"Ctrl.handle_client: Response {response_code} sent complete.")

        except uasyncio.CancelledError: 
            DPRINT("Ctrl.handle_client: Task cancelled.")
            raise
        except OSError as e: 
            DPRINT(f"Ctrl.handle_client: OS Error: {e} (Client likely disconnected)")
        except Exception as e:
            DPRINT(f"Ctrl.handle_client: Unexpected Exception: {e}")
            sys.print_exception(e)
            if not response_sent and writer and not writer.is_closing():
                try: # Send 500
                    DPRINT("Ctrl.handle_client: Attempting to send 500 error to client...")
                    err_bytes = ujson.dumps({"status": "error", "message": f"Server Error: {e}"}).encode('utf-8')
                    writer.write(b"HTTP/1.1 500 ISE\r\nContent-Type: application/json\r\nConnection: close\r\n")
                    writer.write(f"Content-Length: {len(err_bytes)}\r\n\r\n".encode('utf-8'))
                    await writer.drain()
                    await writer.awrite(err_bytes)
                    await writer.drain()
                    DPRINT("Ctrl.handle_client: 500 error sent.")
                except Exception as send_err: 
                    DPRINT(f"Ctrl.handle_client: Error sending 500: {send_err}")
        finally:
            DPRINT("Ctrl.handle_client: FINALLY block. Closing connection.")
            if writer: 
                writer.close()
                await writer.wait_closed()
            DPRINT("Ctrl.handle_client: Connection fully closed.")

    # --- Background Task ---
    async def background_update_task(self, interval_ms=5000):
        DPRINT("Ctrl.background_task: Starting background input scanner...")
        while True:
            try:
                if hasattr(self.board, 'update_inputs') and callable(self.board.update_inputs): 
                    # DPRINT("Ctrl.background_task: Calling board.update_inputs()...") # Too noisy
                    await self.board.update_inputs()
                else: 
                    DPRINT("Ctrl.background_task: board.update_inputs missing.")
                    await uasyncio.sleep_ms(interval_ms * 5) # Sleep longer if method missing
            except Exception as e: 
                DPRINT(f"Ctrl.background_task: Error: {e}")
                sys.print_exception(e)
            await uasyncio.sleep_ms(interval_ms)


    # --- Main Server Entry Point (Async) ---
    async def serve_async(self):
        if not self.ip or self.ip == "0.0.0.0": 
            DPRINT("Ctrl.serve_async: No valid IP. Server NOT started.")
            return
        DPRINT(f"Ctrl.serve_async: Starting async server on {self.ip}:80")
        try:
            server = await uasyncio.start_server(self.handle_client, self.ip, 80, backlog=2)
            DPRINT("Ctrl.serve_async: Server started and listening.")
            self.html_out(f"Async Server LIVE at http://{self.ip}/")
            print(f"--- ASYNC SERVER RUNNING at http://{self.ip}/ ---")
            while True:
                await uasyncio.sleep(60) # Keep alive loop
        except OSError as e:
            DPRINT(f"Ctrl.serve_async: FATAL BIND/START ERROR: {e}")
            if e.args[0] == 98: # EADDRINUSE
                print("FATAL: Port 80 busy. Rebooting...")
                self.html_out("FATAL: Port 80 busy. Rebooting...", 'error')
                time.sleep(1)
                machine.reset()
            else: 
                print(f"FATAL ASYNC START ERROR: {e}. Halting.")
                self.html_out(f"FATAL: Server start error: {e}. Halting.", 'error')
                # Halt execution or loop indefinitely
                while True: 
                    machine.idle() 
        except Exception as e:
             DPRINT(f"Ctrl.serve_async: UNEXPECTED SERVER ERROR: {e}")
             sys.print_exception(e)
             self.html_out(f"FATAL: Server loop error: {e}. Resetting.", 'error')
             print("Forcing reset...")
             time.sleep(1)
             machine.reset()
eof


cat >> html_server.py <<'eof'
import machine
import time
import config
import network # Ensure network is imported
import uasyncio # Import asyncio

def DPRINT(s):
    if config.DEBUG:
        print(s)

DPRINT("--- html_server.py: TOP LEVEL START ---")

# --- Ensure Wi-Fi is Connected (Synchronous) ---
wlan_ok = False
# Check if wlan exists and is connected
if 'wlan' in globals() and isinstance(globals().get('wlan'), network.WLAN) and globals().get('wlan').isconnected():
    DPRINT("Server: Wi-Fi already connected from boot.py.")
    wlan = globals()['wlan'] # Make sure wlan is accessible locally
    wlan_ok = True
else:
    DPRINT("Server: 'wlan' not connected/found. Attempting manual connect...")
    APP_SSID = 'ANTEATER2' # Fallback credentials
    APP_PASSWORD = 'Juliaz13'
    try:
        nic = network.WLAN(network.STA_IF)
        nic.active(True)
        nic.connect(APP_SSID, APP_PASSWORD)
        wait = 15; start_time = time.ticks_ms(); timeout = 15000
        while not nic.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout: break
            DPRINT(f"Server: Manual connect waiting...")
            time.sleep(1)
        if nic.isconnected():
            globals()['wlan'] = nic # Make it globally accessible
            wlan = nic # Make accessible locally
            DPRINT("Server: Manual Wi-Fi connection SUCCESS.")
            wlan_ok = True
        else: DPRINT("Server: Manual Wi-Fi connection FAILED. Halting.")
    except Exception as e:
         DPRINT(f"Server: Error during manual Wi-Fi connect: {e}")

# If Wi-Fi failed, halt execution
if not wlan_ok:
     print("FATAL: Could not establish Wi-Fi connection. Stopping.")
     # Loop forever or reset? Loop is safer than reset loop.
     while True: machine.idle()


DPRINT("Server: Wi-Fi OK. Proceeding...")

# --- Imports that depend on other files ---
try:
    DPRINT("Server: Importing Html_controler...")
    from html_controler import Html_controler
except Exception as e:
    DPRINT(f"Server: FATAL: Failed to import Html_controler: {e}")
    import sys; sys.print_exception(e)
    print("Forcing reset due to import error...")
    time.sleep(2); machine.reset()


DPRINT("Server: Imports complete.")

# --- Main Async Function ---
async def main():
    DPRINT("Server: main() coroutine started.")
    global wlan # Need access to the global wlan object

    # Credentials for controller
    APP_SSID = 'ANTEATER2'
    APP_PASSWORD = 'Juliaz13'

    controller = None
    server_task = None
    pin_worker_task = None
    input_scan_task = None

    try:
        DPRINT("Server.main: Instantiating Html_controler...")
        # Pass the globally confirmed wlan object
        controller = Html_controler(wlan, APP_SSID, APP_PASSWORD)
        DPRINT("Server.main: Html_controler instantiated.")

        # --- Create and schedule background tasks ---
        DPRINT("Server.main: Creating background tasks...")

        # Create the pin action worker task from the board
        if hasattr(controller.board, '_process_pin_actions'):
            pin_worker_task = uasyncio.create_task(controller.board._process_pin_actions())
            DPRINT("Server.main: Pin worker task created.")
        else: DPRINT("Server.main: ERROR - Pin worker method missing on board!")

        # Create the input scanning task from the controller
        if hasattr(controller, 'background_update_task'):
            input_scan_task = uasyncio.create_task(controller.background_update_task())
            DPRINT("Server.main: Input scan task created.")
        else: DPRINT("Server.main: ERROR - Input scan method missing on controller!")

        # Create the web server task (serve_async now just starts the listener)
        if hasattr(controller, 'serve_async'):
            server_task = uasyncio.create_task(controller.serve_async())
            DPRINT("Server.main: Web server task created.")
        else: DPRINT("Server.main: ERROR - Web server method missing on controller!")

        # Check if essential tasks were created
        if not server_task or not pin_worker_task or not input_scan_task:
             raise RuntimeError("Failed to create essential background tasks.")


        DPRINT("Server.main: All tasks created. Running forever (via server task)...")
        # await server_task # This will run indefinitely
        # Or just let the loop run - tasks are scheduled. Keep main alive.
        while True:
            # Maybe add a check here to see if tasks are still running?
            # if server_task.done() or pin_worker_task.done() or input_scan_task.done():
            #     DPRINT("Server.main: A background task has unexpectedly stopped!")
            #     # Attempt restart? Or just reset?
            #     break # Exit loop for cleanup/reset
            await uasyncio.sleep(60) # Heartbeat sleep

    except KeyboardInterrupt:
        DPRINT("\nServer.main: KeyboardInterrupt caught. Cancelling tasks...")
    except Exception as e:
        DPRINT(f"Server.main: UNEXPECTED FATAL ERROR in main loop: {e}")
        import sys; sys.print_exception(e)
    finally:
        # --- Cleanup ---
        DPRINT("Server.main: Cleaning up tasks...")
        if server_task: server_task.cancel()
        if pin_worker_task: pin_worker_task.cancel()
        if input_scan_task: input_scan_task.cancel()

        # Wait briefly for tasks to acknowledge cancellation
        await uasyncio.sleep_ms(200)

        if controller and hasattr(controller, 'board') and controller.board:
             # Stop BLE synchronously during cleanup
             DPRINT("Server.main: Stopping BLE...")
             # Need a synchronous stop or run stop within loop briefly
             # For simplicity, assume stop_ble_advertising is robust enough if called async
             # but might be better to have a sync version for cleanup.
             # Let's try calling the async version and sleeping.
             try:
                  stop_task = uasyncio.create_task(controller.board.stop_ble_advertising())
                  await uasyncio.wait_for(stop_task, 1.0) # Wait up to 1 sec
             except uasyncio.TimeoutError: DPRINT("BLE stop timed out.")
             except Exception as ble_stop_err: DPRINT(f"Error stopping BLE: {ble_stop_err}")

        DPRINT("Server.main: Cleanup attempt complete.")
        # Optional: Reset after cleanup on error?
        # machine.reset()


# --- Run the Async Event Loop ---
if __name__ == "__main__":
    DPRINT("Server: __main__ block executing.")
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        DPRINT("Server: Loop stopped by KeyboardInterrupt.")
    except Exception as e:
         DPRINT(f"Server: Asyncio loop error: {e}")
         import sys; sys.print_exception(e)
    finally:
        # Reset the event loop state in case of errors or KeyboardInterrupt
        uasyncio.new_event_loop()
        DPRINT("Server: Asyncio loop finished or cleared.")
        # Consider a reset here if the loop exits unexpectedly
        # print("Resetting device...")
        # machine.reset()
eof


cat >> pico_adc.py <<'eof'
import machine
import config

# Need Pico_pin for type hints/constants if used, though not strictly necessary here
try: from pico_pin import Pico_pin
except: Pico_pin = None

def DPRINT(s):
    if config.DEBUG:
        print(s)

class Pico_adc:
    """
    Models the ADC (Analog-to-Digital Converter) subsystem.
    Manages all ADC channels. Assumes synchronous ADC reads are acceptable.
    """

    CONVERSION_FACTOR = 3.3 / 65535.0

    def __init__(self, board_pins):
        DPRINT("ADC: Initializing ADC subsystem...")
        # Link to the board's pins using their IDs
        self._pin_adc0_id = 26
        self._pin_adc1_id = 27
        self._pin_adc2_id = 28

        self._pin_adc0 = self._find_pin(board_pins, self._pin_adc0_id)
        self._pin_adc1 = self._find_pin(board_pins, self._pin_adc1_id)
        self._pin_adc2 = self._find_pin(board_pins, self._pin_adc2_id)

        # Initialize machine.ADC objects
        DPRINT("ADC: Creating machine.ADC instances...")
        try:
            # Use pin ID directly for machine.ADC constructor
            self.adc_ch0 = machine.ADC(self._pin_adc0_id) if self._pin_adc0 else None
            self.adc_ch1 = machine.ADC(self._pin_adc1_id) if self._pin_adc1 else None
            self.adc_ch2 = machine.ADC(self._pin_adc2_id) if self._pin_adc2 else None
            self.adc_ch_temp = machine.ADC(4) # Internal temp sensor is ADC(4)
            DPRINT("ADC: machine.ADC instances created.")
        except Exception as e:
            DPRINT(f"ADC: ERROR creating machine.ADC instances: {e}")
            self.adc_ch0 = self.adc_ch1 = self.adc_ch2 = self.adc_ch_temp = None


        # Set the corresponding pins' controller to ADC (using sync init is okay here)
        # Ensure pin objects exist before trying to modify them
        if self._pin_adc0 and Pico_pin:
            # Use sync init for simplicity during setup
            self._pin_adc0._sync_init_internal(controller=Pico_pin.CTRL_ADC)
            DPRINT(f"ADC: Set {self._pin_adc0.name} controller to ADC.")
        if self._pin_adc1 and Pico_pin:
            self._pin_adc1._sync_init_internal(controller=Pico_pin.CTRL_ADC)
            DPRINT(f"ADC: Set {self._pin_adc1.name} controller to ADC.")
        if self._pin_adc2 and Pico_pin:
            self._pin_adc2._sync_init_internal(controller=Pico_pin.CTRL_ADC)
            DPRINT(f"ADC: Set {self._pin_adc2.name} controller to ADC.")

        DPRINT("ADC: Subsystem init complete.")

    def _find_pin(self, pins, pin_id):
        """Helper to find a pin by its ID from the board's list."""
        if not pins: return None
        for pin in pins:
             # Check if pin object has _id before accessing
            if hasattr(pin, '_id') and pin._id == pin_id:
                return pin
        DPRINT(f"ADC: WARNING - Pin ID {pin_id} not found in board pins list.")
        return None

    def read_temp_c(self):
        """Reads the internal temperature sensor in Celsius. Synchronous."""
        if not self.adc_ch_temp: return -999.9
        try:
            # Add small delay/yield if reads are slow? Not usually needed for ADC.
            temp_val = self.adc_ch_temp.read_u16() * self.CONVERSION_FACTOR
            # Formula from Pico datasheet section 4.9.5. Temperature Sensor
            return 27.0 - (temp_val - 0.706) / 0.001721
        except Exception as e:
            DPRINT(f"ADC: Error reading temp: {e}")
            return -999.0 # Use float for consistency

    def read_u16(self, channel):
        """Reads the raw 16-bit value from an ADC channel. Synchronous."""
        adc_instance = None
        if channel == 0: adc_instance = self.adc_ch0
        elif channel == 1: adc_instance = self.adc_ch1
        elif channel == 2: adc_instance = self.adc_ch2

        if not adc_instance: return 0

        try:
            # Add small delay/yield?
            return adc_instance.read_u16()
        except Exception as e:
            DPRINT(f"ADC: Error reading u16 ch{channel}: {e}")
            return 0

    def read_volts(self, channel):
        """Reads the voltage from an ADC channel. Synchronous."""
        return self.read_u16(channel) * self.CONVERSION_FACTOR
eof


cat >> pico_board.py <<'eof'
import machine
import network
import ubluetooth
import utime
from micropython import const
import config
import uasyncio # Added asyncio

# Import hardware models
try:
    from pico_pin import Pico_pin
    from pico_adc import Pico_adc
except ImportError:
    print("Pico_board: FATAL: Failed to import Pin/ADC models.")
    # Define dummy classes
    class Pico_pin: pass
    class Pico_adc: pass


def DPRINT(s):
    if config.DEBUG:
        print(s)

# BLE Constants
ADV_FLAG_LE_GENERAL_DISCOVERABLE = const(0x02)
ADV_TYPE_NAME_COMPLETE = const(0x09)

class Pico_board:
    """ Pico W Digital Twin Model - Uses queue for pin actions, lock for others. """
    def __init__(self, wlan, initial_ssid, initial_password):
        DPRINT("Board: Initializing Pico_board...")
        self.nic = wlan
        self.ssid = initial_ssid
        self.password = initial_password
        DPRINT("Board: Wi-Fi linked.")

        # --- Hardware Lock (for non-pin actions like BLE/WiFi/Direct HW access) ---
        self.hw_lock = uasyncio.Lock()
        DPRINT("Board: Hardware lock created.")

        # --- Pin Action Queue (for pin mode/value/pwm changes) ---
        self.pin_action_queue = uasyncio.Queue(maxsize=30) # Increased buffer size
        DPRINT("Board: Pin action queue created.")

        # --- Pins (pass lock to pins) ---
        DPRINT("Board: Initializing Pins...")
        # Lists based on physical header layout
        self.pins_left = [
            Pico_pin(0, "GP0 / UART0 TX", self.hw_lock), Pico_pin(1, "GP1 / UART0 RX", self.hw_lock), Pico_pin(-3, "GND", self.hw_lock),
            Pico_pin(2, "GP2", self.hw_lock), Pico_pin(3, "GP3", self.hw_lock), Pico_pin(4, "GP4 / UART1 TX", self.hw_lock),
            Pico_pin(5, "GP5 / UART1 RX", self.hw_lock), Pico_pin(-8, "GND", self.hw_lock), Pico_pin(6, "GP6", self.hw_lock),
            Pico_pin(7, "GP7", self.hw_lock), Pico_pin(8, "GP8", self.hw_lock), Pico_pin(9, "GP9", self.hw_lock),
            Pico_pin(-13, "GND", self.hw_lock), Pico_pin(10, "GP10", self.hw_lock), Pico_pin(11, "GP11", self.hw_lock),
            Pico_pin(12, "GP12", self.hw_lock), Pico_pin(13, "GP13", self.hw_lock), Pico_pin(-18, "GND", self.hw_lock),
            Pico_pin(14, "GP14", self.hw_lock), Pico_pin(15, "GP15", self.hw_lock)
        ] # 20 pins

        self.pins_right = [
            Pico_pin(-40, "VBUS", self.hw_lock), Pico_pin(-39, "VSYS", self.hw_lock), Pico_pin(-38, "GND", self.hw_lock),
            Pico_pin(-37, "3V3_EN", self.hw_lock), Pico_pin(-36, "3V3(OUT)", self.hw_lock), Pico_pin(-35, "ADC_VREF", self.hw_lock),
            Pico_pin(28, "GP28 (ADC2)", self.hw_lock, is_adc=True), Pico_pin(-33, "GND", self.hw_lock), # AGND mapped to GND
            Pico_pin(27, "GP27 (ADC1)", self.hw_lock, is_adc=True), Pico_pin(26, "GP26 (ADC0)", self.hw_lock, is_adc=True),
            Pico_pin(-30, "RUN", self.hw_lock), Pico_pin(22, "GP22", self.hw_lock), Pico_pin(-28, "GND", self.hw_lock),
            Pico_pin(21, "GP21", self.hw_lock), Pico_pin(20, "GP20", self.hw_lock), Pico_pin(19, "GP19", self.hw_lock),
            Pico_pin(18, "GP18", self.hw_lock), Pico_pin(-23, "GND", self.hw_lock), Pico_pin(17, "GP17", self.hw_lock),
            Pico_pin(16, "GP16", self.hw_lock)
        ] # 20 pins

        # Onboard LED is GP25 on Pico W, not on header
        self.onboard_led_pin = Pico_pin(25, "GP25 (LED)", self.hw_lock)

        self.pins = self.pins_left + self.pins_right # 40 header pins
        # Create a list of only the controllable GPIO pins for easier iteration
        self.all_gpio_pins = [p for p in self.pins if hasattr(p,'_id') and p._id >= 0] + [self.onboard_led_pin]
        DPRINT(f"Board: Pin lists created ({len(self.pins)} header, {len(self.all_gpio_pins)} controllable).")

        # --- ADC ---
        DPRINT("Board: Initializing ADC...")
        self.adc = Pico_adc(self.all_gpio_pins) # Pass all controllable pins
        DPRINT("Board: ADC initialized.")

        # --- Pin Aliases & Defaults (Sync init ok here) ---
        self.gp13 = self.get_pin_by_id(13)
        self.gp14 = self.get_pin_by_id(14)
        self.gp15 = self.get_pin_by_id(15)
        DPRINT("Board: Setting default pin modes (sync)...")
        # Use sync init for defaults during construction
        if self.gp13: self.gp13._sync_init_internal(mode=Pico_pin.MODE_OUT)
        if self.gp14: self.gp14._sync_init_internal(mode=Pico_pin.MODE_OUT)
        if self.gp15: self.gp15._sync_init_internal(mode=Pico_pin.MODE_OUT)
        if self.onboard_led_pin: self.onboard_led_pin._sync_init_internal(mode=Pico_pin.MODE_OUT)
        DPRINT("Board: Default modes set.")

        # --- Bluetooth (Sync init ok here) ---
        DPRINT("Board: Initializing Bluetooth...")
        self.ble = None
        self._ble_adv_active = False # Internal flag to track advertising state
        self.ble_name = "Pico-WebIO"
        self._sync_init_ble_internal() # Use sync internal version for init

        DPRINT("Board: Pico_board init complete.")


    # --- Pin Action Worker Task ---
    async def _process_pin_actions(self):
        """Dedicated async task to process pin actions sequentially from the queue."""
        DPRINT("Board._process_pin_actions: Worker task started.")
        while True:
            action = None # Clear action for error handling
            pin = None    # Clear pin for error handling
            try:
                # Wait indefinitely for an action from the queue
                action = await self.pin_action_queue.get()
                action_type, pin_id, *args = action
                DPRINT(f"BoardWorker: Dequeued action '{action_type}' for pin {pin_id} with args {args}")

                pin = self.get_pin_by_id(pin_id)
                if not pin:
                    DPRINT(f"BoardWorker: Pin {pin_id} not found. Skipping action.")
                    self.pin_action_queue.task_done()
                    continue

                # Acquire lock before modifying the pin
                DPRINT(f"BoardWorker: Waiting for lock for pin {pin_id} action '{action_type}'...")
                async with self.hw_lock: # No timeout needed if lock usage is correct
                    DPRINT(f"BoardWorker: Acquired lock for pin {pin_id} action '{action_type}'.")

                    # --- Perform Action ---
                    if action_type == 'mode':
                        mode_str, pull_str = args
                        # Pin.init handles logic for mode/pull/controller transitions
                        await pin.init(mode=Pico_pin.str_to_mode(mode_str), # Helper func needed?
                                       pull=Pico_pin.str_to_pull(pull_str), # Helper func needed?
                                       controller=Pico_pin.mode_str_to_controller(mode_str, pin.is_adc_capable)) # Helper
                        DPRINT(f"BoardWorker: Pin {pin_id} mode set via worker.")

                    elif action_type == 'value':
                        value = args[0]
                        # Pin setter handles mode check internally
                        await pin.set_value_async(value)
                        DPRINT(f"BoardWorker: Pin {pin_id} value set via worker.")

                    elif action_type == 'pwm':
                         freq, duty_pc = args
                         if pin.pwm_instance:
                              # PWM setters are sync, lock already held
                              if freq is not None: pin.pwm_instance.freq = freq
                              if duty_pc is not None: pin.pwm_instance.duty_percent = duty_pc
                              DPRINT(f"BoardWorker: Pin {pin_id} PWM set via worker.")
                         else: DPRINT(f"BoardWorker: Pin {pin_id} has no PWM instance. Skipping.")
                    else:
                        DPRINT(f"BoardWorker: Unknown action type '{action_type}'. Skipping.")

                    await uasyncio.sleep_ms(0) # Yield after hardware op

                # Lock released automatically
                DPRINT(f"BoardWorker: Released lock for pin {pin_id} action '{action_type}'.")
                self.pin_action_queue.task_done() # Signal completion

            except uasyncio.CancelledError:
                DPRINT("Board._process_pin_actions: Task cancelled.")
                raise # Re-raise CancelledError to allow clean task shutdown
            except Exception as e:
                DPRINT(f"Board._process_pin_actions: ERROR processing action {action} for pin {pin}: {e}")
                import sys; sys.print_exception(e)
                # Ensure task_done is called if get() succeeded but processing failed
                if action is not None and self.pin_action_queue.empty(): # Check if queue empty after potential get()
                     try:
                          # This logic might be flawed if queue fills again quickly.
                          # Better: Check if the failed action *was* the one we got.
                          # Simplest: Just call task_done and let potential errors happen.
                          self.pin_action_queue.task_done()
                          DPRINT("BoardWorker: Called task_done after error.")
                     except ValueError: pass # task_done might fail if already called

                await uasyncio.sleep_ms(100) # Delay before next attempt


    # --- Methods that queue pin actions (Synchronous) ---
    def set_pin_mode(self, pin_id, mode_str, pull_str=None):
        """ Sync Action: Queue request to set pin mode/pull. """
        DPRINT(f"Board.set_pin_mode: Queuing pin {pin_id} -> Mode={mode_str}, Pull={pull_str}")
        try:
            # Queue tuple: (action_type, pin_id, mode_str, pull_str)
            self.pin_action_queue.put_nowait(('mode', pin_id, mode_str, pull_str))
            return True, "Mode change queued."
        except uasyncio.QueueFull: DPRINT("Queue full!"); return False, "Queue full."
        except Exception as e: DPRINT(f"Error queueing: {e}"); return False, f"Error: {e}"

    def set_pin_value(self, pin_id, value):
        """ Sync Action: Queue request to set pin value. """
        DPRINT(f"Board.set_pin_value: Queuing pin {pin_id} -> Value={value}")
        try:
            self.pin_action_queue.put_nowait(('value', pin_id, value))
            return True, "Value change queued."
        except uasyncio.QueueFull: DPRINT("Queue full!"); return False, "Queue full."
        except Exception as e: DPRINT(f"Error queueing: {e}"); return False, f"Error: {e}"

    def set_pwm_params(self, pin_id, freq=None, duty_pc=None):
        """ Sync Action: Queue request to set PWM params. """
        DPRINT(f"Board.set_pwm_params: Queuing pin {pin_id} -> Freq={freq}, DutyPC={duty_pc}")
        try:
            freq_int = int(freq) if freq is not None else None
            duty_float = float(duty_pc) if duty_pc is not None else None
            self.pin_action_queue.put_nowait(('pwm', pin_id, freq_int, duty_float))
            return True, "PWM change queued."
        except uasyncio.QueueFull: DPRINT("Queue full!"); return False, "Queue full."
        except (ValueError, TypeError) as e: DPRINT(f"Invalid value: {e}"); return False, "Invalid value"
        except Exception as e: DPRINT(f"Error queueing: {e}"); return False, f"Error: {e}"

    # --- Other methods ---
    async def update_inputs(self): # Keep async
        DPRINT("Board.update_inputs (async): Scanning hardware inputs...")
        # Use simple loop instead of gather for less overhead?
        for pin in self.all_gpio_pins:
             if pin.mode == "IN":
                  await pin.read_input_value() # This method acquires the lock internally
        DPRINT("Board.update_inputs (async): Scan complete.")


    def export_state_dict(self): # Keep sync
        # (Implementation remains the same - reads cached state)
        DPRINT("Board.export_state: Exporting board state...")
        pin_states = []
        for pin in self.all_gpio_pins:
            state = { "id": pin._id, "name": pin.name, "mode": pin.mode, "value": pin.value, "pull": pin.pull_str, "controller": pin.controlled_by }
            if pin.pwm_instance: state["pwm_freq"] = pin.pwm_instance.freq; state["pwm_duty"] = pin.pwm_instance.duty_percent
            pin_states.append(state)
        temp_c = self.get_internal_temp()
        wifi_info = ('0.0.0.0',) * 4 # Default
        if hasattr(self, 'nic') and self.nic and self.nic.isconnected(): # Add checks
            wifi_info = self.nic.ifconfig()

        time_tuple = self.get_time_tuple(); time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*time_tuple[0:6])
        state = {
            "pins": pin_states,
            "status": { "ip": wifi_info[0], "netmask": wifi_info[1], "gateway": wifi_info[2], "dns": wifi_info[3], "temp_c": f"{temp_c:.2f}", "time": time_str, "ble_status": "Advertising" if self.ble_is_advertising else "Inactive", "ble_name": self.ble_name, "wifi_ssid": self.ssid },
            "adc_volts": { "adc0": f"{self.adc.read_volts(0):.3f}", "adc1": f"{self.adc.read_volts(1):.3f}", "adc2": f"{self.adc.read_volts(2):.3f}" }
        }
        DPRINT("Board.export_state: State export complete.")
        return state

    @property
    def ble_is_advertising(self): return self._ble_adv_active # Sync property read ok

    def get_pin_by_id(self, pin_id): # Sync ok
        # Ensure pin_id is int
        try: pin_id_int = int(pin_id)
        except: return None
        for pin in self.all_gpio_pins:
            if hasattr(pin, '_id') and pin._id == pin_id_int: return pin
        DPRINT(f"Board.get_pin_by_id: Pin ID {pin_id_int} not found!"); return None

    def get_internal_temp(self): # Sync ok
        if hasattr(self, 'adc') and self.adc: return self.adc.read_temp_c()
        return -999.0

    def get_time_tuple(self): return utime.localtime() # Sync ok

    async def connect_wifi(self, ssid, password): # Keep async, use lock
        DPRINT(f"Board.connect_wifi (async): Reconnect to '{ssid}'...")
        self.ssid = ssid; self.password = password
        if not hasattr(self, 'nic') or self.nic is None: DPRINT("WLAN obj missing."); return False

        connected = False
        async with self.hw_lock: # Lock during network state change
            DPRINT("Board.connect_wifi: Acquired lock.");
            try:
                if self.nic.isconnected(): DPRINT("Disconnecting..."); self.nic.disconnect(); await uasyncio.sleep_ms(1000)
                self.nic.active(True); self.nic.connect(self.ssid, self.password)
                DPRINT("Board.connect_wifi: Connect initiated.")
            except Exception as e:
                DPRINT(f"Board.connect_wifi: Error during disconnect/connect: {e}")
                return False # Exit if error occurs under lock
        # Release lock before waiting loop

        start_time = utime.ticks_ms(); timeout = 15000
        while not self.nic.isconnected():
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout: DPRINT("Timeout."); break
            DPRINT("Waiting..."); await uasyncio.sleep_ms(500) # Yield control

        connected = self.nic.isconnected(); DPRINT(f"Connected={connected}")
        if not connected:
            DPRINT(f"FAILED connect to {ssid}.")
            # Consider deactivating radio again? Needs lock.
            # async with self.hw_lock: self.nic.active(False)
        return connected

    # --- Internal Sync BLE Init (for constructor) ---
    def _sync_init_ble_internal(self):
        DPRINT("Board._sync_init_ble...")
        try:
            self.ble = ubluetooth.BLE(); self.ble.active(True); self._ble_adv_active = False
            DPRINT("BLE radio activated (sync).")
        except Exception as e:
            self.ble = None; self._ble_adv_active = False
            DPRINT(f"FAILED BLE init (sync): {e}")

    # --- Async BLE Methods (use lock) ---
    async def init_ble(self): # Public async version
        DPRINT("Board.init_ble (async)...")
        if self.ble: DPRINT("Already init."); return True
        async with self.hw_lock: # Lock during BLE init
            # Re-check inside lock
            if self.ble: return True
            try:
                self.ble = ubluetooth.BLE(); self.ble.active(True); self._ble_adv_active = False
                DPRINT("BLE radio activated.")
                return True
            except Exception as e:
                self.ble = None; self._ble_adv_active = False
                DPRINT(f"FAILED BLE init: {e}"); return False

    def _adv_encode(self, adv_type, value): return bytes([len(value) + 1, adv_type]) + value

    async def start_ble_advertising(self): # Async, uses lock
        DPRINT(f"Board.start_ble_adv (async) as '{self.ble_name}'...")
        if not self.ble:
            if not await self.init_ble(): return False # Await init

        is_active = False
        try: is_active = self.ble.active()
        except: pass
        if not is_active: DPRINT("BLE radio inactive, cannot start adv."); return False

        # Check flag outside lock for quick exit
        if self._ble_adv_active: DPRINT("Already advertising."); return True

        async with self.hw_lock: # Lock before advertising
            if self._ble_adv_active: DPRINT("Already adv (checked under lock)."); return True # Re-check
            try:
                name_bytes = self.ble_name.encode('utf-8')[:27]
                adv_data = bytes([0x02, 0x01, ADV_FLAG_LE_GENERAL_DISCOVERABLE]) + self._adv_encode(ADV_TYPE_NAME_COMPLETE, name_bytes)
                DPRINT(f"Board.start_ble_adv: Payload (len {len(adv_data)}): {adv_data}")
                self.ble.gap_advertise(100_000, adv_data=adv_data, connectable=False)
                await uasyncio.sleep_ms(10) # Small delay after starting
                self._ble_adv_active = True # Update flag under lock
                DPRINT("Advertising started."); return True
            except Exception as e:
                self._ble_adv_active = False # Update flag under lock
                DPRINT(f"ERROR starting advertising: {e}")
                # Try cycling radio state (still under lock) - might deadlock if active() blocks? Risky.
                # try: self.ble.active(False); await uasyncio.sleep_ms(100); self.ble.active(True); DPRINT("Cycled BLE radio state.")
                # except: DPRINT("Error cycling BLE radio state.")
                return False

    async def stop_ble_advertising(self): # Async, uses lock
        DPRINT("Board.stop_ble_adv (async)...")
        is_active = False
        try: is_active = self.ble and self.ble.active()
        except: pass
        if not is_active: DPRINT("BLE inactive/init."); self._ble_adv_active = False; return
        if not self._ble_adv_active: DPRINT("Already stopped (per flag)."); return

        async with self.hw_lock: # Lock before stopping
            if not self._ble_adv_active: DPRINT("Already stopped (checked lock)."); return # Re-check
            try:
                self.ble.gap_advertise(None)
                await uasyncio.sleep_ms(10) # Small delay after stopping
                self._ble_adv_active = False # Update flag under lock
                DPRINT("Advertising stopped.")
            except Exception as e:
                self._ble_adv_active = False # Update flag under lock
                DPRINT(f"ERROR stopping advertising: {e}")

    async def set_ble_name(self, new_name): # Async, calls other async methods
        new_name = new_name[:27]
        DPRINT(f"Board.set_ble_name (async) to '{new_name}'")
        was_advertising = self.ble_is_advertising # Read property (sync ok)
        if was_advertising:
            await self.stop_ble_advertising() # Call async stop (uses lock)
            await uasyncio.sleep_ms(200) # Yield/delay

        self.ble_name = new_name # Setting string sync ok

        if was_advertising:
            DPRINT("Board.set_ble_name: Restarting advertising...")
            return await self.start_ble_advertising() # Call async start (uses lock)
        else:
            DPRINT("Board.set_ble_name: Name set, advertising remains off.")
            return True

    # --- Add log message method ---
    # This assumes html_out is available via controller instance passed elsewhere or monkeypatched
    # It's better if html_controler handles logging based on board state changes.
    # Let's remove this for now and handle logging purely in html_controler.
    # def log_message(self, text, tag='info'):
    #      # This method needs access to the html_out function from the controller
    #      # It's currently added dynamically in html_controler.__init__
    #      pass

# --- Add Pin helper functions if needed ---
# These need to be defined *inside* the Pico_pin class or passed self
# Pico_pin.str_to_mode = lambda s: Pico_pin.MODE_OUT if s=='OUT' else Pico_pin.MODE_IN # Example
# Pico_pin.str_to_pull = lambda s: Pico_pin.PULL_UP if s=='UP' else Pico_pin.PULL_DOWN if s=='DOWN' else Pico_pin.PULL_NONE
# Pico_pin.mode_str_to_controller = lambda s, adc: Pico_pin.CTRL_ADC if s=='ADC' and adc else Pico_pin.CTRL_PWM if s=='PWM' else Pico_pin.CTRL_GPIO


eof


cat >> pico_pin.py <<'eof'
import machine
import config
import uasyncio # Added asyncio import

try:
    from pico_pwm import Pico_pwm # Import the new PWM class
except ImportError:
     # Use local print because config might not be loaded yet
    print("Pico_pin: Failed to import Pico_pwm. PWM functions will fail.")
    Pico_pwm = None # Define as None so checks don't crash

def DPRINT(s):
    if config.DEBUG:
        print(s)

class Pico_pin:
    """
    Represents a single GPIO pin, abstracting state, mode,
    and its current hardware controller. Uses async methods with locking.
    """

    # --- Constants ---
    MODE_IN = machine.Pin.IN
    MODE_OUT = machine.Pin.OUT
    PULL_UP = machine.Pin.PULL_UP
    PULL_DOWN = machine.Pin.PULL_DOWN
    PULL_NONE = None

    CTRL_GPIO = "GPIO"
    CTRL_ADC = "ADC"
    CTRL_PWM = "PWM"
    CTRL_NONE = "N/A" # For non-GPIO pins

    def __init__(self, pin_id, name, board_lock, is_adc=False): # Pass the board's lock
        self._id = pin_id
        self.name = name
        self.is_adc_capable = is_adc
        self.pwm_instance = None
        self._pull = self.PULL_NONE
        self._lock = board_lock # Store the shared lock
        DPRINT(f"Pin: Initializing {self.name} (ID: {self._id})")

        try:
            self._pin = machine.Pin(self._id)
            self.controlled_by = self.CTRL_GPIO
        except ValueError:
            self._pin = None
            self.controlled_by = self.CTRL_NONE
            self._mode = "N/A"
            self._value_cache = "N/A" # Use cache for non-GPIO
            DPRINT(f"Pin: {self.name} is not a machine.Pin.")
            return

        # Initialize internal state defaults
        self._mode = "IN"
        self._last_out_value = 0
        self._value_cache = 0 # Cache for input reading

        # Perform initial setup synchronously without lock (only called once at startup)
        self._sync_init_internal(mode=self.MODE_IN, pull=self.PULL_NONE)
        DPRINT(f"Pin: {self.name} sync init complete. Mode=IN, Pull=None")

    def _sync_init_internal(self, mode=None, pull=None, controller=CTRL_GPIO):
        """ Internal synchronous init ONLY for use in constructor. """
        if not self._pin: return

        self.controlled_by = controller
        self._pull = pull if mode == self.MODE_IN else self.PULL_NONE # Pull only for IN

        if controller == self.CTRL_GPIO:
            if mode == self.MODE_OUT:
                self._mode = "OUT"
                try:
                    self._pin.init(mode=self.MODE_OUT)
                    self._pin.value(self._last_out_value)
                except Exception as e: DPRINT(f"Pin _sync_init: Error setting OUT {self.name}: {e}")
            else: # Default to IN
                self._mode = "IN"
                try:
                    self._pin.init(mode=self.MODE_IN, pull=self._pull)
                    self._value_cache = self._pin.value()
                except Exception as e:
                    DPRINT(f"Pin _sync_init: Error setting IN {self.name}: {e}")
                    self._value_cache = -1 # Indicate error
        elif controller == self.CTRL_ADC:
             self._mode = "ADC"
        elif controller == self.CTRL_PWM:
             self._mode = "PWM"
             # PWM instance created async later
        else: # Fallback
            self._mode = "IN"
            self.controlled_by = self.CTRL_GPIO
            self._pull = self.PULL_NONE
            try:
                self._pin.init(mode=self.MODE_IN, pull=self._pull)
                self._value_cache = self._pin.value()
            except: self._value_cache = -1

    async def init(self, mode=None, pull=None, controller=CTRL_GPIO):
        """ Initializes the pin mode, pull resistor, and controller asynchronously using lock. """
        if not self._pin: return

        async with self._lock: # Acquire lock before modifying pin state
            DPRINT(f"Pin.init (async): {self.name} | Mode={mode}, Pull={pull}, Controller={controller}")

            # --- Release PWM if changing away ---
            is_currently_pwm = (self.controlled_by == self.CTRL_PWM)
            new_controller = controller

            if is_currently_pwm and new_controller != self.CTRL_PWM:
                DPRINT(f"Pin.init: Releasing PWM from {self.name}")
                if self.pwm_instance:
                    try: self.pwm_instance.deinit()
                    except Exception as e: DPRINT(f"Pin.init: Error deinit PWM: {e}")
                    self.pwm_instance = None

            # --- Update internal state ---
            self.controlled_by = new_controller
            self._pull = pull if (mode == self.MODE_IN and self.controlled_by == self.CTRL_GPIO) else self.PULL_NONE

            # --- Apply hardware changes based on new controller ---
            try:
                if self.controlled_by == self.CTRL_GPIO:
                    if mode == self.MODE_OUT:
                        self._mode = "OUT"
                        self._pin.init(mode=self.MODE_OUT)
                        self._pin.value(self._last_out_value) # Restore last value
                        DPRINT(f"Pin.init: {self.name} set to GPIO OUT. Value={self._last_out_value}")
                    else: # Default to IN
                        self._mode = "IN"
                        self._pin.init(mode=self.MODE_IN, pull=self._pull)
                        await self._read_input_value_internal() # Read initial value async
                        pull_str = self.pull_str # Use property
                        DPRINT(f"Pin.init: {self.name} set to GPIO IN. Pull={pull_str}. Value={self._value_cache}")

                elif self.controlled_by == self.CTRL_ADC:
                    self._mode = "ADC"
                    # We might need to ensure pin is input for ADC?
                    # self._pin.init(mode=self.MODE_IN, pull=self.PULL_NONE)
                    DPRINT(f"Pin.init: {self.name} set to ADC mode.")

                elif self.controlled_by == self.CTRL_PWM:
                    self._mode = "PWM"
                    if Pico_pwm and self.pwm_instance is None:
                        try:
                            DPRINT(f"Pin.init: Creating PWM instance for {self.name}")
                            # Pico_pwm.__init__ handles setting pin OUT
                            self.pwm_instance = Pico_pwm(self._pin)
                            DPRINT(f"Pin.init: {self.name} set to PWM mode.")
                        except Exception as e:
                            DPRINT(f"Pin.init: FAILED create PWM for {self.name}: {e}")
                            # Fallback needed *within* lock
                            self._mode = "IN"; self.controlled_by = self.CTRL_GPIO; self._pull = self.PULL_NONE
                            self._pin.init(mode=self.MODE_IN, pull=self._pull); await self._read_input_value_internal()
                            DPRINT(f"Pin.init: {self.name} fallback to GPIO IN after PWM fail.")
                    elif not Pico_pwm:
                         DPRINT(f"Pin.init: PWM class missing, cannot set {self.name} to PWM.")
                         self._mode = "IN"; self.controlled_by = self.CTRL_GPIO; self._pull = self.PULL_NONE
                         self._pin.init(mode=self.MODE_IN, pull=self._pull); await self._read_input_value_internal()
                         DPRINT(f"Pin.init: {self.name} fallback to GPIO IN.")

                else: # Fallback (shouldn't happen with proper controller strings)
                    self._mode = "IN"; self.controlled_by = self.CTRL_GPIO; self._pull = self.PULL_NONE
                    self._pin.init(mode=self.MODE_IN, pull=self._pull); await self._read_input_value_internal()
                    DPRINT(f"Pin.init: {self.name} fallback to GPIO IN.")

            except Exception as e:
                 DPRINT(f"Pin.init: ERROR during hardware init for {self.name}: {e}")
                 # Revert state? Or just log? Log for now.
                 self._mode = "Error"; self.controlled_by = self.CTRL_NONE

        # Lock released automatically here

    # --- Internal async read method (assumes lock is held) ---
    async def _read_input_value_internal(self):
        """ Internal: Reads hardware if IN mode, updates cache. ASSUMES LOCK HELD. """
        if self._pin and self._mode == "IN" and self.controlled_by == self.CTRL_GPIO:
            try:
                await uasyncio.sleep_ms(0) # Yield first
                self._value_cache = self._pin.value()
            except Exception as e:
                DPRINT(f"Pin._read_internal: Error reading {self.name}: {e}")
                self._value_cache = -1 # Indicate error

    # --- Public async read method (acquires lock) ---
    async def read_input_value(self):
        """ Async: Reads hardware value if IN mode, updates cache. Uses lock. """
        async with self._lock:
            await self._read_input_value_internal()

    # --- Properties (remain synchronous, read cached state) ---
    @property
    def mode(self): return self._mode
    @property
    def pull(self): return self._pull
    @property
    def pull_str(self):
        if self._pull == self.PULL_UP: return "UP"
        if self._pull == self.PULL_DOWN: return "DOWN"
        return "NONE"

    @property
    def value(self):
        """ Gets the pin's current value (returns cached value for IN mode). """
        if not self._pin: return "N/A"
        if self.controlled_by == self.CTRL_GPIO:
            if self._mode == "OUT": return self._last_out_value
            else: return self._value_cache # IN mode returns cache
        elif self.controlled_by == self.CTRL_ADC: return "ADC"
        elif self.controlled_by == self.CTRL_PWM: return "PWM"
        else: return "N/A"

    # --- Setter becomes async ---
    async def set_value_async(self, new_val):
        """ Async: Sets the pin's value (only if in GPIO OUT mode). Uses lock. """
        # Check mode synchronously before acquiring lock
        if not self._pin or self.controlled_by != self.CTRL_GPIO or self._mode != "OUT":
            DPRINT(f"Pin.set_value_async: {self.name} | IGNORED (Not GPIO OUT)")
            return

        async with self._lock: # Acquire lock before setting value
            self._last_out_value = 1 if int(new_val) else 0
            try:
                await uasyncio.sleep_ms(0) # Yield first
                self._pin.value(self._last_out_value)
                DPRINT(f"Pin.set_value_async: {self.name} (OUT) -> {self._last_out_value}")
            except Exception as e:
                DPRINT(f"Pin.set_value_async: ERROR setting {self.name} value: {e}")

    # --- Helpers become async ---
    async def on(self): await self.set_value_async(1)
    async def off(self): await self.set_value_async(0)
    async def toggle(self):
        # Read last value outside lock, calculate next, then set inside lock
        if self._mode == "OUT":
            next_val = 1 - self._last_out_value
            await self.set_value_async(next_val)
eof


cat >> pico_pwm.py <<'eof'
import machine
import config

def DPRINT(s):
    if config.DEBUG:
        print(s)

class Pico_pwm:
    """
    Models a single PWM (Pulse Width Modulation) instance
    tied to a specific pin.
    """

    def __init__(self, machine_pin):
        DPRINT(f"PWM: Initializing for Pin {machine_pin}")
        if not machine_pin:
            raise ValueError("Invalid machine.Pin object")

        self._pin_obj = machine_pin
        # Ensure pin is OUT before PWM init
        try:
             self._pin_obj.init(mode=machine.Pin.OUT)
        except Exception as e:
             DPRINT(f"PWM Init: Error setting pin {machine_pin} to OUT: {e}")
             # Decide how to handle this - raise error or try proceeding?
             # Raising error is safer.
             raise ValueError(f"Could not set pin {machine_pin} to OUT for PWM") from e

        try:
            self._pwm = machine.PWM(self._pin_obj)
        except ValueError as e:
            # Handle cases where PWM might not be available on the pin (shouldn't happen on Pico RP2040 GPIOs)
            DPRINT(f"PWM Init: Error creating PWM on {machine_pin}: {e}")
            raise ValueError(f"Could not create PWM on pin {machine_pin}") from e

        self._freq = 1000 # Default 1 KHz
        self._duty_u16 = 0 # Default 0% duty cycle

        try:
            self._pwm.freq(self._freq)
            self._pwm.duty_u16(self._duty_u16)
            DPRINT(f"PWM: Init OK. Freq={self._freq}, Duty={self._duty_u16}")
        except Exception as e:
             DPRINT(f"PWM Init: Error setting initial freq/duty: {e}")
             # Clean up if init fails partially
             try: self._pwm.deinit()
             except: pass
             raise RuntimeError("PWM initial setup failed") from e


    @property
    def freq(self):
        """Gets the current PWM frequency."""
        return self._freq

    @freq.setter
    def freq(self, value):
        """Sets the PWM frequency."""
        try:
            val = int(value)
            if val < 10: val = 10 # Set a reasonable min
            # RP2040 max PWM freq depends on clock, let's cap lower for stability
            if val > 60_000_000: val = 60_000_000 # Cap at 60MHz? Datasheet implies higher possible.
            self._freq = val
            self._pwm.freq(self._freq)
            DPRINT(f"PWM: Set Freq -> {self._freq}")
        except Exception as e:
            DPRINT(f"PWM: Freq set error: {e}")

    @property
    def duty_u16(self):
        """Gets the current duty cycle (0-65535)."""
        return self._duty_u16

    @duty_u16.setter
    def duty_u16(self, value):
        """Sets the duty cycle (0-65535)."""
        try:
            val = int(value)
            if val < 0: val = 0
            if val > 65535: val = 65535
            self._duty_u16 = val
            self._pwm.duty_u16(self._duty_u16)
            # DPRINT(f"PWM: Set Duty(u16) -> {self._duty_u16}") # Reduce noise
        except Exception as e:
            DPRINT(f"PWM: Duty(u16) set error: {e}")

    @property
    def duty_percent(self):
        """Gets the duty cycle as a percentage (0-100)."""
        return (self._duty_u16 / 65535.0) * 100.0

    @duty_percent.setter
    def duty_percent(self, percent):
        """Sets the duty cycle as a percentage (0-100)."""
        try:
            p = float(percent)
            if p < 0: p = 0
            if p > 100: p = 100
            self.duty_u16 = int((p / 100.0) * 65535)
            # DPRINT(f"PWM: Set Duty(%) -> {p}% (raw: {self.duty_u16})") # Reduce noise
        except Exception as e:
            DPRINT(f"PWM: Duty(%) set error: {e}")

    def deinit(self):
        """De-initializes the PWM, releasing the pin."""
        DPRINT(f"PWM: De-initializing for Pin {self._pin_obj}")
        try:
            self._pwm.deinit()
        except Exception as e:
            DPRINT(f"PWM: Error during deinit: {e}")
eof


cat >> pinout.py <<'eof'
#RPi pico W pinout
def pinout():
    print("""
            led_builtin(GP25)
                     ---usb---
        UART0 TX GP0   1  |o     o| 40  VBUS
        UART0 RX GP1   2  |o     o| 39  VSYS
                 GND   3  |o     o| 38  GND
                 GP2   4  |o     o| 37  3V3_EN
                 GP3   5  |o     o| 36  3V3(OUT)
        UART1 TX GP4   6  |o     o| 35           ADC_VREF
        UART1 RX GP5   7  |o     o| 34  GP28     ADC2
                 GND   8  |o     o| 33  GND      AGND
                 GP6   9  |o     o| 32  GP27     ADC1
                 GP7   10 |o     o| 31  GP26     ADC0
        UART1 TX GP8   11 |o     o| 30  RUN
        UART1 RX GP9   12 |o     o| 29  GP22
                 GND   13 |o     o| 28  GND
                 GP10  14 |o     o| 27  GP21
                 GP11  15 |o     o| 26  GP20
        uart0 TX GP12  16 |o     o| 25  GP19
        uart0 RX GP13  17 |o     o| 24  GP18
                 GND   18 |o     o| 23  GND
        uart1 TX GP14  19 |o     o| 22  GP17
        uart1 RX GP15  20 |o     o| 21  GP16
             ---------
    """)
#pinout()
eof


cat >> request_handler.py <<'eof'
# request_handler.py
import config
import uasyncio # Still need for async BLE/WiFi handlers

def DPRINT(s):
    if config.DEBUG: print(s)

class Request_handler:
    """ Parses URLs, queues sync pin actions, calls async BLE/WiFi methods. """
    def __init__(self, board):
        self.board = board
        # Map URL components to handler methods
        self.action_map = {
            # Object: pin (Sync handlers - queue actions)
            "pin": {
                "mode": self.handle_pin_mode,    # Sync
                "value": self.handle_pin_value,  # Sync
                "pull": self.handle_pin_pull     # Sync
            },
            # Object: pwm (Sync handler - queue action)
            "pwm": {
                 "set": self.handle_pwm_set      # Sync
            },
            # Object: ble (Async handlers - await board methods)
            "ble": {
                "start": self.handle_ble_start,  # Async
                "stop": self.handle_ble_stop,    # Async
                "set_name": self.handle_ble_set_name # Async
            },
            # Object: wifi (Async handler - await board method)
            "wifi": {
                "connect": self.handle_wifi_connect # Async
            },
            # Object: console (Sync handler - logs via board)
            "console": {
                 "command": self.handle_console_command # Sync
            }
            # Add control handlers if needed (e.g., load/free templates)
            # "control": { "load_templates": self.handle_load_templates ... }
        }

    async def handle_request(self, path): # Handler itself remains async
        """ Async: Parses path, calls sync or async handler, returns dict. """
        DPRINT(f"Handler: Processing path '{path}'")
        parts = path.strip('/').split('/')

        # Handle different path structures
        # /object/method/arg1... OR /command/the_command
        obj_name, method_name, args = None, None, []
        if len(parts) >= 2:
            if parts[0] == 'console' and parts[1] == 'command': # /console/command/arg
                 obj_name, method_name = 'console', 'command'
                 args = parts[2:] # Command text might have slashes? Join them.
                 args = ["/".join(args)] if args else [] # Treat rest of path as single command arg
            else: # Standard /object/method/arg...
                 obj_name, method_name = parts[0], parts[1]
                 args = parts[2:]
        elif len(parts) == 1 and parts[0] == 'command': # Allow /command?input=... (Handled by GET params)
             # This case shouldn't be reached if using path-based routing only
             # Let query param parsing handle this? Or map /command to console/command?
             # For now, assume path based /console/command/TEXT
              pass # Let it fall through to unknown path

        if not obj_name or not method_name:
             return {"status": "error", "message": "Invalid path format"}


        if obj_name not in self.action_map or method_name not in self.action_map[obj_name]:
            return {"status": "error", "message": f"Unknown object/method '{obj_name}/{method_name}'"}

        handler_method = self.action_map[obj_name][method_name]

        try:
            # Check if handler is async or sync using iscoroutinefunction
            if uasyncio.iscoroutinefunction(handler_method):
                DPRINT(f"Handler: Awaiting async method {handler_method.__name__}...")
                success, message = await handler_method(args) # Use await for async handlers
            else:
                DPRINT(f"Handler: Calling sync method {handler_method.__name__}...")
                success, message = handler_method(args) # Call sync handlers directly
            return {"status": "success" if success else "error", "message": message}
        except Exception as e:
            DPRINT(f"Handler: Exception during handling {path}: {e}")
            import sys; sys.print_exception(e)
            return {"status": "error", "message": f"Internal error: {e}"}

    # --- Pin Action Handlers (Synchronous - Queue Actions) ---

    def handle_pin_mode(self, args):
        """ Sync: Queues pin mode change. Usage: /pin/mode/<id>/<MODE> """
        if len(args) != 2: return False, "Usage: /pin/mode/<id>/<IN|OUT|ADC|PWM>"
        try:
            pin_id = int(args[0]); mode_str = args[1].upper()
            # Queue the action, pull defaults to None if mode is not IN
            return self.board.set_pin_mode(pin_id, mode_str, pull_str=None)
        except (ValueError, TypeError): return False, "Invalid pin ID or mode format"

    def handle_pin_value(self, args):
        """ Sync: Queues pin value change. Usage: /pin/value/<id>/<0|1> """
        if len(args) != 2: return False, "Usage: /pin/value/<id>/<0|1>"
        try:
            pin_id = int(args[0]); value = int(args[1])
            return self.board.set_pin_value(pin_id, value)
        except (ValueError, TypeError): return False, "Invalid pin ID or value format"

    def handle_pin_pull(self, args):
        """ Sync: Queues pin mode change for pull resistors. Usage: /pin/pull/<id>/<NONE|UP|DOWN> """
        if len(args) != 2: return False, "Usage: /pin/pull/<id>/<NONE|UP|DOWN>"
        try:
            pin_id = int(args[0]); pull_str = args[1].upper()
            # Check pin exists and is IN mode synchronously before queueing
            pin = self.board.get_pin_by_id(pin_id) # Sync read is fine
            if not pin: return False, f"Pin {pin_id} not found"
            # Allow setting pull only if currently IN or changing TO IN?
            # Let set_pin_mode handle the logic, just queue the request.
            #if pin.mode != "IN": return False, f"Can only set pull for IN mode"
            # Queue the mode change action with mode='IN' and the pull string
            return self.board.set_pin_mode(pin_id, "IN", pull_str=pull_str)
        except (ValueError, TypeError): return False, "Invalid pin ID or pull format"

    def handle_pwm_set(self, args):
         """ Sync: Queues PWM parameter change. Usage: /pwm/set/<id>/<freq>/<duty_pc> """
         if len(args) != 3: return False, "Usage: /pwm/set/<id>/<freq>/<duty_percent>"
         try:
            pin_id=int(args[0]); freq=args[1]; duty_pc=args[2] # Keep as strings for queueing robustness
            return self.board.set_pwm_params(pin_id, freq=freq, duty_pc=duty_pc)
         except (ValueError, TypeError): return False, "Invalid pin ID, freq, or duty format"

    # --- BLE/WiFi Handlers (Asynchronous - Await Board Methods) ---

    async def handle_ble_start(self, args):
        """ Async: Handles /ble/start """
        success = await self.board.start_ble_advertising()
        return success, "BLE advertising started." if success else "Failed to start BLE."

    async def handle_ble_stop(self, args):
        """ Async: Handles /ble/stop """
        await self.board.stop_ble_advertising()
        return True, "BLE advertising stopped."

    async def handle_ble_set_name(self, args):
        """ Async: Handles /ble/set_name/<name> """
        if len(args) != 1: return False, "Usage: /ble/set_name/<name>"
        new_name = args[0] # Assumes URL decoding happened in handle_client
        success = await self.board.set_ble_name(new_name)
        return success, f"BLE name set." if success else "Failed to set BLE name."

    async def handle_wifi_connect(self, args):
        """ Async: Handles /wifi/connect/<ssid>/<password> """
        # NOTE: Still insecure
        if len(args) != 2: return False, "Usage: /wifi/connect/<ssid>/<password>"
        ssid = args[0]; password = args[1]
        DPRINT(f"Handler: Wi-Fi connect API call for SSID '{ssid}'")
        success = await self.board.connect_wifi(ssid, password)
        # Device resets on success, response might not be seen
        return success, "Wi-Fi connect initiated (device may reset)." if success else "Wi-Fi connect failed."

    # --- Console Command Handler (Synchronous) ---
    def handle_console_command(self, args):
         """ Sync: Handles /console/command/<command_text> """
         if not args: return False, "No command provided."
         command_text = args[0] # Command is the first part after /console/command/
         DPRINT(f"Handler: Received console command '{command_text}'")
         # Use the log_message method added to the board instance
         if hasattr(self.board, 'log_message'):
             self.board.log_message(f"> {command_text}", 'input') # Log the command
             # Basic command parsing and execution logging
             if command_text.lower() == 'temp':
                  temp_c = self.board.get_internal_temp() # Sync read ok
                  self.board.log_message(f"Temp: {temp_c:.2f} C", 'data')
             elif command_text.lower() == 'help':
                   self.board.log_message("Cmds: temp, clear, led_on/off, red/green/blue/rgb_off", 'info')
             elif command_text.lower() == 'clear':
                   # Need controller access to clear its log buffer...
                   # For now, just log the request. Could add a clear method to board?
                   self.board.log_message("Clear log requested (not implemented).", 'info')
             # Add simple LED/RGB commands here too?
             elif command_text.lower() == 'led_on':
                  # Queue action for onboard LED
                  return self.board.set_pin_value(25, 1) # GP25
             elif command_text.lower() == 'led_off':
                  return self.board.set_pin_value(25, 0)
             elif command_text.lower() == 'red':
                   # Queue multiple actions? Or specific command?
                   # Simple: queue individual actions
                   self.board.set_pin_value(13, 1)
                   self.board.set_pin_value(14, 0)
                   self.board.set_pin_value(15, 0)
                   self.board.log_message("RGB Red requested.", 'status')
             # Add green, blue, rgb_off similarly...
             else:
                  self.board.log_message(f"Unknown command: '{command_text}'", 'error')
             return True, f"Command processed." # Return generic success
         else:
             return False, "Board logging method missing."
eof

