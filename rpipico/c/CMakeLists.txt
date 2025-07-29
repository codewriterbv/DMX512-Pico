cmake_minimum_required(VERSION 3.13)

# Include the Pico SDK
include(pico_sdk_import.cmake)

project(dmx_receiver)

# Initialize the SDK
pico_sdk_init()

# Add executable
add_executable(dmx_receiver
    dmx_receiver.c
)

# Link libraries
target_link_libraries(dmx_receiver
    pico_stdlib
    hardware_uart
    hardware_gpio
    hardware_irq
)

# Enable USB output, disable UART output
pico_enable_stdio_usb(dmx_receiver 1)
pico_enable_stdio_uart(dmx_receiver 0)

# Create map/bin/hex/uf2 files
pico_add_extra_outputs(dmx_receiver)