#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"

#define UART_ID uart1
#define UART_TX_PIN 8
#define UART_RX_PIN 9

int main() {
    stdio_init_all();
    
    printf("=== DMX512 Connection Test ===\n");
    printf("TX Pin: GP%d\n", UART_TX_PIN);
    printf("RX Pin: GP%d\n", UART_RX_PIN);
    
    // Test different baud rates
    uint32_t baud_rates[] = {9600, 115200, 250000};
    int num_rates = sizeof(baud_rates) / sizeof(baud_rates[0]);
    
    for (int i = 0; i < num_rates; i++) {
        printf("\n--- Testing at %u baud ---\n", baud_rates[i]);
        
        // Initialize UART
        uart_init(UART_ID, baud_rates[i]);
        uart_set_format(UART_ID, 8, 1, UART_PARITY_NONE);  // Try 8N1 first
        
        gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
        gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);
        
        printf("UART initialized. Waiting for data (10 seconds)...\n");
        
        uint32_t start_time = time_us_32();
        int byte_count = 0;
        bool got_data = false;
        
        while ((time_us_32() - start_time) < 10000000) {  // 10 seconds
            if (uart_is_readable(UART_ID)) {
                uint8_t ch = uart_getc(UART_ID);
                printf("Byte %d: 0x%02X (%d)\n", byte_count++, ch, ch);
                got_data = true;
                
                if (byte_count >= 20) break;  // Stop after 20 bytes
            }
            sleep_ms(1);
        }
        
        if (!got_data) {
            printf("No data received at %u baud\n", baud_rates[i]);
        } else {
            printf("SUCCESS: Got %d bytes at %u baud\n", byte_count, baud_rates[i]);
        }
        
        uart_deinit(UART_ID);
        sleep_ms(100);
    }
    
    // Test with 8N2 format at DMX baud rate
    printf("\n--- Testing DMX format (250000 baud, 8N2) ---\n");
    uart_init(UART_ID, 250000);
    uart_set_format(UART_ID, 8, 2, UART_PARITY_NONE);  // DMX format
    
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);
    
    printf("Testing DMX format for 10 seconds...\n");
    
    uint32_t start_time = time_us_32();
    int byte_count = 0;
    
    while ((time_us_32() - start_time) < 10000000) {  // 10 seconds
        if (uart_is_readable(UART_ID)) {
            uint8_t ch = uart_getc(UART_ID);
            printf("DMX Byte %d: 0x%02X (%d)\n", byte_count++, ch, ch);
            
            if (byte_count >= 50) break;  // Stop after 50 bytes
        }
        sleep_ms(1);
    }
    
    if (byte_count == 0) {
        printf("No data received in DMX format\n");
        printf("\nTROUBLESHOOTING:\n");
        printf("1. Check wiring:\n");
        printf("   - DollaTek VCC -> Pico 3.3V\n");
        printf("   - DollaTek GND -> Pico GND\n");
        printf("   - DollaTek TX -> Pico GP9 (RX)\n");
        printf("   - DollaTek RX -> Pico GP8 (TX)\n");
        printf("2. Verify DMX source is transmitting\n");
        printf("3. Check RS485 A/B connections\n");
        printf("4. Try swapping A/B lines\n");
    } else {
        printf("SUCCESS: Received %d bytes in DMX format!\n", byte_count);
    }
    
    while (true) {
        sleep_ms(1000);
    }
    
    return 0;
}