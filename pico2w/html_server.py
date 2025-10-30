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