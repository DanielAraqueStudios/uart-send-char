/*
 * ESP32-S3 Input Monitor with UART
 * Sends GPIO6 state via UART when GPIO6 button is pressed
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "esp_log.h"

#define BUTTON_PIN 6
#define UART_PORT UART_NUM_0  // UART0 uses USB-Serial converter
#define UART_BUF_SIZE 1024

static const char *TAG = "LED_UART";
static QueueHandle_t gpio_evt_queue = NULL;

// ISR handler for button
static void IRAM_ATTR button_isr_handler(void* arg) {
    uint32_t gpio_num = (uint32_t) arg;
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, NULL);
}

// Task to handle button events with debounce
void button_task(void *arg) {
    uint32_t io_num;
    const TickType_t debounce_ticks = pdMS_TO_TICKS(50); // 50ms debounce
    
    while (1) {
        if (xQueueReceive(gpio_evt_queue, &io_num, portMAX_DELAY)) {
            // Debounce: wait and check if button is still pressed (low)
            vTaskDelay(debounce_ticks);
            int level = gpio_get_level(io_num);
            
            if (level == 1) { // Button pressed (active high)
                // Generate random letter A-Z
                uint32_t random_val = (uint32_t)esp_timer_get_time() ^ xTaskGetTickCount();
                char letter = 'A' + (random_val % 26);
                char msg[5];
                snprintf(msg, sizeof(msg), "%c\n", letter);
                uart_write_bytes(UART_PORT, msg, strlen(msg));
                ESP_LOGI(TAG, "Button pressed -> Sent '%c'", letter);
            }
        }
    }
}

void app_main(void)
{
    // Configure button with interrupt
    gpio_config_t button_conf = {
        .pin_bit_mask = (1ULL << BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_POSEDGE // Trigger on rising edge
    };
    gpio_config(&button_conf);
    
    // Configure UART
    uart_config_t uart_config = {
        .baud_rate = 460800,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_PORT, &uart_config);
    // No need to set pins for UART0 - it uses USB-Serial converter automatically
    
    // Create queue for GPIO events
    gpio_evt_queue = xQueueCreate(10, sizeof(uint32_t));
    
    // Install GPIO ISR service and add handler
    gpio_install_isr_service(0);
    gpio_isr_handler_add(BUTTON_PIN, button_isr_handler, (void*) BUTTON_PIN);
    
    // Create button task
    xTaskCreate(button_task, "button_task", 4096, NULL, 10, NULL);
    
    ESP_LOGI(TAG, "System ready. Press button on GPIO6 to read GPIO5 state");
    
    // Keep main task alive
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}