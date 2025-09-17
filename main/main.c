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
#define UART_PORT UART_NUM_1
#define UART_TX_PIN 17   // UART1 TX -> GPIO17
#define UART_RX_PIN 16   // UART1 RX -> GPIO16
#define UART_BUF_SIZE 1024

static const char *TAG = "BTN_UART";
// change queue to hold event struct with timestamp and level
typedef struct {
    uint32_t gpio_num;
    int level_at_isr;      // 0 = low, 1 = high
    int64_t isr_ts_us;     // timestamp from esp_timer_get_time()
} gpio_event_t;
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

/* ISR: push gpio event (with timestamp and level) to queue */
static void IRAM_ATTR button_isr_handler(void* arg) {
    gpio_event_t evt;
    evt.gpio_num = (uint32_t) arg;
    evt.level_at_isr = gpio_get_level(evt.gpio_num);
    evt.isr_ts_us = esp_timer_get_time();
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR(gpio_evt_queue, &evt, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

/* Task: process button events, debounce, pick random different letter and send via UART */
void button_task(void *arg) {
    gpio_event_t evt;
    const TickType_t debounce_ticks = pdMS_TO_TICKS(200);
    const uint32_t debounce_ms = 200;
    while (1) {
        if (xQueueReceive(gpio_evt_queue, &evt, portMAX_DELAY)) {
            int64_t recv_ts_us = esp_timer_get_time();
            ESP_LOGI(TAG, "Detected input on GPIO %d level_at_isr=%d at %lld us", evt.gpio_num, evt.level_at_isr, (long long)evt.isr_ts_us);
            ESP_LOGI(TAG, "Event queued and received at %lld us (latency %lld us)", (long long)recv_ts_us, (long long)(recv_ts_us - evt.isr_ts_us));

            /* simple debounce: wait and check stable level (assuming active-low button) */
            vTaskDelay(debounce_ticks);
            int level = gpio_get_level(evt.gpio_num);
            ESP_LOGI(TAG, "After debounce (%u ms) level=%d", debounce_ms, level);

            /* If button is active-low and now low, treat as valid press */
            if (level == 0) {
                /* mark interrupt handled */
                ESP_LOGI(TAG, "Interrupt on GPIO %d handled: valid press detected", evt.gpio_num);

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
                int64_t send_ts_us = esp_timer_get_time();
                ESP_LOGI(TAG, "Sent '%c' (%d bytes) at %lld us (time since ISR %lld us)", letter, tx_bytes, (long long)send_ts_us, (long long)(send_ts_us - evt.isr_ts_us));
            } else {
                ESP_LOGI(TAG, "Interrupt on GPIO %d ignored after debounce: not a press", evt.gpio_num);
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
    gpio_evt_queue = xQueueCreate(10, sizeof(gpio_event_t));
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