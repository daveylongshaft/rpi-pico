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

