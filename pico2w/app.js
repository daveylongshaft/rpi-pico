// app.js - Client-side JavaScript for Pico W Digital Twin

let boardState = null; // Holds the last received state from /api/board_state
let isUpdating = false; // Flag to prevent rapid updates/API calls
const UPDATE_INTERVAL = 2500; // Poll slightly faster (milliseconds)
let pollIntervalId = null; // To store interval ID for stopping/starting polling

// --- Utility Functions ---

// Debounce function to limit rapid calls (e.g., from sliders if added later)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// --- API Helper Function ---
// Makes fetch calls to the Pico, handles basic errors, expects JSON response
async function apiCall(path, method = 'GET', body = null) {
    // Use relative paths, ensure leading slash is added if needed
    const url = path.startsWith('/') ? path : `/${path}`;
    console.log(`API Call: ${method} ${url}`);
    setStatusItem('ip', 'Connecting...', 'warning'); // Indicate network activity

    let options = { method: method };
    if (body) { // For potential future POST requests
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, options);
        // Check if response is JSON, handle non-JSON responses gracefully
        const contentType = response.headers.get("content-type");
        let data;
        if (contentType && contentType.indexOf("application/json") !== -1) {
             data = await response.json(); // Parse JSON if header indicates it
        } else {
             // Handle plain text or other responses if needed, or treat as error
             const textResponse = await response.text();
             console.warn(`API non-JSON response from ${url}: ${textResponse}`);
             // If expecting JSON, treat this as an error
             data = { status: "error", message: `Non-JSON response: ${textResponse.substring(0, 100)}` };
        }

        console.log("API Response:", data);

        // Log message from Pico JSON response if present
        if (data && data.message) {
            logToConsole(`[API] ${path}: ${data.message}`);
        }

        // Check response HTTP status code AND status field in JSON
        if (!response.ok || (data && data.status === 'error')) {
            const errorMsg = data?.message || response.statusText || `HTTP ${response.status}`;
            console.error(`API Error ${response.status}:`, errorMsg);
            logToConsole(`[ERROR] API ${path}: ${errorMsg}`);
            // Safely access boardState properties or use fallback from initial load
            const lastIP = boardState?.status?.ip || document.getElementById('status-ip')?.textContent || 'API ERR';
            setStatusItem('ip', lastIP, 'error');
            return null; // Indicate failure
        }

        // Restore IP display on success
        const currentIP = boardState?.status?.ip || document.getElementById('status-ip')?.textContent || 'OK';
        setStatusItem('ip', currentIP, 'normal');
        return data; // Return successful JSON data

    } catch (error) {
        // Handle network errors (fetch failure)
        console.error(`Fetch Error for ${url}:`, error);
        logToConsole(`[ERROR] Fetch failed for ${path}: ${error}`);
        setStatusItem('ip', 'OFFLINE?', 'error');
        // Stop polling if connection seems lost
        if (pollIntervalId) { clearInterval(pollIntervalId); pollIntervalId = null; }
        return null; // Indicate failure
    }
}

// --- Action Functions ---
// These functions are called by button clicks or select changes in the HTML
// They call the API and then trigger a UI refresh.

function setPinMode(pinId, mode) {
    // Basic confirmation, can be removed for faster interaction
    // if (!confirm(`Set Pin ${pinId} to ${mode} mode?`)) return;
    apiCall(`pin/mode/${pinId}/${mode}`).then(refreshBoardState);
}

function setPinPull(pinId, pull) {
    // if (!confirm(`Set Pin ${pinId} pull resistor to ${pull}?`)) return;
    apiCall(`pin/pull/${pinId}/${pull}`).then(refreshBoardState);
}

function togglePinValue(pinId) {
    // Find current value from the locally stored boardState
    const pin = boardState?.pins?.find(p => p.id === pinId);
    // Only proceed if pin exists in state and is in OUT mode
    if (!pin || pin.mode !== 'OUT') {
        console.warn(`togglePinValue called for non-output pin ${pinId}`);
        return;
    }
    const nextValue = pin.value === 1 ? 0 : 1; // Calculate the opposite value
    apiCall(`pin/value/${pinId}/${nextValue}`).then(refreshBoardState);
}

// Debounced PWM set function (can be used if needed later)
const debouncedSetPwm = debounce((pinId, freq, duty) => {
     apiCall(`pwm/set/${pinId}/${freq}/${duty}`).then(refreshBoardState);
}, 300);

