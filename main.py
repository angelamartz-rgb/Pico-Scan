import network
import bluetooth
import time
import machine
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY

# Initialize Display
# Using 270 for landscape; 145 is not hardware-supported.
display = PicoGraphics(display=DISPLAY_PICO_DISPLAY, rotate=180)
display.set_font("bitmap8")

# Define Colors
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
CYAN = display.create_pen(0, 255, 255)

# Button Pins
btn_a = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP) # WiFi
btn_b = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP) # BT
btn_x = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP) # Up
btn_y = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP) # Down

results = []
scroll_idx = 0
mode_label = "IDLE"
MAX_WIDTH = 230  # Leave a small margin

def wrapped_text(text, x, y, wrap_width):
    """Simple word wrap logic for PicoGraphics"""
    words = text.split(' ')
    line = ""
    for word in words:
        test_line = line + word + " "
        if display.measure_text(test_line, 2) < wrap_width:
            line = test_line
        else:
            display.text(line, x, y, wrap_width, 2)
            y += 15
            line = word + " "
    display.text(line, x, y, wrap_width, 2)
    return y + 20 # Return new Y position for next item

def log_results(mode, data_list):
    with open("scans.txt", "a") as f:
        f.write(f"\n--- {mode} SCAN: {time.ticks_ms()} ---\n")
        for item in data_list:
            f.write(f"{item}\n")

def refresh_ui():
    display.set_pen(BLACK)
    display.clear()
    
    # Header
    display.set_pen(CYAN)
    display.text(f"MODE: {mode_label}", 5, 5, MAX_WIDTH, 2)
    display.set_pen(WHITE)
    display.line(0, 25, 240, 25)
    
    # List Items with Wrap
    current_y = 35
    # Show items starting from scroll_idx
    for i in range(scroll_idx, len(results)):
        if current_y > 115: # Stop if we run out of screen space
            break
        current_y = wrapped_text(results[i], 10, current_y, MAX_WIDTH)
    
    display.update()

def scan_wifi():
    global results, mode_label, scroll_idx
    mode_label = "SCAN WIFI..."
    refresh_ui()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # Extract only SSID (index 0), skip RSSI (index 3)
    found = [net[0].decode('utf-8') for net in wlan.scan() if net[0]]
    results = sorted(list(set(found))) # Unique and sorted
    log_results("WIFI", results)
    scroll_idx = 0
    mode_label = "WIFI DONE"
    refresh_ui()

def scan_ble():
    global results, mode_label, scroll_idx
    mode_label = "SCAN BLE..."
    refresh_ui()
    ble = bluetooth.BLE()
    ble.active(True)
    found_names = []

    def ble_irq(event, data):
        if event == 5: # _IRQ_SCAN_RESULT
            addr_type, addr, adv_type, rssi, adv_data = data
            name = "Unknown"
            # Try to find Name (0x09) in payload
            i = 0
            while i < len(adv_data):
                l = adv_data[i]
                if adv_data[i+1] in (0x08, 0x09): # Short/Full Name
                    name = bytes(adv_data[i+2:i+1+l]).decode('utf-8', 'ignore')
                i += l + 1
            if name not in found_names: found_names.append(name)

    ble.irq(ble_irq)
    ble.gap_scan(2000, 30000, 30000)
    time.sleep(2.2)
    ble.gap_scan(None)
    results = sorted(found_names)
    log_results("BLE", results)
    scroll_idx = 0
    mode_label = "BLE DONE"
    refresh_ui()

# Initial State
refresh_ui()

while True:
    if not btn_a.value(): # WiFi Scan
        scan_wifi()
        time.sleep(0.4)
    if not btn_b.value(): # BLE Scan
        scan_ble()
        time.sleep(0.4)
    if not btn_x.value(): # Scroll Up
        if scroll_idx > 0:
            scroll_idx -= 1
            refresh_ui()
        time.sleep(0.15)
    if not btn_y.value(): # Scroll Down
        if scroll_idx < len(results) - 1:
            scroll_idx += 1
            refresh_ui()
        time.sleep(0.15)
    time.sleep(0.01)