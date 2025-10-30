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