// Set PWM Parameters (called by PWM control form button)
function setPwm(pinId) {
    const freqEl = document.getElementById(`pwm-freq-${pinId}`);
    const dutyEl = document.getElementById(`pwm-duty-${pinId}`);
    if (!freqEl || !dutyEl) { logToConsole(`[ERROR] PWM elements missing for pin ${pinId}`); return; }
    const freq = freqEl.value;
    const duty = dutyEl.value;
    if (freq === '' || duty === '' || isNaN(freq) || isNaN(duty)) {
         logToConsole("[ERROR] Invalid PWM frequency or duty value.");
         return;
    }
    // Call API directly for button click
    apiCall(`pwm/set/${pinId}/${freq}/${duty}`).then(refreshBoardState);
}

// Set Wi-Fi Credentials and Reconnect
function setWifi() {
    const ssidEl = document.getElementById('ssid');
    const passwordEl = document.getElementById('password');
    if (!ssidEl || !passwordEl) return;
    const ssid = ssidEl.value;
    const password = passwordEl.value;
    if (!ssid) { alert("SSID is required."); return; }
    // Password required by current API structure
    if (!password) { alert("Password is required to change/set Wi-Fi."); return; }

    if (!confirm(`Reconnect to Wi-Fi network "${ssid}"? The device will likely reset or lose connection.`)) return;
    // Call API - Pico resets, don't expect response
    apiCall(`wifi/connect/${encodeURIComponent(ssid)}/${encodeURIComponent(password)}`);
    logToConsole(`[SYSTEM] Wi-Fi reconnect initiated for ${ssid}. Connection may be lost.`);
    setStatusItem('ip', 'Reconnecting...', 'warning');
    // Stop polling
    if (pollIntervalId) { clearInterval(pollIntervalId); pollIntervalId = null; }
}

// Set BLE Advertising Name
function setBleName() {
    const nameEl = document.getElementById('ble_name');
    if (!nameEl) return;
    const name = nameEl.value;
    if (!name) { alert("BLE name cannot be empty."); return; }
    apiCall(`ble/set_name/${encodeURIComponent(name)}`).then(refreshBoardState);
}

// Start or Stop BLE Advertising
function controlBle(action) { // action should be 'start' or 'stop'
    apiCall(`ble/${action}`).then(refreshBoardState);
}

// Send Command to Server-side Console Log
function sendConsoleCommand() {
    const input = document.getElementById('user_input');
    if (!input) return;
    const command = input.value.trim();
    if (!command) return;
    // Use the correct API path /console/command/
    apiCall(`console/command/${encodeURIComponent(command)}`).then(data => {
        // Response message logged by apiCall, refresh state to see server log update
        if (data) refreshBoardState();
    });
    input.value = ''; // Clear input field
}

// --- UI Update Functions ---
// These functions take the data received from /api/board_state
// and update the HTML elements on the page.

// Update the server log display area
function updateConsoleLog(logLines) {
    const consoleEl = document.getElementById('console-log'); // Correct ID
    if (consoleEl && Array.isArray(logLines)) {
        // Join lines, ensure it doesn't grow indefinitely if server doesn't limit
        const limitedLines = logLines.slice(-20); // Show last 20 lines from state
        consoleEl.textContent = limitedLines.join('\n').trim();
        consoleEl.scrollTop = consoleEl.scrollHeight; // Scroll to bottom
    }
}

// Update a generic status item span by ID
function setStatusItem(id, value, type = 'normal') {
     const el = document.getElementById(`status-${id}`);
     if (el) {
         el.textContent = value;
         el.className = `status-value status-${type}`; // Apply status styling
     } else {
         // console.warn(`Status element not found: status-${id}`); // Reduce noise
     }
}

