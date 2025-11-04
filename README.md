# BathyImager Seabed Imager

An autonomous seabed imaging system for surface vessels, capturing geotagged images and storing them on USB drives.

## Project Overview

The BathyImager Seabed Imager is designed to run on autonomous surface vessels (ASVs) to capture continuous imagery of the seabed. The system uses a downward-facing camera, integrates GPS coordinates into image metadata, and stores everything on external USB storage for later analysis.

### Key Features

- **Autonomous Operation**: Runs as a systemd service with automatic startup
- **GPS Geotagging**: Embeds precise GPS coordinates into EXIF metadata
- **USB Storage**: Organized file storage with automatic cleanup
- **LED Status Indicators**: Visual feedback for system status
- **Robust Error Handling**: Graceful degradation and automatic recovery
- **Wireless Compatible**: SSH access for remote monitoring
- **Indoor Testing**: Mock GPS mode for development and testing

### Hardware Requirements

- **Raspberry Pi 4 Model B** (4GB RAM recommended)
- **DWE StellarHD USB Camera** (1080p@30fps capable)
- **Adafruit Ultimate GPS - USB Version**
- **SanDisk 512GB USB 3.0 Flash Drive** (or similar)
- **MicroSD Card** (32GB+ for OS and logs)
- **Status LEDs** (optional, for visual feedback)

## Quick Start Guide

### Fresh Raspberry Pi Setup (Complete Installation)

#### 1. Prepare Raspberry Pi OS
```bash
# Start with fresh Raspberry Pi OS (Bullseye or later recommended)
# Enable SSH if needed: sudo systemctl enable ssh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install git (if not already installed)
sudo apt install -y git

# Create project directory and clone repository
cd ~
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager
```

#### 2. Connect Hardware
```bash
# Before running installer, connect hardware:
# - USB Camera (should appear as /dev/video0)
# - USB GPS (should appear as /dev/ttyUSB0 or /dev/ttyACM0) 
# - USB Storage Drive (will be mounted to /media/usb)
# - LED indicators on GPIO pins 18, 23, 24, 25 (optional)

# Verify hardware detection
lsusb  # Should show camera and GPS
ls -la /dev/video* /dev/ttyUSB* /dev/ttyACM*
```

#### 3. Run Full Installation
```bash
# Run the comprehensive installation script
sudo ./scripts/install.sh

# The installer will:
# - Update the system packages
# - Install required dependencies (Python, OpenCV, etc.)
# - Create 'bathyimager' user account
# - Set up Python virtual environment
# - Install Python packages
# - Configure device permissions and udev rules
# - Create and enable systemd service
# - Set up USB auto-mounting
# - Configure log rotation
# - Run initial hardware tests
```

#### 4. Verify Installation
```bash
# Check hardware and permissions
./scripts/hardware_diagnostics.sh all

# Check service status
sudo systemctl status bathyimager

# View real-time logs
sudo journalctl -u bathyimager -f

# If service is running, you should see:
# - Solid green LED (power)
# - Blue LED (GPS status) - solid when fix acquired
# - Yellow LED flashes briefly each time photo is taken
# - Images being saved to /media/usb/bathyimager/images/YYYYMMDD/
```

### 2. Hardware Diagnostics and Configuration

```bash
# Run hardware diagnostics to check system status
./scripts/hardware_diagnostics.sh all

# Check device permissions and user groups
./scripts/hardware_diagnostics.sh permissions

# Edit configuration if needed (installer creates default)
sudo nano config/bathycat_config.json

# Test hardware manually if needed
./scripts/hardware_diagnostics.sh camera
./scripts/hardware_diagnostics.sh gps
```

### 3. Network Configuration (Dual Ethernet + WiFi)

BathyImager supports simultaneous Ethernet and WiFi connectivity for maximum reliability:

```bash
# Setup dual networking (Ethernet primary, WiFi backup)
sudo ./scripts/network_setup.sh

# Configure WiFi networks interactively
sudo ./scripts/wifi_config.sh

# Check network status
./scripts/network_status.sh

# Test connectivity
./scripts/network_test.sh
```

