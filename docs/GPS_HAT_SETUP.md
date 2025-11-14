# GPS HAT Integration Guide
## Adafruit Ultimate GPS HAT Setup for BathyCat

Complete guide for upgrading to or installing the Adafruit Ultimate GPS HAT (#2324) with integrated PPS timing and hardware UART connectivity.

---

## 🏗️ Hardware Overview

### GPS HAT Features
- **Adafruit Ultimate GPS HAT** (Product #2324) - $29.95
- **HAT Form Factor**: No manual wiring required for GPS functions
- **Hardware UART**: Uses `/dev/ttyAMA0` or `/dev/serial0` for reliable communication
- **PPS Signal**: GPIO 4 (Physical Pin 7) for precision timing
- **Integrated RTC**: CR1220 battery backup for timekeeping
- **Automatic Connections**: 5V power, ground, UART, PPS, and I2C via 40-pin header

### What's Included
- ✅ GPS receiver with ceramic patch antenna
- ✅ Hardware UART connection (no USB required)
- ✅ PPS signal for nanosecond timing precision
- ✅ Real-time clock with battery backup
- ✅ Prototyping area for LED connections
- ✅ HAT identification EEPROM

---

## 📦 Hardware Installation

### Step 1: Power Down System
```bash
sudo shutdown -h now
# Wait for green LED to stop flashing before disconnecting power
```

### Step 2: Install GPS HAT
1. **Remove any existing GPS wiring** (if upgrading from USB GPS)
2. **Align HAT** with Raspberry Pi 40-pin GPIO header
3. **Press down firmly** until HAT sits flush on GPIO pins
4. **Install CR1220 battery** (optional, for RTC backup when Pi is powered off)
5. **Reconnect power** and boot Pi

### Step 3: Verify GPS HAT Detection
```bash
# Check HAT EEPROM detection
sudo cat /proc/device-tree/hat/vendor
sudo cat /proc/device-tree/hat/product

# Verify hardware UART is available
ls -la /dev/serial0 /dev/ttyAMA0

# Test GPS data reception
sudo cat /dev/serial0
# Should show NMEA sentences like: $GNGGA,123519,4807.038,N,01131.000,E...
```

---

## ⚙️ Software Configuration

### Automatic Setup
The BathyCat installation script includes GPS HAT support:

```bash
cd ~/BathyCat-Seabed-Imager
sudo ./scripts/install.sh

# The installer automatically:
# ✅ Configures hardware UART (/dev/serial0)
# ✅ Sets up PPS kernel module (pps-gpio)
# ✅ Installs GPS HAT device tree overlay
# ✅ Configures Chrony NTP with PPS source
# ✅ Updates BathyCat configuration for GPS HAT
```

### Manual Configuration (if needed)
```bash
# Enable hardware UART and disable Bluetooth UART
echo "enable_uart=1" | sudo tee -a /boot/config.txt
echo "dtoverlay=disable-bt" | sudo tee -a /boot/config.txt

# Enable PPS GPIO support
echo "dtoverlay=pps-gpio,gpiopin=4" | sudo tee -a /boot/config.txt

# Disable console on serial port
sudo raspi-config nonint do_serial 2

# Reboot to apply changes
sudo reboot
```

---

## 🔧 LED Status Indicators (Optional)

### Materials Needed
- **4x LEDs**: Green, Blue, Yellow, Red (5mm recommended)
- **4x 220Ω Resistors** (current limiting)
- **Jumper wires** or solid core hookup wire

### LED Connections to GPS HAT Prototyping Area

```
LED Wiring Diagram:
┌─────────────────────────────────────────────────────────────────────┐
│                        LED WIRING TO GPS HAT                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Power LED (Green):                                                  │
│   GPS HAT GPIO 18 ──► 220Ω Resistor ──► Green LED (+) ──┐         │
│                                                           │         │
│   GPS HAT GND ◄─────────────────────── Green LED (-) ◄───┘         │
│                                                                     │
│ GPS Status LED (Blue):                                              │
│   GPS HAT GPIO 23 ──► 220Ω Resistor ──► Blue LED (+) ───┐         │
│                                                           │         │
│   GPS HAT GND ◄─────────────────────── Blue LED (-) ◄────┘         │
│                                                                     │
│ Camera LED (Yellow):                                                │
│   GPS HAT GPIO 24 ──► 220Ω Resistor ──► Yellow LED (+) ─┐         │
│                                                           │         │
│   GPS HAT GND ◄─────────────────────── Yellow LED (-) ◄──┘         │
│                                                                     │
│ Error LED (Red):                                                    │
│   GPS HAT GPIO 25 ──► 220Ω Resistor ──► Red LED (+) ────┐         │
│                                                           │         │
│   GPS HAT GND ◄─────────────────────── Red LED (-) ◄─────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

GPIO Pin Mapping:
• GPIO 4  (Pin 7)  = PPS Signal (automatic via HAT)
• GPIO 18 (Pin 12) = Power LED (Green)
• GPIO 23 (Pin 16) = GPS Status LED (Blue)  
• GPIO 24 (Pin 18) = Camera Status LED (Yellow)
• GPIO 25 (Pin 22) = Error LED (Red)
```

### LED Status Patterns
| LED | Color | Pattern | Meaning |
|-----|-------|---------|---------|
| **Power** | Green | Solid | System running normally |
| Power | Green | Slow blink (1Hz) | System starting up |
| Power | Green | Off | System stopped or failed |
| **GPS** | Blue | Solid | GPS fix acquired |
| GPS | Blue | Slow blink (0.5Hz) | Searching for GPS fix |
| GPS | Blue | Off | GPS disabled or failed |
| **Camera** | Yellow | Brief flash | Image captured |
| Camera | Yellow | SOS pattern | Camera error/failure |
| **Error** | Red | Off | No critical errors |
| Error | Red | Solid | Critical system error |

---

## 🛰️ GPS HAT Configuration

### BathyCat Configuration Update
Update `config/bathyimager_config.json` for GPS HAT:

```json
{
  "gps": {
    "port": "/dev/serial0",               # Hardware UART (was /dev/ttyUSB0)
    "baudrate": 9600,
    "timeout": 1.0,
    "require_gps_fix": true,
    "mock_mode": false,
    "pps_enabled": true,                  # Enable PPS timing
    "pps_device": "/dev/pps0"             # PPS device path
  }
}
```

### PPS Timing Validation
```bash
# Check PPS device is available
ls -la /dev/pps0

# Monitor PPS signals
sudo ppstest /dev/pps0

# Check PPS kernel module
lsmod | grep pps_gpio

# Verify PPS events in sysfs
cat /sys/class/pps/pps0/assert
cat /sys/class/pps/pps0/clear
```

### Chrony NTP Configuration
PPS timing is automatically configured with Chrony:

```bash
# Check Chrony PPS source
chrony sources -v

# Expected output should show PPS(0) source
# Check time synchronization accuracy
chronyc tracking

# Should show accuracy in microseconds with PPS
```

---

## 🔍 Testing and Validation

### GPS Data Reception Test
```bash
# Test NMEA data stream
sudo cat /dev/serial0 | head -20

# Expected output (sample NMEA sentences):
# $GNGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
# $GNRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```

### PPS Signal Test
```bash
# Run BathyCat PPS validation script
cd ~/BathyCat-Seabed-Imager/tests
python3 test_pps_system_sync.py --duration 30

# Expected output:
# ✅ GPS fix: Active
# ✅ PPS device detected via sysfs
# ✅ GPIO PPS signal: 1Hz pulses detected
# ✅ System time accuracy: <50μs
```

### Complete System Test
```bash
# Run comprehensive hardware diagnostics
python3 tests/troubleshoot.py --quick

# Start BathyCat service and verify GPS integration
sudo systemctl start bathyimager
sudo journalctl -u bathyimager -f

# Check for GPS fix and image geotagging
ls -la /media/usb/bathyimager/images/$(date +%Y%m%d)/
python3 tests/analyze_exif.py /media/usb/bathyimager/images/$(date +%Y%m%d)/*.jpg
```

---

## 🚨 Troubleshooting

### GPS HAT Not Detected
```bash
# Check HAT EEPROM
sudo cat /proc/device-tree/hat/vendor
# Should show: Adafruit Industries LLC

# Check hardware connections
sudo i2cdetect -y 1
# Should show HAT EEPROM at address 0x50

# Verify GPIO pins not in use by other services
sudo cat /sys/kernel/debug/gpio
```

### No GPS Data on /dev/serial0
```bash
# Check UART configuration
sudo cat /boot/config.txt | grep uart
# Should show: enable_uart=1

# Check if Bluetooth is using UART
sudo systemctl status hciuart
# Should be disabled for GPS HAT

# Test different serial devices
ls -la /dev/tty*
sudo cat /dev/ttyAMA0  # Alternative UART device
```

### PPS Not Working
```bash
# Check PPS device tree overlay
sudo cat /boot/config.txt | grep pps-gpio
# Should show: dtoverlay=pps-gpio,gpiopin=4

# Check PPS kernel module
lsmod | grep pps
# Should show: pps_gpio

# Manually load PPS module if missing
sudo modprobe pps-gpio

# Check GPIO 4 is configured for PPS
sudo cat /sys/kernel/debug/gpio | grep gpio-4
```

### System Time Not Syncing with GPS
```bash
# Check Chrony configuration
sudo cat /etc/chrony/chrony.conf | grep pps

# Check Chrony status
chronyc sources -v
chronyc tracking

# Restart Chrony service
sudo systemctl restart chronyd

# Check for NTP conflicts
sudo systemctl status ntp
# Should be disabled if using Chrony
```

---

## 🔧 Advanced Configuration

### Custom PPS GPIO Pin
If you need to use a different GPIO pin for PPS:

```bash
# Edit boot configuration
sudo nano /boot/config.txt

# Change PPS GPIO pin (default is 4)
dtoverlay=pps-gpio,gpiopin=18

# Update BathyCat configuration
nano config/bathyimager_config.json
# Update: "pps_gpio_pin": 18

# Reboot to apply changes
sudo reboot
```

### Indoor Testing Without GPS Signal
```bash
# Enable mock GPS mode for development
nano config/bathyimager_config.json

{
  "gps": {
    "mock_mode": true,
    "mock_latitude": 40.7128,
    "mock_longitude": -74.0060,
    "require_gps_fix": false
  }
}
```

### External GPS Antenna
For indoor use or better signal reception:

1. **Purchase**: Adafruit GPS External Antenna (Product #960)
2. **Connect**: uFL connector on GPS HAT to external antenna
3. **Position**: Place antenna near window or outdoors
4. **Test**: GPS should acquire fix faster and maintain better signal

---

## 📚 Related Documentation

- **[Installation Guide](INSTALL.md)**: Complete BathyCat system setup
- **[Troubleshooting Guide](TROUBLESHOOTING.md)**: Problem resolution procedures
- **[Network Setup](NETWORK_SETUP.md)**: Networking configuration for updates
- **[Logging System](LOGGING_SYSTEM.md)**: Understanding BathyCat logs

---

## 🎯 Key Benefits of GPS HAT Upgrade

- **✅ Reliability**: Hardware UART more stable than USB connection
- **⚡ PPS Timing**: Nanosecond precision for image timestamping
- **🔋 RTC Backup**: Maintains time when GPS signal unavailable
- **🔧 Simplicity**: No manual wiring for GPS functions
- **📶 Better Signal**: Integrated antenna with external antenna option
- **💻 Integration**: Seamless BathyCat system integration

The Adafruit Ultimate GPS HAT provides a professional-grade GPS solution optimized for precision timing applications like the BathyCat Seabed Imager.