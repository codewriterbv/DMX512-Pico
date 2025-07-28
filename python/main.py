# Fixed RS485 to TFT Display for Raspberry Pi Pico
# MicroPython implementation

import framebuf
import machine
import utime
from machine import Pin, UART, SPI

# Configuration
RS485_UART_ID = 0  # UART1
RS485_RX_PIN = 1   # GP5 - connect to RXD on module

# TFT ILI9341 Configuration
TFT_SPI_ID = 0
TFT_SCK_PIN = 18   # GP18 - SPI Clock
TFT_MOSI_PIN = 19  # GP19 - SPI MOSI
TFT_CS_PIN = 17    # GP17 - Chip Select
TFT_DC_PIN = 16    # GP16 - Data/Command
TFT_RST_PIN = 20   # GP20 - Reset

BAUD_RATE = 9600   # RS485 baud rate

# DMX Fixture definitions
DMX_FIXTURES = [
    {"name": "PicoSpot 1", "address": 1, "channels": 11, "type": "Moving Head"},
    {"name": "PicoSpot 2", "address": 12, "channels": 11, "type": "Moving Head"},
    {"name": "RGB LED 1", "address": 23, "channels": 5, "type": "Color Changer"},
    {"name": "RGB LED 2", "address": 28, "channels": 5, "type": "Color Changer"},
]