**Key Features:**
- **Automatic Priority**: Ethernet (metric 100) preferred over WiFi (metric 300)
- **Seamless Failover**: Maintains connectivity if primary interface fails
- **Easy Management**: Interactive scripts for configuration and monitoring

See [Network Setup Guide](docs/NETWORK_SETUP.md) for detailed configuration instructions.

## System Control

### Service Management Commands

```bash
# Check current service status
sudo systemctl status bathyimager

# Start the imaging system
sudo systemctl start bathyimager

# Stop the imaging system
sudo systemctl stop bathyimager

# Restart the system (applies configuration changes)
sudo systemctl restart bathyimager

# Enable auto-start on boot (production mode)
sudo systemctl enable bathyimager

# Disable auto-start on boot
sudo systemctl disable bathyimager

# View real-time system logs
sudo journalctl -u bathyimager -f

# View recent logs (last 50 lines)
sudo journalctl -u bathyimager -n 50
```

### Manual Operation (Testing/Development)

```bash
# Run system manually for testing (stops when you press Ctrl+C)
cd ~/BathyCat-Seabed-Imager
./run_bathyimager.sh

# Run with debug output
./run_bathyimager.sh --verbose

# Run with custom configuration
./run_bathyimager.sh --config config/custom_config.json

# Run Python directly (advanced)
cd src
source ../venv/bin/activate
python3 main.py --config ../config/bathycat_config.json
```

### System Shutdown

```bash
# Graceful shutdown (recommended)
sudo systemctl stop bathyimager

# Check that service has stopped
sudo systemctl status bathyimager

# For complete system shutdown
sudo shutdown -h now

# Or reboot system
sudo reboot
```

## System Architecture

### Core Components

1. **Camera Module** (`src/camera.py`)
   - OpenCV-based USB camera interface
   - Configurable resolution, FPS, and image quality
   - Health monitoring and error recovery

2. **GPS Module** (`src/gps.py`)
   - NMEA sentence parsing using pynmea2
   - Serial communication with GPS device
   - Mock GPS support for testing

3. **Image Processor** (`src/image_processor.py`)
   - EXIF GPS metadata embedding
   - JPEG optimization and compression
   - Coordinate format conversion

4. **Storage Manager** (`src/storage.py`)
   - Hierarchical directory organization (YYYY/MM/DD)
   - Automatic file cleanup based on age/space
   - USB device monitoring

5. **LED Status System** (`src/led_status.py`)
   - GPIO-based LED control
   - Status indication (OK, Error, Activity)
   - Configurable blink patterns

6. **Main Service** (`src/main.py`)
   - Coordinates all subsystems
   - Threaded execution for concurrent operations
   - Signal handling for graceful shutdown

### Configuration System

The enhanced configuration system (`src/config.py`) provides:

- **Environment Detection**: Automatically detects hardware and adjusts settings
- **Validation**: Comprehensive configuration validation with detailed error messages
- **Environment Profiles**: Different settings for development/testing/production
- **Hot Reloading**: Runtime configuration updates without service restart

### File Organization

```
/home/bathyimager/BathyCat-Seabed-Imager/  # Installation directory
├── src/                                    # Source code
├── scripts/                               # Installation and maintenance scripts
├── config/                                # Configuration files
├── venv/                                 # Python virtual environment
├── run_bathyimager.sh                    # Service run script
└── update                                # Quick update script

/var/log/bathyimager/         # Log directory
├── bathyimager.log           # Application logs (rotated)
└── system.log               # System-level logs

/media/usb/                  # Default USB storage mount point
└── bathyimager/            # BathyImager data directory
    └── YYYY/MM/DD/         # Date-based organization
        └── bathyimager_*.jpg  # Geotagged images

/etc/systemd/system/         # System service files
└── bathyimager.service     # BathyImager systemd service

/etc/udev/rules.d/          # Device rules
└── 99-bathyimager.rules   # Hardware permission rules
```

## Configuration Reference

### Camera Settings

