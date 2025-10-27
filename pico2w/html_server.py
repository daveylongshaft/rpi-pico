import machine
import utime
# The boot file is assumed to handle the initial Wi-Fi connection
import boot 

# Import the core logic class from the separate file
from html_controler import Html_controler

class Html_server:
    """
    The main execution class. It holds the network credentials 
    and starts the server process using the Html_controler class.
    Class name matches filename, capitalized.
    """
    
    # Store initial credentials here (they will be passed to and stored in the controller)
    INITIAL_SSID = 'ANTEATER2' 
    INITIAL_PASSWORD = 'Juliaz13'

    def start(self):
        """Initializes and runs the web console."""
        
        # Check if the Wi-Fi connection was successfully established in boot.py
        # We assume the global 'wlan' is set up by boot.py
        if 'wlan' not in globals() and 'wlan' not in dir(boot):
            print("FATAL: Wi-Fi connection object 'wlan' not found. Ensure boot.py is correct.")
            return

        try:
            # Instantiate the core server logic, passing initial credentials
            # The Html_controler instance manages all state changes moving forward
            console = Html_controler(self.INITIAL_SSID, self.INITIAL_PASSWORD)
            
            # Start the main server loop
            console.serve()
            
        except RuntimeError as e:
            print(f"Server Startup Failed: {e}")
        except Exception as e:
            print(f"Application Error: {e}")
            
# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # Start the application via the Html_server class
    server_runner = Html_server()
    server_runner.start()
