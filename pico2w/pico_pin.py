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