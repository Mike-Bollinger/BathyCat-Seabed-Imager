# BathyCat Hardware Wiring Guide

## Overview
This guide provides complete GPIO wiring instructions for the BathyCat Seabed Imager system, including LED status indicators and direct GPIO GPS connection with PPS support.

## GPIO Pin Assignments

### LED Status System
- **GPIO 18** (Pin 12) → Green LED (Power/Status)
- **GPIO 23** (Pin 16) → Blue LED (GPS Status)
- **GPIO 24** (Pin 18) → Yellow LED (Camera Status)
- **GPIO 25** (Pin 22) → Red LED (Error Status)

### GPS Direct Connection (Adafruit Ultimate GPS)
- **5V Power** (Pin 2 or 4) → GPS VCC ⭐ 5V power as requested
- **Ground** (Pin 6, 14, 20, 30, 34, or 39) → GPS GND
- **GPIO 14** (Pin 8) → GPS RX (UART TX from Pi to GPS)
- **GPIO 15** (Pin 10) → GPS TX (UART RX from GPS to Pi)
- **GPIO 16** (Pin 36) → GPS RI/PPS ⭐ Even-numbered pin for precision timing

## Complete Wiring Diagram

```
Raspberry Pi GPIO Header                    External Components
┌────────────────────────────┐             ┌─────────────────────────┐
│ Pin 1  (3.3V)              │             │                         │
│ Pin 2  (5V)   ●────────────┼─────────────┤ GPS VCC (Red wire)      │
│ Pin 3  (GPIO 2)            │             │                         │
│ Pin 4  (5V)                │             │                         │
│ Pin 5  (GPIO 3)            │             │                         │
│ Pin 6  (GND)  ●────────────┼─────────────┤ GPS GND (Black wire)    │
│ Pin 7  (GPIO 4)            │             │                         │
│ Pin 8  (GPIO 14) ●─────────┼─────────────┤ GPS RX (White wire)     │
│ Pin 9  (GND)               │             │                         │
│ Pin 10 (GPIO 15) ●─────────┼─────────────┤ GPS TX (Green wire)     │
│ Pin 11 (GPIO 17)           │             │                         │
│ Pin 12 (GPIO 18) ●─────────┼─────── LED ─┤ Green LED (Power)       │
│ Pin 13 (GPIO 27)           │             │                         │
│ Pin 14 (GND)               │             │                         │
│ Pin 15 (GPIO 22)           │             │                         │
│ Pin 16 (GPIO 23) ●─────────┼─────── LED ─┤ Blue LED (GPS)          │
│ Pin 17 (3.3V)              │             │                         │
│ Pin 18 (GPIO 24) ●─────────┼─────── LED ─┤ Yellow LED (Camera)     │
│ Pin 19 (GPIO 10)           │             │                         │
│ Pin 20 (GND)               │             │                         │
│ Pin 21 (GPIO 9)            │             │                         │
│ Pin 22 (GPIO 25) ●─────────┼─────── LED ─┤ Red LED (Error)         │
│ Pin 23 (GPIO 11)           │             │                         │
│ Pin 24 (GPIO 8)            │             │                         │
│ Pin 25 (GND)               │             │                         │
│ Pin 26 (GPIO 7)            │             │                         │
│ Pin 27 (GPIO 0)            │             │                         │
│ Pin 28 (GPIO 1)            │             │                         │
│ Pin 29 (GPIO 5)            │             │                         │
│ Pin 30 (GND)               │             │                         │
│ Pin 31 (GPIO 6)            │             │                         │
│ Pin 32 (GPIO 12)           │             │                         │
│ Pin 33 (GPIO 13)           │             │                         │
│ Pin 34 (GND)               │             │                         │
│ Pin 35 (GPIO 19)           │             │                         │
│ Pin 36 (GPIO 16) ●─────────┼─────────────┤ GPS RI/PPS (Blue wire)  │
│ Pin 37 (GPIO 26)           │             │                         │
│ Pin 38 (GPIO 20)           │             │                         │
│ Pin 39 (GND)               │             │                         │
│ Pin 40 (GPIO 21)           │             │                         │
└────────────────────────────┘             └─────────────────────────┘
```

## LED Wiring Details

Each LED requires a current-limiting resistor (220Ω recommended):

```
GPIO Pin → 220Ω Resistor → LED Anode (+) → LED Cathode (-) → Ground

Example for Power LED:
GPIO 18 (Pin 12) → 220Ω → Green LED+ → Green LED- → Ground Pin
```

### LED Specifications
- Forward voltage: ~2.0V (Red), ~2.1V (Yellow), ~2.2V (Green), ~3.2V (Blue)
- Forward current: 20mA maximum
- 220Ω resistor provides safe current limiting for 3.3V GPIO

