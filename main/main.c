
/*
 * ESP32-S3 UART LED Control Backend
 *
 * Controls two LEDs via UART commands.
 * Commands: "LED1 ON", "LED1 OFF", "LED2 ON", "LED2 OFF"
 *
 * Author: Professional Mechatronics Engineer
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"

#define LED1_GPIO 2      // Change as per your hardware
#define LED2_GPIO 4      // Change as per your hardware
#define UART_PORT UART_NUM_1
#define UART_TX_PIN 17   // Change as per your hardware
#define UART_RX_PIN 16   // Change as per your hardware
#define UART_BUF_SIZE 1024

static const char *TAG = "UART_LED";

void led_init(void) {
	gpio_config_t io_conf = {
		.pin_bit_mask = (1ULL << LED1_GPIO) | (1ULL << LED2_GPIO),
		.mode = GPIO_MODE_OUTPUT,
		.pull_up_en = GPIO_PULLUP_DISABLE,
		.pull_down_en = GPIO_PULLDOWN_DISABLE,
		.intr_type = GPIO_INTR_DISABLE
	};
	gpio_config(&io_conf);
	gpio_set_level(LED1_GPIO, 0);
	gpio_set_level(LED2_GPIO, 0);
}

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

void handle_uart_command(const char *cmd) {
	if (strncmp(cmd, "LED1 ON", 7) == 0) {
		gpio_set_level(LED1_GPIO, 1);
		ESP_LOGI(TAG, "LED1 turned ON");
	} else if (strncmp(cmd, "LED1 OFF", 8) == 0) {
		gpio_set_level(LED1_GPIO, 0);
		ESP_LOGI(TAG, "LED1 turned OFF");
	} else if (strncmp(cmd, "LED2 ON", 7) == 0) {
		gpio_set_level(LED2_GPIO, 1);
		ESP_LOGI(TAG, "LED2 turned ON");
	} else if (strncmp(cmd, "LED2 OFF", 8) == 0) {
		gpio_set_level(LED2_GPIO, 0);
		ESP_LOGI(TAG, "LED2 turned OFF");
	} else {
		ESP_LOGW(TAG, "Unknown command: %s", cmd);
	}
}

void uart_task(void *arg) {
	uint8_t *data = (uint8_t *)malloc(UART_BUF_SIZE);
	while (1) {
		int len = uart_read_bytes(UART_PORT, data, UART_BUF_SIZE - 1, 100 / portTICK_PERIOD_MS);
		if (len > 0) {
			data[len] = '\0';
			ESP_LOGI(TAG, "Received: %s", (char *)data);
			handle_uart_command((char *)data);
		}
		vTaskDelay(10 / portTICK_PERIOD_MS);
	}
	free(data);
}

void app_main(void)
{
	led_init();
	uart_init();
	xTaskCreate(uart_task, "uart_task", 4096, NULL, 10, NULL);
}