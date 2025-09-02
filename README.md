# _Sample project_

(See the README.md file in the upper level 'examples' directory for more information about examples.)

This is the simplest buildable example. The example is used by command `idf.py create-project`
that copies the project to user specified path and set it's name. For more information follow the [docs page](https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html#start-a-new-project)



## How to use example
We encourage the users to use the example as a template for the new projects.
A recommended way is to follow the instructions on a [docs page](https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html#start-a-new-project).

## Example folder contents

The project **sample_project** contains one source file in C language [main.c](main/main.c). The file is located in folder [main](main).

ESP-IDF projects are built using CMake. The project build configuration is contained in `CMakeLists.txt`
files that provide set of directives and instructions describing the project's source files and targets
(executable, library, or both). 

Below is short explanation of remaining files in the project folder.

```
├── CMakeLists.txt
├── main
│   ├── CMakeLists.txt
│   └── main.c
└── README.md                  This is the file you are currently reading
```
Additionally, the sample project contains Makefile and component.mk files, used for the legacy Make based build system. 
They are not used or needed when building with CMake and idf.py.

## ESP32-S3 LED Control Pinout

This project uses two GPIO pins and UART for communication with the ESP32-S3:

| Signal         | ESP32-S3 GPIO Pin | Description                                 |
|----------------|-------------------|---------------------------------------------|
| LED1           | GPIO2             | LED 1 Control Pin                           |
| LED2           | GPIO4             | LED 2 Control Pin                           |
| UART TX        | GPIO17            | ESP32 UART TX (connect to USB-to-Serial RX) |
| UART RX        | GPIO16            | ESP32 UART RX (connect to USB-to-Serial TX) |

**Wiring Instructions:**
- Connect the anode (long leg) of each LED to the specified GPIO pin via a current-limiting resistor (220Ω–330Ω recommended).
- Connect the cathode (short leg) of each LED to GND.
- UART TX (GPIO17) connects to the RX pin of your USB-to-Serial adapter.
- UART RX (GPIO16) connects to the TX pin of your USB-to-Serial adapter.

**Example Schematic:**
```
ESP32-S3 GPIO2 ----[220Ω]----|>|---- GND   (LED1)
ESP32-S3 GPIO4 ----[220Ω]----|>|---- GND   (LED2)
```

> **Note:** You can change the GPIO pins in `main.c` by modifying the `LED1_GPIO`, `LED2_GPIO`, `UART_TX_PIN`, and `UART_RX_PIN` definitions to match your hardware setup.
