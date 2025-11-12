# BathyCat GPS HAT Wiring Guide
## Adafruit Ultimate GPS HAT + LED Status Indicators

**Hardware**: [Adafruit Ultimate GPS HAT #2324](https://www.adafruit.com/product/2324)  
**Compatible**: Raspberry Pi 4, Pi 5 (40-pin GPIO)

---

## 📋 Materials List

### Required Components
- ✅ **Adafruit Ultimate GPS HAT #2324** - $29.95
- ✅ **4x LEDs**: Green, Blue, Yellow, Red (5mm recommended)
- ✅ **4x 220Ω Resistors** (current limiting for LEDs)
- ✅ **Jumper wires** or solid core hookup wire
- ✅ **CR1220 Battery** (optional, for RTC backup)

### Optional Components
- **Breadboard** - for temporary connections
- **External GPS Antenna** - for indoor use
- **Soldering kit** - for permanent connections to HAT prototyping area

---

## 🔧 Installation Steps

### Step 1: Install GPS HAT (Power Off Required)

```bash
# Power down Raspberry Pi safely
sudo shutdown -h now

# Wait for Pi to fully power down (green LED stops)
# Remove power cable from Pi
```

**Physical Installation:**
1. **Align HAT** with Raspberry Pi 40-pin GPIO header
2. **Press down firmly** until HAT sits flush on GPIO header
3. **Install CR1220 battery** (optional, for RTC backup)
4. **Reconnect power** and boot Pi

**Automatic Connections via HAT:**
- ✅ **5V Power**: Supplied from Pi 5V rail
- ✅ **Ground**: Connected to Pi ground
- ✅ **UART**: Hardware serial `/dev/ttyAMA0` (GPIO 14/15)
- ✅ **PPS Signal**: **GPIO 4 (Physical Pin 7)** ⚡
- ✅ **I2C**: SDA/SCL for HAT identification

### Step 2: Verify GPS HAT Detection

```bash
# Boot Pi and check GPS HAT detection
lsusb  # Should NOT show USB GPS (now using UART)
ls /dev/ttyAMA0  # Should show GPS UART device

# Check GPIO 4 (PPS) availability
cat /sys/kernel/debug/gpio  # Look for gpio-4

# Test GPS data stream
sudo cat /dev/ttyAMA0
# Should show NMEA sentences: $GPGGA,$GPRMC,etc.
```

---

## 🚨 LED Status System Wiring

### Physical Pin Reference
Based on **confirmed Raspberry Pi GPIO pinout**:

| GPIO | Physical Pin | BathyCat Function | LED Color |
|------|--------------|-------------------|-----------|
| GPIO 4  | Pin 7  | **PPS Signal** (automatic) | N/A |
| GPIO 18 | Pin 12 | Power/Status LED | **Green** |
| GPIO 23 | Pin 16 | GPS Status LED | **Blue** |
| GPIO 24 | Pin 18 | Camera Status LED | **Yellow** |
| GPIO 25 | Pin 22 | Error Status LED | **Red** |

### Complete LED Wiring Diagram

```
                    ADAFRUIT ULTIMATE GPS HAT
    ┌─────────────────────────────────────────────────────────┐
    │  GPS Module        Prototyping Area         Components  │
    │     🛰️              ┌─────────────────┐                │
    │  [Antenna]          │ #4  #5  #6  #7  │    [CR1220]    │
    │    |                │ #8  #9  #10 #11 │    Battery     │
    │  [GPS IC]           │ #12 #13 #14 #15 │       │        │
    │    |                │ #16 #17 #18 #19 │    [u.FL]      │
    │ Status LED          │ #20 #21 #22 #23 │    Antenna     │
    │    💡               │ #24 #25 #26 #27 │    Connector   │
    │                     │ GND 5V  3V3     │                │
    │                     └─────────────────┘                │
    └─────────────────────────────────────────────────────────┘
             │                    │
             ▼                    ▼
    Automatic GPIO            LED Connections
    Connections via           to Prototyping
    40-pin Header            Area (Manual)

LED WIRING TO HAT PROTOTYPING AREA:

Power LED (Green) - GPIO 18:
   HAT #18 ──► 220Ω ──► Green LED (+) ──┐
                                        │
   HAT GND ◄──────────── Green LED (-) ◄─┘

GPS LED (Blue) - GPIO 23:  
   HAT #23 ──► 220Ω ──► Blue LED (+) ───┐
                                        │
   HAT GND ◄──────────── Blue LED (-) ◄──┘

Camera LED (Yellow) - GPIO 24:
   HAT #24 ──► 220Ω ──► Yellow LED (+) ─┐
                                        │
   HAT GND ◄──────────── Yellow LED (-) ◄┘

Error LED (Red) - GPIO 25:
   HAT #25 ──► 220Ω ──► Red LED (+) ────┐
                                        │
   HAT GND ◄──────────── Red LED (-) ◄───┘

POWER DISTRIBUTION:
   Pi 5V Rail ──► HAT 5V Rail ──► GPS Module + Prototyping
   Pi GND Rail ──► HAT GND Rail ──► All LED Returns
```

### LED Connection Details

#### Method 1: Breadboard Prototyping (Temporary)
```
Components Needed:
- Half-size breadboard
- Male-to-male jumper wires  
- LEDs and resistors

Connections:
1. HAT Pin #18 → Breadboard → 220Ω → Green LED → GND
2. HAT Pin #23 → Breadboard → 220Ω → Blue LED → GND  
3. HAT Pin #24 → Breadboard → 220Ω → Yellow LED → GND
4. HAT Pin #25 → Breadboard → 220Ω → Red LED → GND
5. HAT GND → Breadboard GND rail (common return)
```

#### Method 2: Direct HAT Soldering (Permanent)
```
Materials Needed:
- 22-24 AWG solid core wire
- Soldering iron and solder
- LEDs with leads

Process:
1. Solder wires to HAT prototyping area GPIO pins
2. Solder 220Ω resistors in series with LED anodes  
3. Connect LED cathodes to HAT GND points
4. Heat shrink or insulate all connections
5. Mount LEDs in enclosure or panel
```

### LED Behavior Reference

| LED | Color | Steady | Blinking | SOS Pattern | Off |
|-----|-------|--------|----------|-------------|-----|
| **Power** | Green | System Running | Starting Up | Shutting Down | System Off |
| **GPS** | Blue | Fix Acquired | Searching | N/A | GPS Disabled |
| **Camera** | Yellow | Standby | Capturing | Error | Camera Off |
| **Error** | Red | Critical Error | Warning | N/A | No Errors |

---

## ⚙️ Software Configuration

### Enable GPS HAT in BathyCat Config

```json
{
  "gps_port": "/dev/ttyAMA0",
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true,
  
  "pps_enabled": true,
  "pps_gpio_pin": 4,
  "pps_device": "/dev/pps0",
  
  "led_power_pin": 18,
  "led_gps_pin": 23,
  "led_camera_pin": 24,
  "led_error_pin": 25
}
```

### System Configuration (Boot Config)

Update `/boot/firmware/config.txt`:
```ini
# GPS HAT Configuration
enable_uart=1
dtoverlay=pps-gpio,gpiopin=4
```

Enable PPS kernel module:
```bash
echo 'pps-gpio' | sudo tee -a /etc/modules
```

### Test Installation

```bash
# Run BathyCat GPS HAT test suite
python3 tests/test_gps_hat_pps.py

# Expected results:
# ✅ Hardware Detection: GPS HAT found
# ✅ PPS Interface: GPIO 4 configured  
# ✅ GPS Connection: UART communication
# ✅ LED Status: All 4 LEDs functional
```

---

## 🔍 Troubleshooting

### GPS HAT Not Detected
```bash
# Check HAT installation
ls /dev/ttyAMA0  # Should exist
dmesg | grep -i uart  # Look for ttyAMA0 initialization

# If missing, check HAT seating and boot config
```

### PPS Not Working
```bash
# Check PPS device
ls /dev/pps*  # Should show /dev/pps0

# Test PPS signal (requires GPS fix)
sudo ppstest /dev/pps0
# Should show: source 0 - assert [timestamp], sequence: [number]
```

### LEDs Not Working
```bash
# Test individual LED manually
echo 18 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio18/direction  
echo 1 > /sys/class/gpio/gpio18/value    # LED on
echo 0 > /sys/class/gpio/gpio18/value    # LED off

# Check wiring and resistor values
```

### GPS No Fix Indoors
```bash
# This is normal - GPS requires clear sky view
# For indoor testing, enable mock GPS mode:
```
```json
{
  "gps": {
    "mock_mode": true,
    "mock_latitude": 40.7128,
    "mock_longitude": -74.0060
  }
}
```

---

## 📐 Mechanical Considerations

### Enclosure Requirements
- **Height clearance**: GPS HAT adds ~7mm to Pi thickness
- **Antenna access**: GPS antenna needs clear sky view
- **LED visibility**: Position LEDs for operational visibility
- **Heat dissipation**: Ensure adequate ventilation

### Marine Environment Protection
- **IP67+ enclosure** recommended for marine use
- **Cable glands** for antenna and power connections  
- **Desiccant packs** to prevent condensation
- **Shock mounting** for vessel vibration protection

---

## 🎯 Final Verification Checklist

### Hardware Checklist
- [ ] GPS HAT physically installed and secure
- [ ] CR1220 battery installed (optional)
- [ ] 4x LEDs wired with 220Ω resistors
- [ ] All LED connections secure and insulated
- [ ] External GPS antenna connected (if used)

### Software Checklist  
- [ ] `/dev/ttyAMA0` device present
- [ ] `/dev/pps0` device present after GPS fix
- [ ] BathyCat config updated for GPS HAT
- [ ] Boot config updated for UART and PPS
- [ ] Test suite passes all critical tests

### Operational Checklist
- [ ] Green LED: Steady when system running
- [ ] Blue LED: Blinking while searching, steady with GPS fix  
- [ ] Yellow LED: Flashes with each image capture
- [ ] Red LED: Off during normal operation
- [ ] GPS data visible in logs and image EXIF
- [ ] PPS timing active (sub-microsecond precision)

---

**Installation Complete!** 🎉  
Your BathyCat system now has professional GPS HAT with nanosecond PPS timing and comprehensive LED status indicators.