## GPS Module Wiring (Adafruit Ultimate GPS)

### Power Connection
- **GPS VCC → Pi 5V** (Pin 2 or 4) ⭐ **5V power as requested**
- **GPS GND → Pi Ground** (Pin 6 recommended, or any ground pin)

### UART Communication  
- **GPS TX → Pi GPIO 15/RX** (Pin 10) - GPS transmits data to Pi
- **GPS RX → Pi GPIO 14/TX** (Pin 8) - Pi transmits commands to GPS

### Precision Timing (PPS)
- **GPS RI/PPS → Pi GPIO 16** (Pin 36) - Pulse Per Second signal ⭐ **Even-numbered pin**

### Wire Color Coding (Typical)
- **Red**: VCC (5V power)
- **Black**: Ground
- **Green**: GPS TX (data from GPS)
- **White**: GPS RX (data to GPS)  
- **Blue**: RI/PPS (timing pulse)

## Software Configuration Changes

### 1. Boot Configuration (`/boot/firmware/config.txt`)
```ini
# Enable UART for GPS communication
enable_uart=1

# Enable PPS GPIO overlay for precision timing
dtoverlay=pps-gpio,gpiopin=16

# Optional: Disable Bluetooth to free up primary UART
dtoverlay=disable-bt
```

### 2. Load PPS Module (`/etc/modules`)
```
pps-gpio
```

### 3. BathyCat Configuration (`config/bathyimager_config.json`)
```json
{
  "gps_port": "/dev/ttyAMA0",  // Changed from /dev/ttyUSB0 to GPIO UART
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true
}
```

## Advantages of GPIO Connection

### Timing Precision
- **USB GPS**: ~1-10ms timing uncertainty due to USB stack
- **GPIO UART**: <100μs timing precision with direct serial connection
- **GPIO PPS**: <1μs precision with hardware interrupt timing

### System Benefits
- No USB bandwidth competition with camera
- Lower CPU overhead (hardware UART vs USB polling)
- More reliable connection (no USB enumeration issues)
- Better power management
- Hardware-level precision timing support

## Testing and Verification

### Hardware Tests
```bash
# Check UART device exists
ls -la /dev/ttyAMA0

# Test GPS data reception
sudo cat /dev/ttyAMA0
# Should show NMEA sentences: $GPGGA, $GPRMC, etc.

# Check PPS device
ls -la /dev/pps0

# Test PPS pulses (needs GPS fix)
sudo ppstest /dev/pps0
```

### LED Function Test
```bash
# Test Power LED (GPIO 18)
echo 18 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio18/direction  
echo 1 > /sys/class/gpio/gpio18/value    # LED on
echo 0 > /sys/class/gpio/gpio18/value    # LED off
```

## Troubleshooting

### GPS Not Responding
1. Check 5V power connection to GPS VCC
2. Verify ground connection
3. Confirm UART is enabled in boot config
4. Test with: `sudo cat /dev/ttyAMA0`

### No PPS Signal
1. GPS must have valid fix (4+ satellites)
2. Check GPIO 16 connection to GPS RI pin
3. Verify PPS overlay enabled: `lsmod | grep pps`
4. Test outdoors for GPS fix

### LEDs Not Working
1. Check current-limiting resistors (220Ω)
2. Verify ground connections
3. Test GPIO pins manually
4. Check LED polarity (anode to resistor, cathode to ground)

## Safety Notes

- **5V GPS Power**: GPS modules typically handle 3.3V-5V. Adafruit Ultimate GPS is 5V compatible
- **Current Limiting**: Always use resistors with LEDs to prevent GPIO damage
- **Ground Connections**: Ensure solid ground connections for all components
- **Wire Gauge**: 22-24 AWG wire recommended for GPIO connections
- **Strain Relief**: Secure connections to prevent wire stress on GPIO pins

## Pin Summary Table

| Component | Function | GPIO | Physical Pin | Wire Color |
|-----------|----------|------|-------------|------------|
| GPS | Power (5V) | - | Pin 2/4 | Red |
| GPS | Ground | - | Pin 6/etc | Black |
| GPS | TX (data out) | GPIO 15 | Pin 10 | Green |
| GPS | RX (data in) | GPIO 14 | Pin 8 | White |
| GPS | PPS/RI (timing) | GPIO 16 | Pin 36 | Blue |
| LED | Power Status | GPIO 18 | Pin 12 | Green LED |
| LED | GPS Status | GPIO 23 | Pin 16 | Blue LED |
| LED | Camera Status | GPIO 24 | Pin 18 | Yellow LED |
| LED | Error Status | GPIO 25 | Pin 22 | Red LED |

This configuration provides optimal timing precision with GPIO 16 on the even-numbered Pin 36 for PPS, 5V power for the GPS as requested, and complete LED status indication system.