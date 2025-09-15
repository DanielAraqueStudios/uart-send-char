/*
 * ESP32-S3 Button -> Random Letter UART Sender
 *
 * On each valid external button press, pick a random uppercase letter A-Z
 * that is different from the last sent letter and send it over UART.
 *
 * Author: Professional Mechatronics Engineer
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"

#define BUTTON_GPIO 4    // External button GPIO (changed to GPIO4)
#define UART_PORT UART_NUM_0
#define UART_TX_PIN UART_PIN_NO_CHANGE   // use default UART0 pins
#define UART_RX_PIN UART_PIN_NO_CHANGE
#define UART_BUF_SIZE 1024

static const char *TAG = "BTN_UART";
static QueueHandle_t gpio_evt_queue = NULL;
static char last_sent_letter = 0;

void uart_init(void) {
    const uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_PORT, &uart_config);
    uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
}

/* ISR: push gpio number to queue */
static void IRAM_ATTR button_isr_handler(void* arg) {
    uint32_t gpio_num = (uint32_t) arg;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

/* Task: process button events, debounce, pick random different letter and send via UART */
void button_task(void *arg) {
    uint32_t io_num;
    const TickType_t debounce_ticks = pdMS_TO_TICKS(200);
    while (1) {
        if (xQueueReceive(gpio_evt_queue, &io_num, portMAX_DELAY)) {
            /* simple debounce: wait and check stable level (assuming active-low button) */
            vTaskDelay(debounce_ticks);
            int level = gpio_get_level(io_num);
            /* If button is active-low and now low, treat as valid press */
            if (level == 0) {
                /* pick a random letter A-Z different from last_sent_letter */
                char letter = 0;
                for (int attempts = 0; attempts < 10; ++attempts) {
                    uint32_t r = (uint32_t)(esp_timer_get_time() ^ (uint32_t)xTaskGetTickCount());
                    letter = 'A' + (r % 26);
                    if (letter != last_sent_letter) break;
                }
                /* fallback if same after attempts, force change */
                if (letter == last_sent_letter) {
                    letter = (last_sent_letter == 'Z') ? 'A' : last_sent_letter + 1;
                }
                last_sent_letter = letter;
                /* send the letter over UART (single byte). Append newline for readability. */
                char outbuf[2] = { letter, '\n' };
                int tx_bytes = uart_write_bytes(UART_PORT, outbuf, sizeof(outbuf));
                ESP_LOGI(TAG, "Button GPIO %d pressed -> sent '%c' (%d bytes)", io_num, letter, tx_bytes);
            }
        }
    }
}

void button_init(void) {
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_NEGEDGE,         // falling edge (active-low button)
        .mode = GPIO_MODE_INPUT,
        .pin_bit_mask = (1ULL << BUTTON_GPIO),
        .pull_up_en = GPIO_PULLUP_ENABLE,       // enable pull-up if button to GND
        .pull_down_en = GPIO_PULLDOWN_DISABLE
    };
    gpio_config(&io_conf);

    /* create a queue to handle gpio event from isr */
    gpio_evt_queue = xQueueCreate(10, sizeof(uint32_t));
    /* install gpio isr service */
    gpio_install_isr_service(0);
    /* hook isr handler for specific gpio pin */
    gpio_isr_handler_add(BUTTON_GPIO, button_isr_handler, (void*) BUTTON_GPIO);
}

void app_main(void)
{
    uart_init();
    button_init();

    xTaskCreate(button_task, "button_task", 4096, NULL, 10, NULL);
}