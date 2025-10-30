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
    async def background_update_task(self, interval_ms=59000):
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