```json
{
  "camera": {
    "device_index": 0,          # USB camera device (/dev/video0)
    "width": 1920,              # Image width in pixels
    "height": 1080,             # Image height in pixels
    "fps": 30,                  # Frames per second
    "format": "MJPG",           # Video format (MJPG recommended)
    "jpeg_quality": 95,         # JPEG compression quality (1-100)
    "capture_timeout": 5.0,     # Timeout for frame capture
    "retry_count": 3,           # Retry attempts on failure
    "auto_focus": false,        # Enable auto-focus (if supported)
    "exposure": -1,             # Manual exposure (-1 = auto)
    "brightness": 128,          # Brightness adjustment
    "contrast": 32,             # Contrast adjustment
    "saturation": 32            # Saturation adjustment
  }
}
```

### GPS Settings

```json
{
  "gps": {
    "port": "/dev/ttyUSB0",     # GPS device port
    "baudrate": 9600,           # Serial communication speed
    "timeout": 2.0,             # Read timeout in seconds
    "fix_timeout": 30.0,        # Time to wait for GPS fix
    "min_satellites": 4,        # Minimum satellites for valid fix
    "min_accuracy": 10.0,       # Minimum accuracy in meters
    "mock_enabled": false,      # Enable mock GPS for testing
    "mock_latitude": 40.7128,   # Mock GPS latitude
    "mock_longitude": -74.0060  # Mock GPS longitude
  }
}
```

### Storage Settings

```json
{
  "storage": {
    "base_path": "/media/usb",              # USB mount point
    "filename_prefix": "bathyimager",       # Prefix for image filenames
    "max_images_per_day": 10000,            # Daily image limit
    "cleanup_days": 30,                     # Delete files older than N days
    "min_free_space_mb": 1000,              # Minimum free space (MB)
    "directory_structure": "%Y/%m/%d",      # Date-based folders
    "filename_format": "bathyimager_%Y%m%d_%H%M%S_{counter:04d}.jpg"
  }
}
```

### LED Indicators

```json
{
  "leds": {
    "status_pin": 18,           # Status LED GPIO pin (BCM)
    "error_pin": 19,            # Error LED GPIO pin (BCM)  
    "activity_pin": 20,         # Activity LED GPIO pin (BCM)
    "enabled": true,            # Enable LED indicators
    "blink_rate": 0.5,          # Blink interval in seconds
    "brightness": 0.8,          # LED brightness (0.0-1.0)
    "startup_test": true        # Test LEDs at startup
  }
}
```

### System Settings

```json
{
  "system": {
    "environment": "production",        # Environment: development/testing/production
    "capture_interval": 1.0,            # Seconds between image captures
    "max_capture_errors": 10,           # Max consecutive errors before restart
    "restart_on_error": true,           # Auto-restart on critical errors
    "health_check_interval": 60.0,      # Health check frequency (seconds)
    "watchdog_timeout": 300.0,          # Service watchdog timeout
    "graceful_shutdown_timeout": 30.0,  # Shutdown timeout
    "performance_monitoring": false     # Enable performance metrics
  }
}
```

## Operation Guide

### System Startup and Shutdown

#### Automatic Operation (Production Mode)
```bash
# Enable auto-start on boot
sudo systemctl enable bathyimager

# Start service now
sudo systemctl start bathyimager

# Check if service is running
sudo systemctl status bathyimager

# Stop service
sudo systemctl stop bathyimager

# Disable auto-start
sudo systemctl disable bathyimager
```

#### Manual Operation (Testing/Development)
```bash
# Run system manually for testing
cd ~/BathyCat-Seabed-Imager
./run_bathyimager.sh

# Run with specific configuration
./run_bathyimager.sh --config config/custom_config.json

# Run in development mode
cd src
python3 main.py --config ../config/bathycat_config.json
```

### Normal Operation Flow

1. **System Startup**
   - Service starts automatically on boot (if enabled)
   - LED self-test sequence (all LEDs briefly light)
   - Hardware initialization and health checks
   - GPS connection and fix acquisition
   - USB storage detection and mounting
   - Image capture begins when systems ready

2. **Image Capture Process**
   - Continuous capture at configured interval (default: 1 second)
   - GPS coordinates embedded in EXIF metadata (when available)
   - Images saved with timestamp-based naming
   - Visual status indicated via LEDs
   - Comprehensive logging to files and system journal

