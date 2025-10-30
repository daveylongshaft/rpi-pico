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