// Update a single pin's visual representation in the pinout diagram
function updatePinElement(pinData) {
    // Find the container div using the data attribute
    const shell = document.querySelector(`[data-pin-id="${pinData.id}"]`);
    if (!shell) { /* console.warn(`Pin shell not found for ID: ${pinData.id}`);*/ return; }

    // --- Update CSS Classes for visual state ---
    let classes = "pin-element ";
    // Determine pin type (more robustly)
    const isGpio = typeof pinData.id === 'number' && pinData.id >= 0;
    const isPower = ['GND', 'VBUS', '3V3', 'VSYS'].some(pwr => pinData.name.includes(pwr));
    const isSpecial = ['EN', 'VREF', 'RUN'].some(sp => pinData.name.includes(sp));

    if (!isGpio && !isPower && !isSpecial) classes += "pin-fixed "; // Default fixed if not identifiable
    if (isPower) classes += "pin-power ";
    else if (isSpecial) classes += "pin-special ";
    // Add classes based on mode and value for GPIO pins
    else if (pinData.mode === "OUT") {
        classes += "pin-out ";
        classes += (pinData.value === 1) ? "pin-out-high " : "pin-out-low ";
    } else if (pinData.mode === "IN") {
        classes += "pin-in ";
        classes += (pinData.value === 1) ? "pin-in-high " : "pin-in-low ";
    } else if (pinData.mode === "ADC") {
        classes += "pin-adc ";
    } else if (pinData.mode === "PWM") {
        classes += "pin-pwm ";
    }
    shell.className = classes.trim(); // Apply updated classes to the container

    // --- Update Value Display Span ---
    const valueEl = shell.querySelector(`.pin-status`); // Find span inside shell
    if (valueEl) {
        let displayVal = 'N/A';
        if (pinData.mode === 'IN' || pinData.mode === 'OUT') {
            displayVal = pinData.value;
        } else if (pinData.mode === 'ADC') {
            displayVal = 'ADC';
        } else if (pinData.mode === 'PWM') {
            displayVal = 'PWM';
        } else if (isPower || isSpecial) {
            // Show short name like GND, RUN for fixed function pins
            displayVal = pinData.name.split(' ')[0];
        }
        valueEl.textContent = displayVal;
        // Optionally update class on value span too for more specific styling
        // valueEl.className = `pin-status pin-${String(displayVal).toLowerCase()}-val`;
    }

    // --- Update Controls (Selects, Button) ---
    // Find controls within the specific pin's shell element
    const modeSelect = shell.querySelector(`select[id$="-mode"]`);
    const pullSelect = shell.querySelector(`select[id$="-pull"]`);
    const toggleButton = shell.querySelector(`button[id$="-toggle"]`);

    // Update Mode Select dropdown
    if (modeSelect) {
        // Avoid changing select if user is currently interacting with it
        if (document.activeElement !== modeSelect) {
            modeSelect.value = pinData.mode;
        }
    }
    // Update Pull Resistor Select dropdown (visibility and value)
    if (pullSelect) {
        pullSelect.style.display = (pinData.mode === 'IN') ? 'inline-block' : 'none';
        if (pinData.mode === 'IN' && document.activeElement !== pullSelect) {
             // Ensure pull value from state matches one of the option values ('NONE', 'UP', 'DOWN')
             pullSelect.value = pinData.pull || 'NONE'; // Default to NONE if null/undefined
        }
    }
    // Update Output Toggle Button (visibility and text)
    if (toggleButton) {
        toggleButton.style.display = (pinData.mode === 'OUT') ? 'inline-block' : 'none';
        if (pinData.mode === 'OUT') {
            toggleButton.textContent = (pinData.value === 1) ? 'Set LOW' : 'Set HIGH';
        }
    }
}

// Update the entire PWM controls section dynamically based on state
function updatePwmControls(pins) {
    const container = document.getElementById('pwm-controls-container');
    const placeholder = document.getElementById('pwm-placeholder');
    if (!container) return; // Exit if container not found

    // Clear previous forms before adding new ones
    container.querySelectorAll('.pwm-form-container').forEach(div => div.remove());

    // Filter for pins currently in PWM mode based on received state
    const pwmPins = pins.filter(p => p.mode === 'PWM' && typeof p.id === 'number' && p.id >= 0);

    if (pwmPins.length === 0) {
        if(placeholder) placeholder.style.display = 'block'; // Show placeholder if no PWM pins
        return;
    }
    if(placeholder) placeholder.style.display = 'none'; // Hide placeholder if there are PWM pins

    // Create a form div for each PWM pin
    pwmPins.forEach(pin => {
        const formDiv = document.createElement('div');
        formDiv.className = 'pwm-form pwm-form-container'; // Use container class for removal

        // Get current values from state, provide defaults if missing
        const currentFreq = pin.pwm_freq !== undefined ? pin.pwm_freq : 1000;
        const currentDuty = pin.pwm_duty !== undefined ? pin.pwm_duty.toFixed(1) : 0.0;

        // Populate inner HTML with inputs and button
        // Use type="button" and onclick to call JS function
        formDiv.innerHTML = `
            <label class="pwm-label"><b>${pin.name}:</b></label>
            <label for="pwm-freq-${pin.id}" class="pwm-label-small">Freq (Hz):</label>
            <input type="number" id="pwm-freq-${pin.id}" value="${currentFreq}" min="10" max="1000000" class="pwm-input">
            <label for="pwm-duty-${pin.id}" class="pwm-label-small">Duty (%):</label>
            <input type="number" id="pwm-duty-${pin.id}" value="${currentDuty}" min="0" max="100" step="0.1" class="pwm-input">
            <button type="button" class="pwm-submit" onclick="setPwm(${pin.id})">Set PWM</button>
        `;
        container.appendChild(formDiv);
    });
}