3. **Storage Management**
   - Automatic directory creation by date (YYYY/MM/DD)
   - File cleanup when storage limits reached
   - USB device monitoring and automatic remounting
   - Graceful handling of storage device removal/insertion

4. **Error Recovery**
   - Automatic retry on hardware failures
   - Service continues even if GPS or camera temporarily unavailable
   - LED indicators show system health status
   - Detailed error logging for troubleshooting

### LED Status Indicators

The BathyImager system uses GPIO-controlled LEDs to provide visual status feedback during autonomous operation. LEDs are configured via the `led_*_pin` settings in the configuration file.

#### LED Configuration

```json
{
  "led_power_pin": 18,    # Power/Status LED (GPIO 18)
  "led_gps_pin": 23,      # GPS Status LED (GPIO 23) 
  "led_camera_pin": 24,   # Camera Status LED (GPIO 24)
  "led_error_pin": 25     # Error Status LED (GPIO 25)
}
```

#### LED Status Patterns

| LED | Color/Location | Pattern | Meaning |
|-----|----------------|---------|---------|
| **Power LED** (GPIO 18) | Green | Solid | System running normally |
| Power LED | Green | Slow blink (1 Hz) | System starting up |
| Power LED | Green | Fast blink (2 Hz) | System shutting down |
| Power LED | Off | System powered off or failed |
| **GPS LED** (GPIO 23) | Blue | Solid | GPS fix acquired |
| GPS LED | Blue | Slow blink (0.5 Hz) | GPS searching for fix |
| GPS LED | Off | GPS disabled or failed |
| **Camera LED** (GPIO 24) | Yellow | Brief flash | Image captured (each photo) |
| Camera LED | Yellow | Solid | Camera active/standby |
| Camera LED | Yellow | SOS pattern (... --- ...) | Camera error/failure |
| Camera LED | Off | Camera inactive or disabled |
| **Error LED** (GPIO 25) | Red | Off | No critical errors |
| Error LED | Red | Solid | Critical system error - see troubleshooting |

#### Critical Error Conditions (Red LED)

When the red error LED is solid, it indicates one or more critical system failures that prevent normal operation:

| Error Condition | Description | Troubleshooting |
|----------------|-------------|-----------------|
| **Storage Failure** | USB drive disconnected, full, or write-protected | Check USB connection, free space, and mount status |
| **Camera Disconnected** | USB camera hardware failure or disconnection | Check USB camera connection and power |
| **GPS Disconnected** | GPS hardware failure (when GPS required) | Check GPS USB connection and device detection |
| **Capture Failure** | More than 5 consecutive image capture failures | Check camera and storage health, restart service |
| **Low Disk Space** | Less than 1GB of free storage space remaining | Clean up old files or replace storage device |
| **High Temperature** | CPU temperature above 80°C (overheating) | Check cooling, ventilation, and system load |

**Troubleshooting Steps for Red LED:**
1. Check system logs: `sudo journalctl -u bathyimager -n 50`
2. Run hardware diagnostics: `./scripts/hardware_diagnostics.sh all`
3. Check USB connections and power
4. Verify disk space: `df -h /media/usb`
5. Restart service: `sudo systemctl restart bathyimager`

#### LED Hardware Setup

```bash
# Basic LED wiring (with current-limiting resistors)
# GPIO 18 (Power) -> 220Ω -> Green LED -> Ground
# GPIO 23 (GPS) -> 220Ω -> Blue LED -> Ground  
# GPIO 24 (Camera) -> 220Ω -> Yellow LED -> Ground
# GPIO 25 (Error) -> 220Ω -> Red LED -> Ground

# For higher brightness or multiple LEDs per function:
# GPIO -> 1kΩ -> NPN Transistor Base
# Transistor Collector -> LED Cathode
# LED Anode -> 3.3V (through appropriate resistor)
# Transistor Emitter -> Ground
```

#### Troubleshooting LED Issues

```bash
# Test LED functionality manually
echo "18" > /sys/class/gpio/export
echo "out" > /sys/class/gpio/gpio18/direction
echo "1" > /sys/class/gpio/gpio18/value  # Turn on
echo "0" > /sys/class/gpio/gpio18/value  # Turn off

# Check GPIO permissions
ls -la /dev/gpiomem
groups bathyimager | grep gpio

# Verify LED initialization in logs
journalctl -u bathyimager | grep -i led
```

