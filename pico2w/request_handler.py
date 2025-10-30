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