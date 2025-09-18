# TURN_LED_WITH_UART_GUI

Project: ESP32-S3 button → random-letter UART sender + dual GUIs (PyQt6 desktop and Web Serial).

## University / Course / Team
- Universidad Militar Nueva Granada
- Materia: Micros
- Integrantes: Daniel García Araque, Santiago Rubiano, Karol Daniela Mosquera Prieto

## Summary
Firmware running on an ESP32-S3 monitors an external button and, on each valid press, sends a single uppercase letter (A–Z) over UART. The letter is guaranteed to be different from the last sent value. Two user interfaces display the received letters and the button logical state:
- Desktop GUI: Python + PyQt6 (`led_control_gui.py`) with serial port & baud selection.
- Web GUI: Modern dark Web UI using the Web Serial API (`interface 2/index.html` + `interface 2/app.js`).

## Hardware pinout (default)
- Button (active-high): GPIO6 (internal pull-down enabled)
- UART: UART0 (default pins on many devkits)
  - TX0 = GPIO1 (connected to USB-serial TX on many boards)
  - RX0 = GPIO3 (connected to USB-serial RX on many boards)

Wiring example:
- Button: one side to GPIO6, other side to 3.3V. Use internal pull-down (firmware enables it).
- Connect the devkit to the host PC via USB; UART0 typically routed through the onboard USB-serial chip.

> Important: Button is now active-high (press = 3.3V) with pull-down resistor enabled.

## Backend Firmware (main.c) - Detailed Implementation

### Architecture Overview
The ESP32-S3 firmware uses a multi-layered approach combining hardware interrupts, FreeRTOS tasks, and UART communication to create a responsive button-to-serial letter transmission system.

### Hardware Configuration
```c
#define BUTTON_PIN 6           // GPIO6 for button input
#define UART_PORT UART_NUM_0   // UART0 uses USB-Serial converter
```

**Button Setup:**
- **GPIO6** configured as input with **pull-down resistor** enabled
- **Active-high** logic: button press = 3.3V, release = 0V
- **Rising edge** interrupt trigger (`GPIO_INTR_POSEDGE`)

**UART Configuration:**
- **UART0** with configurable baud rate (1200/128000/460800 bps)
- **Uses built-in USB-Serial converter** - no external pins needed
- **8 data bits, no parity, 1 stop bit**
- **No hardware flow control**
- **1024-byte buffer** for reliable transmission

### Interrupt Service Routine (ISR)
```c
static void IRAM_ATTR button_isr_handler(void* arg) {
    uint32_t gpio_num = (uint32_t) arg;
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, NULL);
}
```
- **IRAM_ATTR**: Stores function in internal RAM for fastest execution
- **Non-blocking**: Only queues the event, actual processing happens in task context
- **Thread-safe**: Uses FreeRTOS queue to communicate with task

### Debounce Algorithm
```c
const TickType_t debounce_ticks = pdMS_TO_TICKS(50); // 50ms debounce
vTaskDelay(debounce_ticks);
int level = gpio_get_level(io_num);
if (level == 1) { // Confirm button still pressed }
```
- **50ms delay** after interrupt to avoid mechanical bounce
- **Level confirmation**: Re-reads GPIO to ensure sustained press
- **False positive prevention**: Ignores glitches and partial presses

### Random Letter Generation
```c
uint32_t random_val = (uint32_t)esp_timer_get_time() ^ xTaskGetTickCount();
char letter = 'A' + (random_val % 26);
```
- **High-resolution timer** (`esp_timer_get_time()`) provides microsecond precision
- **XOR with tick count** adds additional entropy
- **Modulo 26** ensures letters A-Z range
- **No duplicate prevention**: Each press generates truly random letter

### UART Transmission
```c
// Send only the character (no newline, no formatting)
uart_write_bytes(UART_PORT, &letter, 1);
```
- **Raw character output**: Sends only the letter (A-Z) without formatting
- **Single byte transmission**: Minimal data for efficient communication
- **Blocking write**: Ensures complete transmission before continuing
- **Frontend reconstruction**: GUIs receive the raw character and rebuild log messages

### Logging System
```c
ESP_LOGI(TAG, "Button pressed -> Sent '%c'", letter);
```
- **ESP_LOGI**: Info-level logging for debugging (console only)
- **Local logging**: Logs are NOT sent over UART to GUIs
- **TAG identification**: "LED_UART" tag for ESP-IDF monitor filtering
- **GUI independence**: Firmware logs and GUI data are separate