### Log Monitoring

```bash
# View real-time logs
sudo journalctl -u bathyimager -f

# View recent logs
sudo journalctl -u bathyimager --since "1 hour ago"

# View log files directly
sudo tail -f /var/log/bathyimager/bathyimager.log

# Check system logs
sudo tail -f /var/log/syslog | grep bathyimager
```

### Performance Monitoring

```bash
# Check service status
sudo systemctl status bathyimager

# Monitor resource usage
sudo htop

# Check disk usage
df -h /media/usb

# View storage statistics
du -sh /media/usb/*
```

## Development Guide

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/Mike-Bollinger/BathyImager-Seabed-Imager.git
cd BathyImager-Seabed-Imager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Set development environment
export BATHYCAT_ENV=development
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/bathycat --cov-report=html

# Run specific test file
python -m pytest tests/test_camera.py

# Run integration tests
python -m pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/bathycat/

# Run all quality checks
./scripts/check-quality.sh
```

### Mock Testing

For development on non-Raspberry Pi systems:

```json
{
  "system": {
    "environment": "development"
  },
  "gps": {
    "mock_enabled": true,
    "mock_latitude": 40.7128,
    "mock_longitude": -74.0060
  },
  "leds": {
    "enabled": false
  }
}
```

### Adding New Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement Changes**
   - Follow existing code patterns
   - Add comprehensive error handling
   - Include logging for debugging
   - Write unit tests

3. **Test Thoroughly**
   - Unit tests for new functionality
   - Integration tests with hardware
   - Mock testing for non-Pi environments

4. **Submit Pull Request**
   - Include test results
   - Document new configuration options
   - Update README if needed

## Troubleshooting

### Common Issues

#### Camera Not Detected

```bash
# Check USB cameras connected
lsusb | grep -i camera

# Check video devices and permissions
ls -la /dev/video*

# Test camera manually with ffplay
ffplay /dev/video0

# Or test with OpenCV
python3 -c "import cv2; cap=cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed')"

# Check user permissions
groups bathyimager | grep video

# Fix permissions if needed
sudo usermod -a -G video bathyimager
sudo ./scripts/setup_device_permissions.sh

# Run camera-specific diagnostics
./scripts/hardware_diagnostics.sh camera
```

#### GPS Not Working

```bash
# Check USB GPS device connected
lsusb | grep -i gps

# Check serial devices and permissions
ls -la /dev/ttyUSB* /dev/ttyACM*

# Test GPS data stream manually
sudo cat /dev/ttyUSB0
# Look for NMEA sentences like: $GPGGA,123519,4807.038,N,01131.000,E...

# Check user permissions
groups bathyimager | grep dialout

# Fix permissions if needed
sudo usermod -a -G dialout bathyimager
sudo ./scripts/setup_device_permissions.sh

# Run GPS-specific diagnostics
./scripts/hardware_diagnostics.sh gps

# Test GPS with Python
python3 -c "
import serial
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=5)
    data = ser.read(100)
    print('GPS data:', data.decode('ascii', errors='ignore'))
    ser.close()
except Exception as e:
    print('GPS error:', e)
"
```

#### GPS Time Synchronization Issues

```bash
# Check for GPS time sync error in logs
sudo journalctl -u bathyimager | grep "Failed to set system time"

# Common error: "Operation not permitted" when setting date
# This indicates sudo privileges are missing for GPS time sync

# Check if GPS time sync sudoers file exists
ls -la /etc/sudoers.d/bathyimager-gps-sync

# Test GPS time sync permissions manually
sudo -u bathyimager sudo -n date

# Fix GPS time sync permissions
sudo ./scripts/setup_device_permissions.sh

# Verify permissions are working
./scripts/hardware_diagnostics.sh permissions

# Check GPS time sync status in logs
sudo journalctl -u bathyimager | grep -E "(GPS time|time sync)"