// --- Main Update Function ---
// Fetches state from API and updates all relevant UI elements
async function refreshBoardState() {
    if (isUpdating) return; // Prevent overlapping updates
    isUpdating = true;
    // console.log("Refreshing board state..."); // Reduce noise in console
    const newState = await apiCall('/api/board_state'); // Ensure leading slash is present
    isUpdating = false;

    // Check if the API call failed or returned invalid data
    if (!newState || !newState.status) {
        console.error("Failed to fetch or parse valid board state.");
        // Optionally update UI to show error state more clearly
        setStatusItem('ip', 'State Fetch Failed', 'error');
        // Maybe try again after a delay? Or stop polling?
        // if (pollIntervalId) { clearInterval(pollIntervalId); pollIntervalId = null; } // Option: Stop polling on error
        return;
    }

    boardState = newState; // Store the latest valid state globally

    // --- Update UI Sections ---

    // Update Status Items
    setStatusItem('time', boardState.status.time);
    setStatusItem('temp', boardState.status.temp_c + ' °C');
    setStatusItem('ip', boardState.status.ip);
    setStatusItem('ble-status', boardState.status.ble_status);
    setStatusItem('ble-name', boardState.status.ble_name);

    // Update input fields only if they are not currently focused by the user
    const ssidInput = document.getElementById('ssid');
    if (ssidInput && document.activeElement !== ssidInput) {
        ssidInput.value = boardState.status.wifi_ssid;
    }
    const bleNameInput = document.getElementById('ble_name');
    if (bleNameInput && document.activeElement !== bleNameInput) {
         bleNameInput.value = boardState.status.ble_name;
    }

    // Update ADC section
    setStatusItem('adc0', boardState.adc_volts.adc0 + ' V');
    setStatusItem('adc1', boardState.adc_volts.adc1 + ' V');
    setStatusItem('adc2', boardState.adc_volts.adc2 + ' V');

    // Update All Pin elements in the pinout diagram
    if (boardState.pins && Array.isArray(boardState.pins)) {
        boardState.pins.forEach(updatePinElement);
        // Explicitly update the separate onboard LED element
        const onboardLedState = boardState.pins.find(p => p.id === 25);
        if (onboardLedState) {
            updatePinElement(onboardLedState);
        } else {
             // Handle case where onboard LED state might be missing
             console.warn("Onboard LED (GP25) state not found in boardState.pins");
        }


        // Update the PWM controls section based on current pin modes
        updatePwmControls(boardState.pins);
    } else {
         console.warn("Board state missing 'pins' array or is not an array.");
    }

    // Update server log display using state data
    if (boardState.server_log && Array.isArray(boardState.server_log)) {
         updateConsoleLog(boardState.server_log);
    }

    // console.log("State refresh complete."); // Reduce noise
}

// --- Initialization ---
// Runs once the initial HTML page's DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Starting JS app.");
    refreshBoardState(); // Fetch the initial state immediately
    // Start the periodic polling only if not already started
    if (!pollIntervalId) {
        pollIntervalId = setInterval(refreshBoardState, UPDATE_INTERVAL);
    }


    // Add event listeners to forms to prevent default submission and call JS functions
    document.getElementById('wifi-form')?.addEventListener('submit', (e) => { e.preventDefault(); setWifi(); });
    document.getElementById('ble-name-form')?.addEventListener('submit', (e) => { e.preventDefault(); setBleName(); });
    document.getElementById('console-form')?.addEventListener('submit', (e) => { e.preventDefault(); sendConsoleCommand(); });
    // Buttons for BLE actions are handled by onclick attributes directly
});

</script>
