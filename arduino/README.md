# Arduino Test

## Wiring Setup

### Arduino to TTL-RS485 Converter

    VCC → 5V
    GND → GND
    RX → Digital pin 3 (Arduino TX)
    TX → Digital pin 2 (Arduino RX)

### DMX Connection

    A+ → DMX+ (Data+)
    B- → DMX- (Data-)
    Add 120Ω termination resistor between A+ and B- at the end of DMX chain

## Code Implementation

Key Points:

* Baud Rate: DMX512 uses 250,000 baud, which is critical for proper communication.
* Break Detection: DMX frames start with a "break" - a gap of at least 88 microseconds between bytes. The code detects this timing gap to identify new frames.
* Start Code: Each DMX frame begins with a start code (0x00 for standard DMX512).
* Channel Access: Use getDMXChannel(n) to get the value of channel n (1-512).
* Connection Check: Use isDMXConnected() to verify if DMX signal is present.

## Troubleshooting Tips:

* No Data Received: Check wiring polarity (A+ and B- connections)
* Garbled Data: Verify baud rate is exactly 250000
* Intermittent Reception: Add 120Ω termination resistor
* Timing Issues: Consider using hardware serial instead of SoftwareSerial for better timing accuracy

The code includes examples for accessing specific channels and controlling outputs based on DMX values.