# Expected behavior after fix:
# - GPS RMC sentences provide accurate time
# - System time automatically synced when GPS fix acquired
# - Images timestamped with GPS-accurate UTC time
# - Status shows 'system_time_synced: true' when GPS synced
```

#### GPS Metadata Not in Images

```bash
# This troubleshooting section helps diagnose why GPS coordinates 
# might not be appearing in image EXIF metadata

# 1. Run comprehensive GPS tagging diagnostic
./scripts/gps_diagnostic.py

# 2. Check GPS fix quality in logs
sudo journalctl -u bathyimager | grep -E "(GPS fix|GPS metadata|coordinates)"

# 3. Manually verify GPS data reception
sudo cat /dev/ttyUSB0 | grep -E "GPGGA|GPRMC"
# Look for valid coordinates in NMEA sentences

# 4. Test image metadata extraction on existing images
python3 -c "
from PIL import Image
import piexif
filepath = '/media/usb/bathyimager/YYYY/MM/DD/{filename_prefix}_YYYYMMDD_HHMMSS.jpg'
with Image.open(filepath) as img:
    exif = piexif.load(img.info.get('exif', b''))
    gps_info = exif.get('GPS', {})
    if gps_info:
        print('GPS EXIF found:', gps_info)
    else:
        print('No GPS EXIF data found')
"

# 5. Check configuration enables metadata
grep -E "(enable_metadata|require_gps_fix)" config/bathyimager_config.json

# 6. Common causes and solutions:
#    - GPS never gets valid fix (< 3 satellites)
#      Solution: Test outdoors with clear sky view
#    - GPS coordinates are 0,0 
#      Solution: Wait longer for GPS acquisition
#    - Metadata disabled in config
#      Solution: Set "enable_metadata": true
#    - GPS fix too strict
#      Solution: Set "require_gps_fix": false
#    - EXIF library errors
#      Solution: Check logs for piexif errors

# 7. Enable more verbose GPS logging temporarily
sudo systemctl stop bathyimager
sudo -u bathyimager LOG_LEVEL=DEBUG ./run_bathyimager.sh
# Watch for GPS fix messages and metadata addition logs
```

#### Camera Auto-Settings Not Working

```bash
# Verify camera auto white balance and exposure are enabled

# 1. Check configuration
grep -E "(auto_exposure|auto_white_balance)" config/bathyimager_config.json
# Should show: "camera_auto_exposure": true, "camera_auto_white_balance": true

# 2. Check logs for camera initialization messages
sudo journalctl -u bathyimager | grep -E "(Camera auto|Actual camera properties)"

# 3. Test camera manually to verify auto settings
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
print('Auto exposure:', cap.get(cv2.CAP_PROP_AUTO_EXPOSURE))
print('Auto WB:', cap.get(cv2.CAP_PROP_AUTO_WB))
cap.release()
"

# 4. Common issues:
#    - USB camera doesn't support auto settings
#      Solution: Check with v4l2-ctl for supported controls
#    - OpenCV version doesn't support properties
#      Solution: Update OpenCV or use manual settings
#    - Camera defaults overriding settings
#      Solution: Power cycle camera or adjust timing

# 5. Verify with v4l2-ctl (if available)
sudo apt install v4l-utils
v4l2-ctl --list-ctrls --device /dev/video0
v4l2-ctl --get-ctrl white_balance_automatic --device /dev/video0
v4l2-ctl --get-ctrl auto_exposure --device /dev/video0
```

#### Storage Issues

```bash
# Check USB storage
lsblk

# Check mount status
mount | grep usb

# Manual mount
sudo mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Check disk space
df -h /media/usb
```

#### Service Not Starting

```bash
# Check service status and recent failures
sudo systemctl status bathyimager

# View detailed logs (last 50 lines)
sudo journalctl -u bathyimager -n 50

# View live logs
sudo journalctl -u bathyimager -f

# Check device permissions and hardware
./scripts/hardware_diagnostics.sh permissions

# Test system manually
cd ~/BathyCat-Seabed-Imager
sudo -u bathyimager ./run_bathyimager.sh

# Reinstall/update service configuration
sudo ./scripts/install.sh --update