# Improved TFT Driver Class with proper orientation and buffering
class ILI9341:
    def __init__(self, spi, cs, dc, rst):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        # Correct orientation for landscape mode
        self.width = 320
        self.height = 240

        # Initialize pins
        self.cs.init(Pin.OUT, value=1)
        self.dc.init(Pin.OUT, value=0)
        self.rst.init(Pin.OUT, value=1)

        # Create a simple buffer for partial updates
        self.dirty_regions = []

        self._init_display()

    def _init_display(self):
        # Hardware reset
        self.rst.off()
        utime.sleep_ms(20)
        self.rst.on()
        utime.sleep_ms(150)

        # Software reset
        self._write_cmd(0x01)
        utime.sleep_ms(150)

        # Power Control A
        self._write_cmd(0xCB)
        self._write_data([0x39, 0x2C, 0x00, 0x34, 0x02])

        # Power Control B
        self._write_cmd(0xCF)
        self._write_data([0x00, 0xC1, 0x30])

        # Driver Timing Control A
        self._write_cmd(0xE8)
        self._write_data([0x85, 0x00, 0x78])

        # Driver Timing Control B
        self._write_cmd(0xEA)
        self._write_data([0x00, 0x00])

        # Power On Sequence Control
        self._write_cmd(0xED)
        self._write_data([0x64, 0x03, 0x12, 0x81])

        # Pump Ratio Control
        self._write_cmd(0xF7)
        self._write_data([0x20])

        # Power Control 1
        self._write_cmd(0xC0)
        self._write_data([0x23])

        # Power Control 2
        self._write_cmd(0xC1)
        self._write_data([0x10])

        # VCOM Control 1
        self._write_cmd(0xC5)
        self._write_data([0x3E, 0x28])

        # VCOM Control 2
        self._write_cmd(0xC7)
        self._write_data([0x86])

        # Memory Access Control - Landscape orientation
        self._write_cmd(0x36)
        self._write_data([0x28])  # Landscape mode with proper rotation

        # Pixel Format Set
        self._write_cmd(0x3A)
        self._write_data([0x55])  # 16-bit color

        # Frame Rate Control
        self._write_cmd(0xB1)
        self._write_data([0x00, 0x18])

        # Display Function Control
        self._write_cmd(0xB6)
        self._write_data([0x08, 0x82, 0x27])

        # 3Gamma Function Disable
        self._write_cmd(0xF2)
        self._write_data([0x00])

        # Gamma Curve Selected
        self._write_cmd(0x26)
        self._write_data([0x01])

        # Positive Gamma Correction
        self._write_cmd(0xE0)
        self._write_data([0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08,
                          0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03,
                          0x0E, 0x09, 0x00])

        # Negative Gamma Correction
        self._write_cmd(0xE1)
        self._write_data([0x00, 0x0E, 0x14, 0x03, 0x11, 0x07,
                          0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C,
                          0x31, 0x36, 0x0F])

        # Sleep Out
        self._write_cmd(0x11)
        utime.sleep_ms(150)

        # Display On
        self._write_cmd(0x29)
        utime.sleep_ms(50)

    def _write_cmd(self, cmd):
        self.cs.off()
        self.dc.off()
        self.spi.write(bytes([cmd]))
        self.cs.on()

    def _write_data(self, data):
        self.cs.off()
        self.dc.on()
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        elif isinstance(data, list):
            self.spi.write(bytes(data))
        else:
            self.spi.write(data)
        self.cs.on()

    def set_window(self, x, y, w, h):
        # Column Address Set
        self._write_cmd(0x2A)
        self._write_data([x >> 8, x & 0xFF, (x + w - 1) >> 8, (x + w - 1) & 0xFF])

        # Row Address Set
        self._write_cmd(0x2B)
        self._write_data([y >> 8, y & 0xFF, (y + h - 1) >> 8, (y + h - 1) & 0xFF])

        # Memory Write
        self._write_cmd(0x2C)

    def fill_rect(self, x, y, w, h, color):
        if x >= self.width or y >= self.height:
            return

        # Clip to screen bounds
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y

        self.set_window(x, y, w, h)

        # Fill with color
        color_bytes = bytes([(color >> 8) & 0xFF, color & 0xFF])
        self.cs.off()
        self.dc.on()
        for _ in range(w * h):
            self.spi.write(color_bytes)
        self.cs.on()

    def clear(self, color=0x0000):
        self.fill_rect(0, 0, self.width, self.height, color)

    def draw_text(self, text, x, y, color=0xFFFF, bg_color=None, size=1):
        # Simple 8x8 font with background clearing
        char_width = 8 * size
        char_height = 8 * size

        # Clear background first if specified
        if bg_color is not None:
            text_width = len(text) * char_width
            self.fill_rect(x, y, text_width, char_height, bg_color)

        for i, char in enumerate(text):
            char_x = x + i * char_width
            if char_x >= self.width:
                break
            self._draw_char(char, char_x, y, color, size)

    def _draw_char(self, char, x, y, color, size):
        # 8x8 character patterns
        font_8x8 = {
            # Space and punctuation
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            '!': [0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x18, 0x00],
            '"': [0x36, 0x36, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00],
            '#': [0x36, 0x36, 0x7F, 0x36, 0x7F, 0x36, 0x36, 0x00],
            '$': [0x0C, 0x3E, 0x68, 0x3C, 0x16, 0x7C, 0x30, 0x00],
            '%': [0x62, 0x66, 0x0C, 0x18, 0x30, 0x66, 0x46, 0x00],
            '&': [0x38, 0x6C, 0x38, 0x70, 0xDA, 0xCC, 0x76, 0x00],
            "'": [0x18, 0x18, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00],
            '(': [0x0C, 0x18, 0x30, 0x30, 0x30, 0x18, 0x0C, 0x00],
            ')': [0x30, 0x18, 0x0C, 0x0C, 0x0C, 0x18, 0x30, 0x00],
            '*': [0x00, 0x36, 0x1C, 0x7F, 0x1C, 0x36, 0x00, 0x00],
            '+': [0x00, 0x18, 0x18, 0x7E, 0x18, 0x18, 0x00, 0x00],
            ',': [0x00, 0x00, 0x00, 0x00, 0x18, 0x18, 0x30, 0x00],
            '-': [0x00, 0x00, 0x00, 0x7E, 0x00, 0x00, 0x00, 0x00],
            '.': [0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x18, 0x00],
            '/': [0x02, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x40, 0x00],

            # Numbers 0-9
            '0': [0x3C, 0x66, 0x6E, 0x76, 0x66, 0x66, 0x3C, 0x00],
            '1': [0x18, 0x38, 0x18, 0x18, 0x18, 0x18, 0x7E, 0x00],
            '2': [0x3C, 0x66, 0x06, 0x0C, 0x18, 0x30, 0x7E, 0x00],
            '3': [0x3C, 0x66, 0x06, 0x1C, 0x06, 0x66, 0x3C, 0x00],
            '4': [0x0C, 0x1C, 0x2C, 0x4C, 0x7E, 0x0C, 0x0C, 0x00],
            '5': [0x7E, 0x60, 0x7C, 0x06, 0x06, 0x66, 0x3C, 0x00],
            '6': [0x1C, 0x30, 0x60, 0x7C, 0x66, 0x66, 0x3C, 0x00],
            '7': [0x7E, 0x06, 0x0C, 0x18, 0x30, 0x30, 0x30, 0x00],
            '8': [0x3C, 0x66, 0x66, 0x3C, 0x66, 0x66, 0x3C, 0x00],
            '9': [0x3C, 0x66, 0x66, 0x3E, 0x06, 0x0C, 0x38, 0x00],

            # Uppercase letters A-Z
            'A': [0x18, 0x3C, 0x66, 0x66, 0x7E, 0x66, 0x66, 0x00],
            'B': [0x7C, 0x66, 0x66, 0x7C, 0x66, 0x66, 0x7C, 0x00],
            'C': [0x3C, 0x66, 0x60, 0x60, 0x60, 0x66, 0x3C, 0x00],
            'D': [0x7C, 0x66, 0x66, 0x66, 0x66, 0x66, 0x7C, 0x00],
            'E': [0x7E, 0x60, 0x60, 0x7C, 0x60, 0x60, 0x7E, 0x00],
            'F': [0x7E, 0x60, 0x60, 0x7C, 0x60, 0x60, 0x60, 0x00],
            'G': [0x3C, 0x66, 0x60, 0x6E, 0x66, 0x66, 0x3C, 0x00],
            'H': [0x66, 0x66, 0x66, 0x7E, 0x66, 0x66, 0x66, 0x00],
            'I': [0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x7E, 0x00],
            'J': [0x3E, 0x0C, 0x0C, 0x0C, 0x0C, 0x6C, 0x38, 0x00],
            'K': [0x66, 0x6C, 0x78, 0x70, 0x78, 0x6C, 0x66, 0x00],
            'L': [0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x7E, 0x00],
            'M': [0x63, 0x77, 0x7F, 0x6B, 0x63, 0x63, 0x63, 0x00],
            'N': [0x66, 0x76, 0x7E, 0x6E, 0x66, 0x66, 0x66, 0x00],
            'O': [0x3C, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
            'P': [0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60, 0x60, 0x00],
            'Q': [0x3C, 0x66, 0x66, 0x66, 0x66, 0x6E, 0x3C, 0x06],
            'R': [0x7C, 0x66, 0x66, 0x7C, 0x78, 0x6C, 0x66, 0x00],
            'S': [0x3C, 0x66, 0x60, 0x3C, 0x06, 0x66, 0x3C, 0x00],
            'T': [0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00],
            'U': [0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
            'V': [0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x18, 0x00],
            'W': [0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00],
            'X': [0x66, 0x66, 0x3C, 0x18, 0x3C, 0x66, 0x66, 0x00],
            'Y': [0x66, 0x66, 0x66, 0x3C, 0x18, 0x18, 0x18, 0x00],
            'Z': [0x7E, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x7E, 0x00],

            # Lowercase letters a-z
            'a': [0x00, 0x00, 0x3C, 0x06, 0x3E, 0x66, 0x3E, 0x00],
            'b': [0x60, 0x60, 0x7C, 0x66, 0x66, 0x66, 0x7C, 0x00],
            'c': [0x00, 0x00, 0x3C, 0x66, 0x60, 0x66, 0x3C, 0x00],
            'd': [0x06, 0x06, 0x3E, 0x66, 0x66, 0x66, 0x3E, 0x00],
            'e': [0x00, 0x00, 0x3C, 0x66, 0x7E, 0x60, 0x3C, 0x00],
            'f': [0x1C, 0x36, 0x30, 0x7C, 0x30, 0x30, 0x30, 0x00],
            'g': [0x00, 0x00, 0x3E, 0x66, 0x66, 0x3E, 0x06, 0x3C],
            'h': [0x60, 0x60, 0x7C, 0x66, 0x66, 0x66, 0x66, 0x00],
            'i': [0x18, 0x00, 0x38, 0x18, 0x18, 0x18, 0x3C, 0x00],
            'j': [0x0C, 0x00, 0x1C, 0x0C, 0x0C, 0x0C, 0x6C, 0x38],
            'k': [0x60, 0x60, 0x66, 0x6C, 0x78, 0x6C, 0x66, 0x00],
            'l': [0x38, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00],
            'm': [0x00, 0x00, 0x36, 0x7F, 0x6B, 0x6B, 0x6B, 0x00],
            'n': [0x00, 0x00, 0x7C, 0x66, 0x66, 0x66, 0x66, 0x00],
            'o': [0x00, 0x00, 0x3C, 0x66, 0x66, 0x66, 0x3C, 0x00],
            'p': [0x00, 0x00, 0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60],
            'q': [0x00, 0x00, 0x3E, 0x66, 0x66, 0x3E, 0x06, 0x06],
            'r': [0x00, 0x00, 0x6C, 0x76, 0x60, 0x60, 0x60, 0x00],
            's': [0x00, 0x00, 0x3E, 0x60, 0x3C, 0x06, 0x7C, 0x00],
            't': [0x30, 0x30, 0x7C, 0x30, 0x30, 0x36, 0x1C, 0x00],
            'u': [0x00, 0x00, 0x66, 0x66, 0x66, 0x66, 0x3E, 0x00],
            'v': [0x00, 0x00, 0x66, 0x66, 0x66, 0x3C, 0x18, 0x00],
            'w': [0x00, 0x00, 0x63, 0x6B, 0x6B, 0x7F, 0x36, 0x00],
            'x': [0x00, 0x00, 0x66, 0x3C, 0x18, 0x3C, 0x66, 0x00],
            'y': [0x00, 0x00, 0x66, 0x66, 0x66, 0x3E, 0x06, 0x3C],
            'z': [0x00, 0x00, 0x7E, 0x0C, 0x18, 0x30, 0x7E, 0x00],

            # Additional symbols
            ':': [0x00, 0x18, 0x18, 0x00, 0x18, 0x18, 0x00, 0x00],
            ';': [0x00, 0x18, 0x18, 0x00, 0x18, 0x18, 0x30, 0x00],
            '<': [0x0C, 0x18, 0x30, 0x60, 0x30, 0x18, 0x0C, 0x00],
            '=': [0x00, 0x00, 0x7E, 0x00, 0x7E, 0x00, 0x00, 0x00],
            '>': [0x30, 0x18, 0x0C, 0x06, 0x0C, 0x18, 0x30, 0x00],
            '?': [0x3C, 0x66, 0x0C, 0x18, 0x18, 0x00, 0x18, 0x00],
            '@': [0x3C, 0x66, 0x6E, 0x6A, 0x6E, 0x60, 0x3C, 0x00],
            '[': [0x3C, 0x30, 0x30, 0x30, 0x30, 0x30, 0x3C, 0x00],
            '\\': [0x40, 0x60, 0x30, 0x18, 0x0C, 0x06, 0x02, 0x00],
            ']': [0x3C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x3C, 0x00],
            '^': [0x18, 0x3C, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00],
            '_': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7E, 0x00],
            '`': [0x30, 0x18, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00],
            '{': [0x0E, 0x18, 0x18, 0x70, 0x18, 0x18, 0x0E, 0x00],
            '|': [0x18, 0x18, 0x18, 0x00, 0x18, 0x18, 0x18, 0x00],
            '}': [0x70, 0x18, 0x18, 0x0E, 0x18, 0x18, 0x70, 0x00],
            '~': [0x76, 0xDC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        }

        # Get character pattern or use space if not found
        pattern = font_8x8.get(char, font_8x8[' '])

        # Draw character pixel by pixel
        for row in range(8):
            for col in range(8):
                if pattern[row] & (0x80 >> col):
                    # Draw pixel(s) based on size
                    for dy in range(size):
                        for dx in range(size):
                            px = x + col * size + dx
                            py = y + row * size + dy
                            if px < self.width and py < self.height:
                                self.fill_rect(px, py, 1, 1, color)

# Replace the DMXReader class with this improved version
class DMXReader:
    def __init__(self, uart_id=0, rx_pin=1, baudrate=250000):
        """
        Initialize DMX512 receiver for DollaTek TTL to RS485 (auto direction control)

        Args:
            uart_id: UART interface number (0 or 1)
            rx_pin: GPIO pin for UART RX
            baudrate: DMX512 standard is 250,000 baud
        """
        self.uart = machine.UART(uart_id, baudrate=baudrate, bits=8, parity=None, stop=2, rx=rx_pin)

        self.dmx_data = bytearray(513)  # DMX universe (0-512)
        self.last_dmx_data = bytearray(513)  # For change detection
        self.last_packet_time = 0
        self.packet_count = 0
        self.frame_count = 0
        self.error_count = 0

        # Import select for polling
        import select
        self.select = select

    def clear_uart_buffer(self):
        """Clear any existing data in UART buffer"""
        while self.uart.any():
            self.uart.read(1)

    def read_dmx_packet(self):
        """Read DMX packet from RS485 using improved detection"""
        try:
            # Create poll object for timeout handling
            poll = self.select.poll()
            poll.register(self.uart, self.select.POLLIN)

            # Wait up to 100ms for data
            result = poll.poll(100)
            if not result:
                return False

            # Read available data
            if self.uart.any():
                data = self.uart.read()
                if not data:
                    poll.unregister(self.uart)
                    return False

                # Look for DMX start code (0x00) at beginning
                if len(data) > 0 and data[0] == 0x00:
                    # Valid DMX frame should start with 0x00
                    frame_data = data[:513]  # Limit to max DMX frame size

                    # Copy to our DMX data buffer
                    for i, byte_val in enumerate(frame_data):
                        if i < 513:
                            self.dmx_data[i] = byte_val

                    self.frame_count += 1
                    self.last_packet_time = utime.ticks_ms()
                    self.packet_count += 1

                    poll.unregister(self.uart)
                    return True

            poll.unregister(self.uart)
            return False

        except Exception as e:
            self.error_count += 1
            print(f"DMX read error: {e}")
            return False

    def get_fixture_data(self, fixture):
        """Get DMX data for a specific fixture"""
        start_addr = fixture["address"] - 1  # DMX addresses are 1-based
        channels = fixture["channels"]

        if start_addr < 0 or start_addr + channels > len(self.dmx_data):
            return [0] * channels

        return list(self.dmx_data[start_addr:start_addr + channels])

    def get_fixture_changes(self, fixture):
        """Get changed channels for a specific fixture"""
        start_addr = fixture["address"] - 1
        channels = fixture["channels"]

        if start_addr < 0 or start_addr + channels > len(self.dmx_data):
            return []

        changes = []
        for i in range(channels):
            dmx_index = start_addr + i
            if dmx_index < len(self.dmx_data) and dmx_index < len(self.last_dmx_data):
                if self.dmx_data[dmx_index] != self.last_dmx_data[dmx_index]:
                    changes.append({
                        'channel': i + 1,  # 1-based channel within fixture
                        'dmx_address': fixture["address"] + i,
                        'old_value': self.last_dmx_data[dmx_index],
                        'new_value': self.dmx_data[dmx_index]
                    })

        return changes

    def update_last_frame(self):
        """Update the last frame data for change detection"""
        self.last_dmx_data[:len(self.dmx_data)] = self.dmx_data[:len(self.dmx_data)]

    def is_receiving_data(self):
        """Check if we're receiving recent DMX data"""
        return (utime.ticks_ms() - self.last_packet_time) < 2000  # 2 second timeout

    def get_stats(self):
        """Get reception statistics"""
        return {
            'frames': self.frame_count,
            'errors': self.error_count,
            'last_frame_ms_ago': utime.ticks_diff(utime.ticks_ms(), self.last_packet_time) if self.last_packet_time > 0 else -1
        }

# Replace the DMXMonitor class methods with these improved versions
class DMXMonitor:
    def __init__(self):
        # Initialize status LED
        self.status_led = Pin(25, Pin.OUT)

        # Initialize SPI for TFT
        self.spi = SPI(TFT_SPI_ID,
                       baudrate=40000000,  # Higher speed for better performance
                       polarity=0,
                       phase=0,
                       sck=Pin(TFT_SCK_PIN),
                       mosi=Pin(TFT_MOSI_PIN))

        # Initialize TFT
        self.tft = ILI9341(self.spi,
                           cs=Pin(TFT_CS_PIN),
                           dc=Pin(TFT_DC_PIN),
                           rst=Pin(TFT_RST_PIN))

        # Initialize DMX reader with improved baud rate for DMX512
        self.dmx_reader = DMXReader(RS485_UART_ID, RS485_RX_PIN)

        # Track last displayed state to avoid unnecessary redraws
        self.last_tft_state = {"receiving": None, "fixtures": []}

        # Change tracking
        self.fixture_change_timers = [0] * len(DMX_FIXTURES)  # Track when changes occurred

        self.draw_initial_tft()
        utime.sleep(2)

    def draw_initial_tft(self):
        """Draw initial TFT layout once"""
        self.tft.clear(0x0000)  # Black background

        # Header - using full width
        self.tft.draw_text("DMX512 MONITOR", 10, 10, 0xFFFF, 0x0000, 2)

        # Draw fixture layout once
        y_pos = 48
        for i, fixture in enumerate(DMX_FIXTURES):
            # Fixture header
            header_text = f"{fixture['name']} - {fixture['type']}"
            self.tft.draw_text(header_text, 10, y_pos, 0xFFE0, 0x0000, 1)  # Yellow

            # Address info
            addr_text = f"DMX Address: {fixture['address']}-{fixture['address'] + fixture['channels'] - 1}"
            self.tft.draw_text(addr_text, 10, y_pos + 13, 0x07FF, 0x0000, 1)  # Cyan

            # Channel labels
            self.tft.draw_text("Data:", 10, y_pos + 26, 0xF79E, 0x0000, 1)  # Orange

            y_pos += 42

    def update_tft_status_only(self, is_receiving):
        """Update only the status line to avoid full redraw"""
        # Clear status area
        self.tft.fill_rect(10, 30, 300, 15, 0x0000)

        # Get stats for more detailed status
        stats = self.dmx_reader.get_stats()

        if is_receiving:
            status_text = f"RECEIVING - Frames: {stats['frames']}"
            self.tft.draw_text(status_text, 10, 30, 0x07E0, 0x0000, 1)  # Green
        else:
            if stats['frames'] > 0:
                status_text = f"TIMEOUT - Last: {stats['last_frame_ms_ago']}ms ago"
            else:
                status_text = "WAITING FOR DATA"
            self.tft.draw_text(status_text, 10, 30, 0xF800, 0x0000, 1)  # Red

    def update_tft_fixture_data(self, is_receiving):
        """Update fixture data with change highlighting"""
        current_time = utime.ticks_ms()
        y_pos = 48

        for i, fixture in enumerate(DMX_FIXTURES):
            data_y = y_pos + 27

            # Clear channel data area
            self.tft.fill_rect(55, data_y, 230, 15, 0x0000)

            if is_receiving:
                # Get current channel data
                channel_data = self.dmx_reader.get_fixture_data(fixture)

                # Get changes for this fixture
                changes = self.dmx_reader.get_fixture_changes(fixture)

                # If there are changes, update the timer
                if changes:
                    self.fixture_change_timers[i] = current_time
                    #print(f"Changes in {fixture['name']}: {[f'Ch{c[\"channel\"]}:{c[\"old_value\"]}→{c[\"new_value\"]}' for c in changes[:3]]}")

                # Determine text color based on recent changes
                time_since_change = current_time - self.fixture_change_timers[i]
                if time_since_change < 500:  # Highlight for 500ms
                    text_color = 0xF81F  # Magenta for recent changes
                elif time_since_change < 2000:  # Fade to yellow
                    text_color = 0xFFE0  # Yellow
                else:
                    text_color = 0xFFFF  # White for stable data

                # Show channel values (limit to fit screen)
                max_channels = min(8, len(channel_data))
                data_values = " ".join([f"{val:3d}" for val in channel_data[:max_channels]])
                if len(channel_data) > max_channels:
                    data_values += "..."

                self.tft.draw_text(data_values, 55, data_y, text_color, 0x0000, 1)

            else:
                # Show placeholder when not receiving
                placeholder_text = "-- " * min(8, fixture["channels"])
                self.tft.draw_text(placeholder_text.rstrip(), 55, data_y, 0x7BEF, 0x0000, 1)  # Gray

            y_pos += 42

    def run(self):
        """Main application loop with improved DMX handling"""
        print("DMX Monitor starting...")
        print("Listening for DMX512 data at 250k baud...")

        last_tft_update = 0
        last_status_blink = 0
        status_led_state = False

        while True:
            try:
                current_time = utime.ticks_ms()

                # Read DMX data using improved method
                packet_received = self.dmx_reader.read_dmx_packet()
                is_receiving = self.dmx_reader.is_receiving_data()

                # Update TFT when data received or every 2 seconds
                if (packet_received or
                        utime.ticks_diff(current_time, last_tft_update) > 2000 or
                        self.last_tft_state["receiving"] != is_receiving):

                    # Only update status if it changed
                    if self.last_tft_state["receiving"] != is_receiving:
                        self.update_tft_status_only(is_receiving)

                    # Update fixture data
                    self.update_tft_fixture_data(is_receiving)

                    # Update last frame data for change detection
                    self.dmx_reader.update_last_frame()

                    self.last_tft_state["receiving"] = is_receiving
                    last_tft_update = current_time

                # Status LED blinking
                if utime.ticks_diff(current_time, last_status_blink) > (250 if is_receiving else 1000):
                    status_led_state = not status_led_state
                    self.status_led.value(status_led_state)
                    last_status_blink = current_time

                # Small delay to prevent excessive CPU usage
                utime.sleep_ms(25)  # Faster updates for better responsiveness

            except KeyboardInterrupt:
                print("Program interrupted by user")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                # Flash LED rapidly to indicate error
                for _ in range(5):
                    self.status_led.on()
                    utime.sleep_ms(100)
                    self.status_led.off()
                    utime.sleep_ms(100)
                utime.sleep(1)

def main():
    """Main entry point"""
    try:
        monitor = DMXMonitor()
        monitor.run()
    except Exception as e:
        print(f"Failed to start DMX Monitor: {e}")
        # Error indication
        led = Pin(25, Pin.OUT)
        for _ in range(10):
            led.on()
            utime.sleep_ms(200)
            led.off()
            utime.sleep_ms(200)

if __name__ == "__main__":
    main()

