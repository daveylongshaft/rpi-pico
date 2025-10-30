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