# Reset device permissions
sudo ./scripts/setup_device_permissions.sh
```

#### Network Connectivity Issues

```bash
# Check network status
./scripts/network_status.sh

# Test connectivity
./scripts/network_test.sh

# Both interfaces down
sudo ip link set eth0 up
sudo ip link set wlan0 up
sudo systemctl restart dhcpcd

# WiFi not connecting  
sudo ./scripts/wifi_config.sh

# Wrong interface priority
sudo systemctl restart dhcpcd

# No internet despite connection
sudo systemctl restart dhcpcd wpa_supplicant@wlan0

# Check for NetworkManager conflicts
sudo systemctl disable NetworkManager
sudo systemctl stop NetworkManager
```

#### Device Permission Issues

```bash
# Run comprehensive permission diagnostics
./scripts/hardware_diagnostics.sh permissions

# Check user group membership
groups bathyimager

# Add user to required groups (if missing)
sudo usermod -a -G video,dialout,gpio bathyimager

# Reset device permissions manually
sudo ./scripts/setup_device_permissions.sh

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Check if devices have correct permissions
ls -la /dev/video* /dev/ttyUSB* /dev/ttyACM* /dev/gpiomem

# If still having issues, reinstall service with updated permissions
sudo ./scripts/install.sh --update
```

#### LED Not Working

```bash
# Check if LEDs are enabled in configuration
grep -A5 "led" ~/BathyCat-Seabed-Imager/config/bathycat_config.json

# Check GPIO permissions
ls -la /dev/gpiomem
groups bathyimager | grep gpio

# Test LED manually (as root)
echo 18 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio18/direction
echo 1 > /sys/class/gpio/gpio18/value  # Should turn on LED on GPIO 18
echo 0 > /sys/class/gpio/gpio18/value  # Should turn off LED
```

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| E001 | Camera initialization failed | Check camera connection and permissions |
| E002 | GPS timeout | Check GPS device and antenna |
| E003 | Storage unavailable | Check USB drive connection |
| E004 | Configuration invalid | Fix configuration file |
| E005 | Insufficient disk space | Clean storage or add capacity |
| E006 | Device permission denied | Run setup_device_permissions.sh |
| E007 | Service startup failed | Check journalctl logs and hardware diagnostics |
| E008 | Hardware not detected | Check USB connections and device power |

### Recovery Procedures

#### Service Recovery

```bash
# Restart service
sudo systemctl restart bathyimager

# Reset configuration
cd /opt/bathycat/src && sudo python3 -m config --create-default

