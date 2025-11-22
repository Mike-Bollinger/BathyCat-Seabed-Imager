# BathyCat Shutdown Button Wiring Guide

## Components Required

### Pushbutton
- **Omron B3F-4055** momentary pushbutton
- **Digikey Part**: [B3F-4055](https://www.digikey.com/en/products/detail/omron-electronics-inc-emc-div/B3F-4055/31799)
- **Alternative**: Any SPST momentary pushbutton (normally open)

### Wiring Materials
- **22-24 AWG stranded wire** (2 wires, ~6 inches each)
- **Dupont connectors** or **breadboard jumper wires**
- **Heat shrink tubing** (optional, for strain relief)

## GPIO Pin Assignments

| Function | GPIO Pin | Physical Pin | Status |
|----------|----------|--------------|---------|
| PPS Signal | GPIO 4 | Pin 7 | **USED** (GPS HAT) |
| Shutdown Button | **GPIO 17** | **Pin 11** | **NEW** |
| Power LED (Green) | GPIO 18 | Pin 12 | **USED** |
| GPS LED (Blue) | GPIO 23 | Pin 16 | **USED** |
| Camera LED (Yellow) | GPIO 24 | Pin 18 | **USED** |
| Error LED (Red) | GPIO 25 | Pin 22 | **USED** |

## Wiring Diagram

```
Raspberry Pi 4 GPIO Header (Top View)
=====================================

    3.3V  [ 1] [ 2]  5V
   GPIO2  [ 3] [ 4]  5V
   GPIO3  [ 5] [ 6]  GND
   GPIO4  [ 7] [ 8]  GPIO14
     GND  [ 9] [10]  GPIO15
  GPIO17  [11] [12]  GPIO18  ← Power LED (Green)
  GPIO27  [13] [14]  GND     ← Connect to Button
  GPIO22  [15] [16]  GPIO23  ← GPS LED (Blue)
    3.3V  [17] [18]  GPIO24  ← Camera LED (Yellow)
  GPIO10  [19] [20]  GND
   GPIO9  [21] [22]  GPIO25  ← Error LED (Red)
  GPIO11  [23] [24]  GPIO8
     GND  [25] [26]  GPIO7
   GPIO0  [27] [28]  GPIO1
   GPIO5  [29] [30]  GND
   GPIO6  [31] [32]  GPIO12
  GPIO13  [33] [34]  GND
  GPIO19  [35] [36]  GPIO16
  GPIO26  [37] [38]  GPIO20
     GND  [39] [40]  GPIO21

         ↑            ↑
   Shutdown Button   Power LED
     (GPIO 17)       (GPIO 18)
      Pin 11          Pin 12
```

## Physical Connections

### Omron B3F-4055 Pinout
```
        Top View
    ┌─────────────┐
    │  1       3  │
    │             │
    │  2       4  │
    └─────────────┘
    
Pin 1 & 2: Normally Open contacts (use these)
Pin 3 & 4: Normally Open contacts (not used)
```

### Connection Details
```
Omron B3F-4055 → Raspberry Pi
===============================
Pin 1 → GPIO 17 (Physical Pin 11)
Pin 2 → GND (Physical Pin 14)

Note: Pins 3 & 4 are not connected
```

## Installation Steps

### 1. Power Down System
```bash
sudo shutdown -h now
```

### 2. Connect Button Wires
1. **Cut two 6-inch wires** (red for GPIO, black for GND)
2. **Strip 1/4 inch** from each end
3. **Solder to button**:
   - Red wire → Pin 1 of B3F-4055
   - Black wire → Pin 2 of B3F-4055
4. **Add heat shrink** around solder joints (optional)

### 3. Connect to Raspberry Pi
1. **Red wire** → Pin 11 (GPIO 17)
2. **Black wire** → Pin 14 (GND)

### 4. Secure Installation
- Mount button in enclosure/panel
- Route wires to avoid strain on connections
- Use cable ties or wire management as needed

## Software Configuration

The shutdown button is automatically configured during installation:

### Service Status
```bash
# Check if shutdown button service is running
sudo systemctl status shutdown-button

# View shutdown button logs
sudo journalctl -u shutdown-button -f
```

### Manual Testing
```bash
# Test the shutdown button script manually
sudo python3 /home/bathyimager/BathyCat-Seabed-Imager/scripts/shutdown_button.py
```

## Operation

### Normal Shutdown Sequence
1. **Press button once**: All 4 LEDs start blinking
2. **Press button again within 10 seconds**: Shutdown begins
   - Only green LED blinks during shutdown
   - Service stops gracefully
   - System powers off
3. **Wait 10+ seconds**: Returns to normal operation

### Safety Features
- **Two-stage activation** prevents accidental shutdown
- **Visual feedback** with LED status indicators
- **Service integration** ensures clean shutdown
- **Filesystem sync** before power-off

## Troubleshooting

### Button Not Responding
```bash
# Check GPIO state manually
gpio readall | grep -E "(17|18|23|24|25)"

# Test button connection
sudo python3 -c "
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
for i in range(10):
    print(f'Button state: {GPIO.input(17)}')
    time.sleep(1)
GPIO.cleanup()
"
```

### Service Issues
```bash
# Restart shutdown button service
sudo systemctl restart shutdown-button

# Check service logs for errors
sudo journalctl -u shutdown-button --no-pager
```

### LED Issues
```bash
# Test LED functionality
sudo python3 -c "
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
for pin in [18, 23, 24, 25]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(pin, GPIO.LOW)
GPIO.cleanup()
"
```

## Hardware Specifications

### Omron B3F-4055 Specifications
- **Contact Type**: SPST-NO (Single Pole Single Throw - Normally Open)
- **Contact Rating**: 50mA @ 12VDC
- **Operating Force**: 1.6N (160gf)
- **Contact Resistance**: < 100mΩ
- **Mechanical Life**: 1,000,000 operations
- **Operating Temperature**: -25°C to +70°C

### GPIO Specifications
- **Input Voltage**: 3.3V logic
- **Pull-up Resistor**: 50kΩ (internal)
- **Input Current**: < 10µA
- **Debounce**: Software debounced (50ms)

## Safety Notes

⚠️ **Important Safety Information**:
- Always power down before making connections
- Use proper ESD precautions when handling Pi
- Double-check wiring before applying power
- Button is active-low (closes to ground)
- Do not exceed 3.3V on GPIO pins
- Test installation before deployment