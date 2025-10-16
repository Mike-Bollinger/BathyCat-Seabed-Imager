# BathyCat Seabed Imager

An autonomous seabed imaging system for surface vessels, capturing geotagged images and storing them on USB drives.

## Project Overview

The BathyCat Seabed Imager is designed to run on autonomous surface vessels (ASVs) to capture continuous imagery of the seabed. The system uses a downward-facing camera, integrates GPS coordinates into image metadata, and stores everything on external USB storage for later analysis.

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

## Quick Start

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

# Run the installation script
sudo ./scripts/install.sh

# The installer will:
# - Update the system
# - Install required packages
# - Set up Python environment
# - Configure the service
# - Set up USB auto-mounting
# - Configure log rotation
```

### 2. Configuration

```bash
# Create default configuration
cd /opt/bathycat/src && sudo python3 -m config --create-default

# Edit configuration if needed
sudo nano /etc/bathycat/config.json

# Validate configuration
cd /opt/bathycat/src && sudo python3 -m config --validate
```

### 3. Network Configuration (Dual Ethernet + WiFi)

BathyCat supports simultaneous Ethernet and WiFi connectivity for maximum reliability:

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

### 4. Service Management

```bash
# Start the service
sudo systemctl start bathyimager

# Check status
sudo systemctl status bathyimager

# View logs
sudo journalctl -u bathyimager -f

# Enable auto-start on boot
sudo systemctl enable bathyimager
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
/opt/bathycat/              # Installation directory
├── src/                    # Source code
├── scripts/                # Installation and maintenance scripts
├── venv/                   # Python virtual environment
├── VERSION                 # Version information
└── backups/               # Update backups

/etc/bathycat/             # Configuration directory
└── config.json            # Main configuration file

/var/log/bathycat/         # Log directory
├── bathycat.log           # Application logs
└── system.log             # System-level logs

/media/usb/                # Default USB storage
└── YYYY/MM/DD/            # Date-based organization
    └── bathycat_*.jpg     # Geotagged images
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
    "max_images_per_day": 10000,            # Daily image limit
    "cleanup_days": 30,                     # Delete files older than N days
    "min_free_space_mb": 1000,              # Minimum free space (MB)
    "directory_structure": "%Y/%m/%d",      # Date-based folders
    "filename_format": "bathycat_%Y%m%d_%H%M%S_{counter:04d}.jpg"
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

### Normal Operation

1. **System Startup**
   - Service starts automatically on boot
   - LED test sequence (if enabled)
   - Hardware initialization and health checks
   - GPS fix acquisition
   - Image capture begins when GPS lock obtained

2. **Image Capture Process**
   - Continuous capture at configured interval
   - GPS coordinates embedded in EXIF metadata
   - Images saved with timestamp-based naming
   - Status indicated via LEDs and logs

3. **Storage Management**
   - Automatic directory creation by date
   - File cleanup when storage limits reached
   - USB device monitoring and remounting

### LED Status Indicators

| LED | Pattern | Meaning |
|-----|---------|---------|
| Status (Green) | Solid | System running normally |
| Status (Green) | Slow blink | Starting up / GPS acquiring |
| Error (Red) | Off | No errors |
| Error (Red) | Solid | Critical error |
| Error (Red) | Fast blink | Warning condition |
| Activity (Blue) | Blink | Image captured |

### Log Monitoring

```bash
# View real-time logs
sudo journalctl -u bathycat -f

# View recent logs
sudo journalctl -u bathycat --since "1 hour ago"

# View log files directly
sudo tail -f /var/log/bathycat/bathycat.log

# Check system logs
sudo tail -f /var/log/syslog | grep bathycat
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
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

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
# Check USB cameras
lsusb | grep -i camera

# Check video devices
ls -la /dev/video*

# Test camera manually
ffplay /dev/video0

# Check permissions
sudo usermod -a -G video pi
```

#### GPS Not Working

```bash
# Check USB GPS device
lsusb | grep -i gps

# Check serial devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# Test GPS manually
sudo cat /dev/ttyUSB0

# Check permissions
sudo usermod -a -G dialout pi
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
# Check service status
sudo systemctl status bathyimager

# View detailed logs
sudo journalctl -u bathyimager -n 50

# Check configuration
cd /opt/bathycat/src && sudo python3 -m config --validate

# Test manually
cd /opt/bathycat/src
sudo -u pi ../venv/bin/python -m main
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

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| E001 | Camera initialization failed | Check camera connection and permissions |
| E002 | GPS timeout | Check GPS device and antenna |
| E003 | Storage unavailable | Check USB drive connection |
| E004 | Configuration invalid | Fix configuration file |
| E005 | Insufficient disk space | Clean storage or add capacity |
| E006 | Network connectivity lost | Check network configuration |
| E007 | Ethernet interface down | Check cable and interface status |
| E008 | WiFi authentication failed | Verify WiFi credentials |

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

### Regular Maintenance Tasks

```bash
# Check system health (weekly)
sudo ./scripts/health-check.sh

# Update system (monthly)
sudo ./scripts/bathycat-update --check
sudo ./scripts/bathycat-update

# Clean old logs (monthly)
sudo journalctl --vacuum-time=30d

# Check storage usage (weekly)
du -sh /media/usb/*
```

### Update System

```bash
# Check for updates
sudo ./scripts/bathycat-update --check

# Perform update
sudo ./scripts/bathycat-update

# Force update
sudo ./scripts/bathycat-update --force

# Show version information
sudo ./scripts/bathycat-update --version
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

## Acknowledgments

- Raspberry Pi Foundation for the excellent hardware platform
- OpenCV community for computer vision libraries
- Python GPS community for NMEA parsing tools