### Task Structure
- **Main task**: Initializes hardware and creates button task, then sleeps
- **Button task**: Infinite loop processing queued button events
- **ISR**: Minimal interrupt handler for immediate response
- **Priority 10**: High priority for responsive button handling

### Error Handling
- **Queue overflow protection**: 10-event queue prevents memory issues
- **GPIO validation**: Confirms button state after debounce
- **UART buffer management**: 2KB buffer handles burst transmissions

### Communication Protocol
**Backend → Frontend:**
- **Raw character transmission**: Backend sends only the letter (A-Z) as a single byte
- **No formatting**: No newlines, no "Sent" prefix, no additional metadata
- **Minimal bandwidth**: Each button press = 1 byte transmitted

**Frontend Processing:**
- **Character detection**: Receives raw character and validates it's A-Z
- **Message reconstruction**: Rebuilds "Sent 'X'" format for log display
- **State inference**: Assumes button HIGH state when letter received
- **UI updates**: Updates last letter display and log with reconstructed message

### Power Considerations
- **Pull-down resistor**: Prevents floating input and reduces power consumption
- **Task delays**: Regular delays allow other tasks to run and save power
- **Efficient ISR**: Minimal processing in interrupt context
- **Minimal UART traffic**: Single character transmission reduces power usage

## Build & Flash (ESP-IDF)
1. Set up ESP-IDF and the toolchain per Espressif instructions.
2. From the project directory:
   - idf.py set-target esp32s3
   - idf.py build
   - idf.py -p /dev/ttyACM0 flash monitor

Use the correct serial port for your system (typically `/dev/ttyACM0` for ESP32-S3). If you get a port busy error, close other applications using the serial port.

## Baud Rate Testing
The project supports multiple baud rates for testing:
- **1200 bps** (current default)
- **128000 bps** 
- **460800 bps**

To change baud rate: modify `.baud_rate = XXXX` in `main.c`, rebuild and flash. Both interfaces support all these speeds in their dropdown menus.

## Interfaces
Both interfaces support the three testing baud rates (1200, 128000, 460800 bps) in their dropdown menus.

### Python GUI (`led_control_gui.py`)
**Requirements:**
- Python 3
- PyQt6
- pyserial

**Setup:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6 pyserial
python led_control_gui.py
```

**Usage:**
1. Select your serial port from the dropdown
2. Select baud rate (1200, 128000, or 460800 bps)
3. Click "Connect" to begin monitoring
4. Press the button on the ESP32-S3 to see letters appear
5. Use "Send Manual Letter" to send random letters from the GUI

**Features:** Serial port selection, 3 baud rate options, live log display, last letter indicator, button state display (ALTO/BAJO), manual letter sending, Matrix background animation.

### Web Interface (`interface 2/index.html`)
**Requirements:**
- Chromium-based browser with Web Serial API support (Chrome, Edge)

**Usage:**
1. Open `interface 2/index.html` in your browser
2. Click "Select Port" and choose your ESP32-S3 device
3. Select baud rate (1200, 128000, or 460800 bps)
4. Click "Connect" to begin monitoring
5. Press the button on ESP32-S3 to see letters appear

**Features:** Serial port selection, 3 baud rate options, live log display, last letter indicator, button state display, Matrix background animation, automatic reconnection on disconnect.

## Log format (for GUI parsing)
The firmware emits lines the GUIs parse. Examples:
- Detected input on GPIO 4 level_at_isr=1 at 12345678 us
- After debounce (200 ms) level=0
- Interrupt on GPIO 4 handled: valid press detected
- Sent 'K' (2 bytes) at 12346789 us (time since ISR 1011 us)

GUIs look for `level_at_isr=` or `level=` and `Sent 'X'` to update UI state.

## Tips and Recommendations
- Button wiring: use a debounced mechanical button or adjust debounce timing (`debounce_ticks`) in firmware.
- Randomness: the firmware uses timestamps for lightweight randomness. For enhanced entropy use `esp_random()` and seed appropriately.
- If you want to remap UART pins or use UART1/2, update `uart_set_pin` and code accordingly and avoid using pins required for flashing.

If you want, I can:
- Add a second desktop GUI in another toolkit/IDE, or
- Harden the firmware (robust PRNG, state machine, edge filtering), or
- Add a testing script that logs incoming characters and timestamps on the PC.

---
