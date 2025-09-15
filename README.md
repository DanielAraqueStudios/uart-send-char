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
- Button (active-low): GPIO4 (internal pull-up enabled)
- UART: UART0 (default pins on many devkits)
  - TX0 = GPIO1 (connected to USB-serial TX on many boards)
  - RX0 = GPIO3 (connected to USB-serial RX on many boards)

Wiring example:
- Button: one side to GPIO4, other side to GND. Use internal pull-up (firmware enables it).
- Connect the devkit to the host PC via USB; UART0 typically routed through the onboard USB-serial chip.

> Important: Do not use GPIO3 for a button if using UART0 via onboard USB. Use GPIO4 as provided.

## Backend behavior (firmware)
- main.c monitors the configured button GPIO with an ISR that timestamps events and queues them.
- A FreeRTOS task debounces the input, validates presses, selects a random letter (A–Z) different from the previous one, and transmits the character plus newline over UART.
- The firmware emits human-readable log lines via `ESP_LOGI`, including `level_at_isr=<0|1>` and `Sent 'X'` so the GUIs can parse and display state.

## Build & Flash (ESP-IDF)
1. Set up ESP-IDF and the toolchain per Espressif instructions.
2. From the project directory:
   - idf.py set-target esp32s3
   - idf.py build
   - idf.py -p /dev/ttyUSB0 flash monitor

Use the correct serial port for your system (e.g. `/dev/ttyUSB0` or `/dev/ttyACM0`). If you get a port busy error, close other applications using the serial port.

## Desktop GUI (PyQt6)
File: `led_control_gui.py`
Requirements:
- Python 3
- PyQt6
- pyserial

Recommended: create and activate a virtual environment in the project folder:

python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6 pyserial
python led_control_gui.py

Features:
- Select serial port and baud rate
- Connect / Disconnect
- Live log view
- Shows last received letter and button logical state (ALTO/BAJO)
- Manual single-letter send
- Dark-mode with Matrix background animation

## Web GUI (Web Serial API)
Files: `interface 2/index.html`, `interface 2/app.js`
Notes:
- Requires a Chromium-based browser with Web Serial support (Chrome, Edge).
- Open `interface 2/index.html` in the browser (use file:// or host via a static server).
- Use the "Select Port" button to pick the serial device and press Connect.
- Web UI displays logs, last received letter and button state, and includes Matrix background animation.

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