# Factory reset
sudo ./scripts/install.sh --reset
```

#### Hardware Reset

```bash
# Reset USB devices
sudo lsusb | grep -E "(camera|gps)" | cut -d' ' -f6 | \
while read device; do
    echo "Resetting $device"
    sudo usb_modeswitch -v ${device%:*} -p ${device#*:} --reset-usb
done
```

## Maintenance

### Configuration Management

```bash
# View current configuration
cat ~/BathyCat-Seabed-Imager/config/bathycat_config.json

# Edit configuration (requires service restart to apply)
nano ~/BathyCat-Seabed-Imager/config/bathycat_config.json

# Apply configuration changes
sudo systemctl restart bathyimager

# Backup current configuration
cp ~/BathyCat-Seabed-Imager/config/bathycat_config.json ~/config_backup.json

# Restore configuration from backup
cp ~/config_backup.json ~/BathyCat-Seabed-Imager/config/bathycat_config.json
sudo systemctl restart bathyimager
```

### Regular Maintenance Tasks

```bash
# Weekly: Check system health and hardware status
./scripts/hardware_diagnostics.sh all

# Weekly: Check storage usage and image count
du -sh /media/usb/bathyimager/*
ls /media/usb/bathyimager/images/$(date +%Y%m%d)/ | wc -l  # Today's image count

# Weekly: Check service logs for errors
sudo journalctl -u bathyimager --since "7 days ago" | grep -i error

# Monthly: Update system software
cd ~/BathyCat-Seabed-Imager
./update
sudo ./scripts/install.sh --update

# Monthly: Clean old logs (keep 30 days)
sudo journalctl --vacuum-time=30d

# Monthly: Check and clean old images if storage getting full
df -h /media/usb  # Check free space
# Manual cleanup if needed:
# find /media/usb/bathyimager -name "*.jpg" -mtime +60 -delete

# As needed: Restart service if any issues
sudo systemctl restart bathyimager
```

### Update System

```bash
# Quick update from GitHub (recommended)
cd ~/BathyCat-Seabed-Imager
./update

# Update with automatic stashing of local changes
./update --stash

# Force update (discards local changes)
./update --force

# After update, reinstall/update service configuration
sudo ./scripts/install.sh --update

# Check if service needs restart
sudo systemctl status bathyimager
sudo systemctl restart bathyimager  # if needed
```

### Backup and Recovery

```bash
# Backup configuration
sudo cp /etc/bathycat/config.json ~/config.json.backup

# Backup images (to external drive)
rsync -av /media/usb/ /external/backup/

# System backup (if needed)
sudo dd if=/dev/mmcblk0 of=/external/system-backup.img bs=4M
```

## API Reference

### Main Components

#### BathyCatService

```python
from main import BathyCatService

service = BathyCatService(config_path='/etc/bathycat/config.json')
service.start()  # Start all subsystems
service.stop()   # Graceful shutdown
```

#### Camera

```python
from camera import Camera

camera = Camera(config)
camera.initialize()
frame = camera.capture_frame()
camera.close()
```

#### GPS

```python
from gps import GPS

gps = GPS(config)
gps.connect()
fix = gps.wait_for_fix(timeout=30)
gps.disconnect()
```

#### Configuration

```python
from config import ConfigManager

manager = ConfigManager('/etc/bathycat/config.json')
config = manager.load_config()
manager.save_config(config)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

### Development Standards

- Python 3.7+ compatibility
- Type hints for all functions
- Comprehensive error handling
- Unit tests with >90% coverage
- Clear documentation and comments
- Follow PEP 8 style guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: GitHub Issues
- **Documentation**: This README and inline code documentation
- **Discussions**: GitHub Discussions

## Quick Reference

### Essential Commands

```bash
# System Status
sudo systemctl status bathyimager              # Check service status
sudo journalctl -u bathyimager -f             # View live logs
./scripts/hardware_diagnostics.sh all         # Check hardware health

# System Control  
sudo systemctl start bathyimager              # Start imaging
sudo systemctl stop bathyimager               # Stop imaging
sudo systemctl restart bathyimager            # Restart (apply config changes)
sudo systemctl enable bathyimager             # Enable auto-start on boot

# Manual Operation
cd ~/BathyCat-Seabed-Imager && ./run_bathyimager.sh   # Run manually

# Troubleshooting
./scripts/hardware_diagnostics.sh permissions  # Check device permissions
sudo ./scripts/setup_device_permissions.sh    # Fix permission issues
sudo ./scripts/install.sh --update            # Reinstall/update service

# Updates and Maintenance
cd ~/BathyCat-Seabed-Imager && ./update      # Update software
du -sh /media/usb/bathyimager/*              # Check storage usage
sudo journalctl --vacuum-time=30d            # Clean old logs
```

### File Locations

```bash
# Main installation
~/BathyCat-Seabed-Imager/                     # Project directory
~/BathyCat-Seabed-Imager/config/bathycat_config.json  # Configuration

# System files
/etc/systemd/system/bathyimager.service       # Service definition
/etc/udev/rules.d/99-bathyimager.rules       # Device permissions

# Data and logs
/media/usb/bathyimager/                       # Image storage
/var/log/bathyimager/                         # Log files
```

### LED Status Quick Reference

- **Green LED (GPIO 18)**: Solid = Running, Off = Stopped  
- **Blue LED (GPIO 23)**: Solid = GPS Fix, Blink = Searching, Off = No GPS
- **Yellow LED (GPIO 24)**: Flash = Photo Taken, SOS = Camera Error
- **Red LED (GPIO 25)**: Off = No Errors, Blink = Warning/Error

## Acknowledgments

- Raspberry Pi Foundation for the excellent hardware platform
- OpenCV community for computer vision libraries
- Python GPS community for NMEA parsing tools