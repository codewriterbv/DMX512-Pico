#include <SoftwareSerial.h>

// Pin definitions for 4-pin RS485 module
#define RS485_RX 2    // Connect to TX of RS485 module
#define RS485_TX 3    // Connect to RX of RS485 module

// DMX parameters
#define DMX_CHANNELS 512
#define DMX_START_CODE 0x00

// Create SoftwareSerial for RS485 communication
SoftwareSerial rs485(RS485_RX, RS485_TX);

// DMX data storage
uint8_t dmxData[DMX_CHANNELS + 1]; // +1 for start code at index 0
bool dmxFrameReceived = false;
unsigned long lastFrameTime = 0;
int dmxState = 0; // 0=waiting for break, 1=receiving data
int channelCount = 0;
unsigned long breakStartTime = 0;
bool inBreak = false;

void setup() {
  // Initialize serial communications
  Serial.begin(115200);
  rs485.begin(250000); // DMX baud rate is 250kbps
  
  Serial.println("DMX512 Receiver Ready");
  Serial.println("Waiting for DMX data...");
  
  // Initialize DMX data array
  for(int i = 0; i <= DMX_CHANNELS; i++) {
    dmxData[i] = 0;
  }
}

void loop() {
  receiveDMX();
  
  // Print received data every second
  if(dmxFrameReceived && (millis() - lastFrameTime > 1000)) {
    printDMXData();
    lastFrameTime = millis();
  }
  
  // Check for timeout (no DMX signal)
  if(millis() - lastFrameTime > 5000) {
    if(dmxFrameReceived) {
      Serial.println("DMX signal lost!");
      dmxFrameReceived = false;
    }
  }
}

void receiveDMX() {
  static unsigned long lastByteTime = 0;
  
  if(rs485.available()) {
    unsigned long currentTime = micros();
    
    // Check for break condition (gap between bytes > 88μs)
    if(currentTime - lastByteTime > 88) {
      // Break detected, start new frame
      dmxState = 1;
      channelCount = 0;
      inBreak = false;
    }
    
    uint8_t receivedByte = rs485.read();
    lastByteTime = currentTime;
    
    if(dmxState == 1) { // Receiving DMX data
      if(channelCount == 0) {
        // First byte should be start code (0x00 for DMX512)
        if(receivedByte == DMX_START_CODE) {
          dmxData[0] = receivedByte;
          channelCount++;
        } else {
          // Invalid start code, reset
          dmxState = 0;
          return;
        }
      } else if(channelCount <= DMX_CHANNELS) {
        // Store channel data
        dmxData[channelCount] = receivedByte;
        channelCount++;
        
        // Check if we've received a complete frame
        if(channelCount > DMX_CHANNELS) {
          dmxFrameReceived = true;
          lastFrameTime = millis();
          dmxState = 0;
        }
      }
    }
  }
}

void printDMXData() {
  Serial.println("=== DMX Frame Received ===");
  Serial.print("Start Code: ");
  Serial.println(dmxData[0], HEX);
  
  // Print first 16 channels as example
  Serial.println("First 16 channels:");
  for(int i = 1; i <= 16 && i <= DMX_CHANNELS; i++) {
    Serial.print("Ch");
    Serial.print(i);
    Serial.print(": ");
    Serial.print(dmxData[i]);
    Serial.print(" ");
    if(i % 8 == 0) Serial.println();
  }
  Serial.println();
  
  // Print any non-zero channels beyond the first 16
  Serial.println("Non-zero channels:");
  for(int i = 17; i <= DMX_CHANNELS; i++) {
    if(dmxData[i] > 0) {
      Serial.print("Ch");
      Serial.print(i);
      Serial.print(": ");
      Serial.print(dmxData[i]);
      Serial.print(" ");
    }
  }
  Serial.println();
  Serial.println("========================");
}

// Function to get specific channel value
uint8_t getDMXChannel(int channel) {
  if(channel >= 1 && channel <= DMX_CHANNELS && dmxFrameReceived) {
    return dmxData[channel];
  }
  return 0;
}

// Function to check if DMX signal is present
bool isDMXConnected() {
  return dmxFrameReceived && (millis() - lastFrameTime < 2000);
}

// Example function to control LED brightness based on DMX channel 1
void controlLED() {
  if(isDMXConnected()) {
    int brightness = getDMXChannel(1); // Get channel 1 value (0-255)
    analogWrite(9, brightness); // Output to PWM pin 9
  } else {
    analogWrite(9, 0); // Turn off LED if no DMX
  }
}