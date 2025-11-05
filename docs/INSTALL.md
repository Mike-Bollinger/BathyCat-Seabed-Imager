# BathyCat Seabed Imager Installation Guide

Complete installation guide for the BathyCat Seabed Imager - an autonomous underwater imaging system designed for surface vessels on shallow water surveys.

## System Overview

The BathyCat Seabed Imager captures geotagged images at high precision timing for underwater surveys. Recent optimizations include:

- **⚡ Precision Timing**: <10ms timestamp accuracy for 2 m/s vehicle deployment
- **📊 Date-Stamped Logging**: USB storage with daily log rotation
- **🚀 Smart Updates**: Intelligent dependency management  
- **🛠️ Unified Diagnostics**: Comprehensive troubleshooting framework

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 4 Model B** (4GB RAM recommended)
- **MicroSD card** (32GB+ Class 10 or better) 
- **DWE StellarHD USB Camera** (1080p@30fps capable)
- **Adafruit Ultimate GPS - USB Version** (or compatible GPS module)
- **USB 3.0 flash drive** (512GB+ recommended for extended deployments)
- **Status LEDs** (optional - GPIO pins 18, 23, 24, 25)

### Software Requirements
- **Raspberry Pi OS** (Bullseye 64-bit or later recommended)
- **Internet connection** for initial setup and package installation
- **SSH access** (recommended for headless deployment setup)

## Installation Methods

### Method 1: Automated Installation (Recommended)

#### Step 1: Prepare Raspberry Pi
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install git curl wget -y

# Verify hardware connections (connect hardware first!)
lsusb                               # Should show camera and GPS
ls /dev/video* 2>/dev/null || echo "No camera detected"
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No GPS detected"
```

#### Step 2: Clone Repository
```bash
# Clone the BathyCat repository
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

# Verify installation scripts
ls scripts/install.sh              # Main installer
ls tests/troubleshoot.py           # Diagnostic tools
```

#### Step 3: Run Comprehensive Installation
```bash
# Make installer executable and run with full installation
chmod +x scripts/install.sh
sudo ./scripts/install.sh

# The installer performs:
# ✅ System package installation (OpenCV, Python, GPS tools)
# ✅ User account creation with proper permissions
# ✅ Python virtual environment setup
# ✅ Package dependency installation  
# ✅ Systemd service configuration
# ✅ USB auto-mounting setup
# ✅ Date-stamped logging configuration
# ✅ Hardware permission rules
# ✅ Initial system validation tests
```

#### Step 4: Configure for Your Hardware
```bash
# Edit main configuration file
nano config/bathyimager_config.json

# Verify hardware detection
./tests/troubleshoot.py --quick
```

**Essential Configuration Settings:**
```json
{
  "camera": {
    "device_index": 0,                    # Usually 0, check with: ls /dev/video*
    "resolution_width": 1920,
    "resolution_height": 1080,
    "capture_interval": 1.0               # Seconds between captures
  },
  "gps": {
    "port": "/dev/ttyUSB0",               # Check with: ls /dev/ttyUSB* /dev/ttyACM*
    "baudrate": 9600,
    "require_gps_fix": true,              # Set false for indoor testing
    "mock_mode": false                    # Set true for testing without GPS
  },
  "storage": {
    "base_path": "/media/usb/bathyimager", # USB mount point
    "use_date_folders": true,             # Creates YYYYMMDD directories
    "cleanup_days": 30                    # Auto-cleanup after 30 days
  },
  "logging": {
    "log_to_file": true,
    "log_file_path": "/media/usb/bathyimager/logs", # Date-stamped logging
    "log_level": "INFO"
  }
}
```

#### Step 5: Validate and Start System
```bash
# Run comprehensive system diagnostic
python3 tests/troubleshoot.py

# Start the imaging service
sudo systemctl start bathyimager

# Enable auto-start on boot (for production deployment)
sudo systemctl enable bathyimager

# Check service status
sudo systemctl status bathyimager

# Monitor real-time operation
sudo journalctl -u bathyimager -f
```

#### Step 6: Verify Operation
```bash
# Check LED indicators (if connected):
# - Green (GPIO 18): Solid = system running
# - Blue (GPIO 23): Solid = GPS fix acquired  
# - Yellow (GPIO 24): Blinks = images captured
# - Red (GPIO 25): Off = no errors

# Verify image capture
ls -la /media/usb/bathyimager/images/$(date +%Y%m%d)/

# Check log files
ls -la /media/usb/bathyimager/logs/$(date +%Y%m%d)/

# Run performance check
python3 tests/performance_analyzer.py --quick
```

### Method 2: Manual Installation (Advanced Users)

Use this method if you need custom installation paths or modifications.

#### 1. System Dependencies
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install core system packages
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    git cmake build-essential pkg-config \
    libjpeg-dev libtiff5-dev libpng-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev libxvidcore-dev libx264-dev \
    libgtk-3-dev libatlas-base-dev gfortran \
    usbutils gpsd gpsd-clients \
    udisks2 ntfs-3g exfat-fuse

# Install OpenCV dependencies for hardware acceleration
sudo apt install -y \
    libopencv-dev libopencv-contrib-dev \
    libblas-dev liblapack-dev libhdf5-dev
```

#### 2. User and Directory Setup
```bash
# Create bathyimager system user
sudo useradd -r -m -d /home/bathyimager -s /bin/bash bathyimager

# Add user to required groups for hardware access
sudo usermod -a -G video,dialout,plugdev,gpio bathyimager

# Create system directories
sudo mkdir -p /opt/bathyimager
sudo mkdir -p /var/log/bathyimager
sudo chown bathyimager:bathyimager /var/log/bathyimager
```

#### 3. Install BathyCat Source Code
```bash
# Clone repository to installation directory
cd /opt
sudo git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git bathyimager
sudo chown -R bathyimager:bathyimager /opt/bathyimager

# Switch to bathyimager user for setup
sudo -u bathyimager bash
cd /opt/bathyimager
```

#### 4. Python Environment Setup
```bash
# Create optimized virtual environment
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install Python packages with optimizations
pip install --upgrade pip setuptools wheel

# Install core dependencies
pip install opencv-python pynmea2 Pillow piexif pyserial

# Install GPIO library (Raspberry Pi only)
pip install RPi.GPIO

# Verify installation
python3 -c "import cv2, pynmea2, PIL; print('All packages installed successfully')"
```

#### 5. System Service Configuration
```bash
# Copy service file to systemd
sudo cp scripts/bathyimager.service /etc/systemd/system/

# Copy udev rules for hardware permissions  
sudo cp scripts/99-bathyimager.rules /etc/udev/rules.d/

# Reload systemd and udev
sudo systemctl daemon-reload
sudo udevadm control --reload-rules && sudo udevadm trigger

# Configure USB auto-mounting
sudo cp scripts/mount_usb.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/mount_usb.sh
```

#### 6. Configuration Setup
```bash
# Create default configuration
mkdir -p config
cp config/bathyimager_config.json.example config/bathyimager_config.json

# Edit configuration for your hardware
nano config/bathyimager_config.json

# Validate configuration
python3 src/config.py --validate
```

#### 7. Enable and Test Service
```bash
# Enable service for auto-start
sudo systemctl enable bathyimager

# Start service
sudo systemctl start bathyimager

# Check status
sudo systemctl status bathyimager

# Test diagnostics
python3 tests/troubleshoot.py --quick
```

## Hardware Setup and Verification

### 1. Camera Setup
```bash
# Connect DWE StellarHD USB camera to USB 3.0 port (blue connector)
# Verify camera detection
lsusb | grep -i camera
ls -la /dev/video*

# Test camera functionality
python3 tests/camera_troubleshoot.py

# Expected output: /dev/video0 (or similar)
# Test capture: ffplay /dev/video0 (if available)
```

### 2. GPS Module Setup
```bash
# Connect Adafruit Ultimate GPS USB to USB port
# Verify GPS detection
lsusb | grep -E "(GPS|Adafruit|Prolific)"
ls -la /dev/ttyUSB* /dev/ttyACM*

# Test GPS functionality
python3 tests/gps_troubleshoot.py

# Monitor GPS data (should show NMEA sentences)
sudo cat /dev/ttyUSB0    # or /dev/ttyACM0
```

### 3. USB Storage Setup
```bash
# Prepare USB drive (512GB+ recommended for long deployments)
# Format as exFAT for cross-platform compatibility:
sudo mkfs.exfat -n "BATHYIMAGER" /dev/sdX1    # Replace X with your drive letter

# OR format as ext4 for Linux-only use:
sudo mkfs.ext4 -L "BATHYIMAGER" /dev/sdX1

# Test auto-mounting
# Unplug and replug USB drive, should appear at /media/usb/
df -h | grep usb
```

### 4. LED Status Indicators (Optional but Recommended)
Connect LEDs with 220Ω resistors to GPIO pins:

| LED Function | GPIO Pin | Physical Pin | Color | Purpose |
|-------------|----------|--------------|-------|---------|
| Power/Status | 18 | 12 | Green | System running normally |
| GPS Status | 23 | 16 | Blue | GPS fix acquired |
| Camera Activity | 24 | 18 | Yellow | Image capture indicator |
| Error Status | 25 | 22 | Red | System errors |

**LED Wiring:**
```
GPIO Pin → 220Ω Resistor → LED Anode (+)
LED Cathode (-) → Ground (GND)
```

### 5. Hardware Validation
```bash
# Run comprehensive hardware diagnostic
python3 tests/troubleshoot.py --component all

# Quick hardware check
python3 tests/system_health_check.py

# Performance benchmark
python3 tests/performance_analyzer.py --benchmark
```

## Configuration

### Main Configuration File
Edit `config/bathyimager_config.json` to match your hardware setup:

```json
{
  "camera": {
    "device_index": 0,
    "backend": "any",
    "resolution_width": 1920,
    "resolution_height": 1080,
    "fps": 30,
    "jpeg_quality": 95,
    "capture_interval": 1.0,
    "timeout_seconds": 5.0
  },
  "gps": {
    "port": "/dev/ttyUSB0",
    "baudrate": 9600,
    "timeout": 1.0,
    "require_gps_fix": true,
    "mock_mode": false,
    "mock_latitude": 40.7128,
    "mock_longitude": -74.0060
  },
  "storage": {
    "base_path": "/media/usb/bathyimager",
    "use_date_folders": true,
    "cleanup_enabled": true,
    "cleanup_days": 30,
    "min_free_space_mb": 1000
  },
  "logging": {
    "log_to_file": true,
    "log_file_path": "/media/usb/bathyimager/logs",
    "log_level": "INFO",
    "log_max_size_mb": 100,
    "log_backup_count": 5
  },
  "led_power_pin": 18,
  "led_gps_pin": 23,
  "led_camera_pin": 24,
  "led_error_pin": 25,
  "performance_monitoring": true,
  "timing_precision_mode": true
}
```

### Configuration Profiles

#### Development/Testing Environment
```json
{
  "camera": {
    "capture_interval": 5.0,
    "timeout_seconds": 10.0
  },
  "gps": {
    "require_gps_fix": false,
    "mock_mode": true
  },
  "logging": {
    "log_level": "DEBUG"
  },
  "performance_monitoring": true
}
```

#### Production Deployment
```json
{
  "camera": {
    "capture_interval": 1.0,
    "jpeg_quality": 95
  },
  "gps": {
    "require_gps_fix": true,
    "mock_mode": false
  },
  "storage": {
    "cleanup_enabled": true,
    "cleanup_days": 30
  },
  "logging": {
    "log_level": "INFO"
  },
  "timing_precision_mode": true
}
```

#### High-Speed Survey Mode
```json
{
  "camera": {
    "capture_interval": 0.5,
    "jpeg_quality": 85,
    "fps": 30
  },
  "storage": {
    "cleanup_days": 14,
    "min_free_space_mb": 2000
  },
  "timing_precision_mode": true
}
```

### Configuration Validation
```bash
# Validate configuration syntax and hardware compatibility
python3 tests/troubleshoot.py --config-check

# Test specific configuration sections
python3 tests/camera_troubleshoot.py --config-test
python3 tests/gps_troubleshoot.py --config-test

# Generate hardware-specific configuration
python3 src/config.py --detect-hardware --output config/detected_config.json
  }
}
```

## Installation Testing and Validation

### Quick Installation Verification
```bash
# Run comprehensive installation test
python3 tests/troubleshoot.py

# Quick health check (30 seconds)
python3 tests/troubleshoot.py --quick

# Component-specific tests
python3 tests/troubleshoot.py --component camera
python3 tests/troubleshoot.py --component gps
python3 tests/troubleshoot.py --component storage
```

### Individual Hardware Tests
```bash
# Camera system diagnostics
python3 tests/camera_troubleshoot.py --detailed
# Expected: Camera detection, resolution test, capture validation

# GPS system diagnostics  
python3 tests/gps_troubleshoot.py --detailed
# Expected: NMEA sentence parsing, coordinate validation, timing sync

# System health analysis
python3 tests/system_health_check.py
# Expected: Service status, memory usage, performance metrics

# Performance benchmarking
python3 tests/performance_analyzer.py --benchmark
# Expected: Timing analysis, throughput measurements
```

### Service Operation Tests
```bash
# Check systemd service status
sudo systemctl status bathyimager

# Monitor real-time logs with automatic log rotation
sudo journalctl -u bathyimager -f

# Test service start/stop
sudo systemctl stop bathyimager
sudo systemctl start bathyimager

# Manual operation test (bypass systemd)
cd /opt/bathyimager
source venv/bin/activate
python3 src/main.py --config config/bathyimager_config.json
```

### Storage and Logging Tests
```bash
# Test date-stamped directory creation
python3 tests/test_dated_logging.py

# Verify USB storage mounting
df -h /media/usb/bathyimager
ls -la /media/usb/bathyimager/

# Check log file structure
ls -la /media/usb/bathyimager/logs/$(date +%Y%m%d)/

# Test image capture and storage
ls -la /media/usb/bathyimager/images/$(date +%Y%m%d)/
```

### Network and Updates
```bash
# Test network connectivity (if configured)
./tests/network_test.sh

# Test update system
./update --check-only

# Validate all system dependencies
python3 tests/system_validation.py
```

### Expected Test Results
✅ **Successful installation shows:**
- All hardware components detected and functional
- Service running without errors (green status LED solid)
- Images being captured and stored with GPS coordinates
- Logs being written to date-stamped directories
- Performance metrics within normal ranges (1-2 second capture intervals)
- All diagnostic tests passing

❌ **Common installation issues:**
- Camera permission errors → Run: `sudo usermod -a -G video bathyimager`
- GPS not detected → Check USB connection and run: `python3 tests/gps_troubleshoot.py`
- USB storage not mounting → Run: `sudo ./scripts/mount_usb.sh`
- Service fails to start → Run: `python3 tests/troubleshoot.py` for diagnosis

## Installation Troubleshooting

### Automated Troubleshooting
```bash
# First step: Run comprehensive diagnostics
python3 tests/troubleshoot.py

# For specific issues, use targeted diagnostics:
python3 tests/troubleshoot.py --component camera     # Camera issues
python3 tests/troubleshoot.py --component gps       # GPS issues  
python3 tests/troubleshoot.py --component storage   # Storage issues
python3 tests/troubleshoot.py --network            # Network issues
```

### Common Installation Issues

#### 1. Permission and User Account Issues
```bash
# The automated diagnostic will show permission errors
python3 tests/system_health_check.py

# Fix user permissions
sudo usermod -a -G video,dialout,plugdev,gpio bathyimager
sudo usermod -a -G video,dialout,plugdev,gpio pi

# Fix directory ownership
sudo chown -R bathyimager:bathyimager /opt/bathyimager
sudo chown -R bathyimager:bathyimager /var/log/bathyimager

# Verify permissions
python3 tests/troubleshoot.py --quick
```

#### 2. Camera Hardware Issues
```bash
# Diagnose camera problems
python3 tests/camera_troubleshoot.py --detailed

# Common fixes:
# - Check USB connection (use USB 3.0 port if available)
# - Verify camera power draw (use powered USB hub if needed)
# - Test different backends: V4L2, GStreamer, FFmpeg

# Manual camera test
lsusb | grep -i camera
ls -la /dev/video*
v4l2-ctl --list-devices    # If available
```

#### 3. GPS Connection Problems
```bash
# Diagnose GPS issues
python3 tests/gps_troubleshoot.py --detailed

# Common GPS issues:
# - Wrong device path (/dev/ttyUSB0 vs /dev/ttyACM0)
# - Incorrect baud rate (usually 9600)
# - USB power issues
# - GPS needs clear sky view for initial fix

# Manual GPS troubleshooting
lsusb | grep -E "(GPS|Prolific|FTDI)"
dmesg | grep -i "usb.*gps"
sudo cat /dev/ttyUSB0    # Should show NMEA sentences
```

#### 4. Python Environment Issues
```bash
# Check Python environment
source /opt/bathyimager/venv/bin/activate
python3 -c "import cv2, pynmea2, PIL; print('All imports successful')"

# Reinstall dependencies if needed
cd /opt/bathyimager
pip install --upgrade pip
pip install -r requirements.txt

# Verify OpenCV installation
python3 -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
```

#### 5. Service and Systemd Issues
```bash
# Check service configuration
sudo systemctl status bathyimager
sudo journalctl -u bathyimager --since "1 hour ago"

# Reload service configuration
sudo systemctl daemon-reload
sudo systemctl restart bathyimager

# Test service manually
sudo systemctl stop bathyimager
cd /opt/bathyimager
sudo -u bathyimager ./venv/bin/python src/main.py --config config/bathyimager_config.json
```

#### 6. USB Storage and Mounting Issues
```bash
# Diagnose storage problems
df -h
lsblk
mount | grep usb

# Fix USB mounting
sudo mkdir -p /media/usb
sudo ./scripts/mount_usb.sh

# Check storage permissions
ls -la /media/usb/bathyimager/
sudo chown -R bathyimager:bathyimager /media/usb/bathyimager/
```

### Advanced Troubleshooting

#### Performance Issues
```bash
# Analyze system performance
python3 tests/performance_analyzer.py --monitor --duration 60

# Check system resources
htop    # Or: python3 tests/system_health_check.py

# Monitor timing precision
python3 tests/performance_analyzer.py --timing-analysis
```

#### Configuration Problems
```bash
# Validate configuration
python3 src/config.py --validate --verbose

# Generate hardware-specific config
python3 src/config.py --detect-hardware

# Test configuration sections
python3 tests/troubleshoot.py --config-check
```

#### Network and Updates
```bash
# Test network connectivity
./tests/network_test.sh

# Check update system
./update --check-only --verbose

# Validate dependencies
python3 tests/system_validation.py
```

### Recovery Procedures

#### Configuration Reset
```bash
# Backup current configuration
cp config/bathyimager_config.json config/bathyimager_config.json.backup

# Generate new default configuration
python3 src/config.py --create-default --output config/bathyimager_config.json

# Validate new configuration
python3 tests/troubleshoot.py --config-check

# Restart service with new configuration
sudo systemctl restart bathyimager
```

#### Service Reinstallation
```bash
# Stop service safely
sudo systemctl stop bathyimager
sudo systemctl disable bathyimager

# Reinstall service files
sudo cp scripts/bathyimager.service /etc/systemd/system/
sudo cp scripts/99-bathyimager.rules /etc/udev/rules.d/

# Reload system configuration
sudo systemctl daemon-reload
sudo udevadm control --reload-rules

# Re-enable and start service
sudo systemctl enable bathyimager
sudo systemctl start bathyimager

# Verify operation
python3 tests/troubleshoot.py --quick
```

#### Complete System Reset
```bash
# Full reinstallation (preserves data but resets configuration)
sudo ./scripts/install.sh --reset

# Nuclear option: Complete clean installation
sudo rm -rf /opt/bathyimager
sudo userdel bathyimager
sudo systemctl disable bathyimager
sudo rm /etc/systemd/system/bathyimager.service
# Then run fresh installation
```

## Post-Installation Setup

### 1. Production Configuration
```bash
# Configure for your deployment environment
nano config/bathyimager_config.json

# Key production settings:
# - Set "require_gps_fix": true
# - Adjust "capture_interval" for survey speed
# - Configure "cleanup_days" for storage management
# - Set appropriate "log_level" (INFO for production)
```

### 2. System Optimization
```bash
# Run performance optimization
python3 tests/performance_analyzer.py --optimize

# Enable timing precision mode
# Edit config: "timing_precision_mode": true

# Monitor performance for first deployment
python3 tests/performance_analyzer.py --monitor --duration 300
```

### 3. Remote Monitoring Setup
```bash
# Configure SSH access for remote monitoring
sudo systemctl enable ssh

# Set up log monitoring
# Logs are automatically written to: /media/usb/bathyimager/logs/YYYYMMDD/

# Monitor system status remotely
python3 tests/system_health_check.py --json    # Machine-readable output
```

### 4. Deployment Validation
```bash
# Final pre-deployment check
python3 tests/troubleshoot.py --deployment-check

# Test complete capture pipeline
python3 tests/performance_analyzer.py --pipeline-test

# Verify storage capacity for planned deployment
python3 tests/troubleshoot.py --storage-analysis
```

## Maintenance and Updates

### Regular Maintenance
```bash
# Update system (smart dependency checking)
./update

# Check system health monthly
python3 tests/system_health_check.py --full-report

# Clean old data (if not using automatic cleanup)
python3 src/storage.py --cleanup --older-than 30
```

### Performance Monitoring
```bash
# Monitor timing precision during deployment
python3 tests/performance_analyzer.py --timing-monitor

# Check storage usage
df -h /media/usb/bathyimager/

# Analyze capture statistics
python3 tests/performance_analyzer.py --analyze-logs
```

## Support Resources

### Documentation
- **README.md**: Complete system overview and usage guide
- **docs/TROUBLESHOOTING.md**: Detailed troubleshooting procedures
- **docs/NETWORK_SETUP.md**: Network configuration and connectivity
- **docs/LOGGING_SYSTEM.md**: Date-stamped logging system details

### Diagnostic Tools
- **tests/troubleshoot.py**: Master diagnostic tool
- **tests/system_health_check.py**: System monitoring and analysis
- **tests/performance_analyzer.py**: Performance monitoring and optimization
- **Component-specific diagnostics**: camera_troubleshoot.py, gps_troubleshoot.py

### Getting Help
- **GitHub Issues**: https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/issues
- **System Logs**: Always check `/media/usb/bathyimager/logs/YYYYMMDD/` for troubleshooting
- **Diagnostic Output**: Run `python3 tests/troubleshoot.py` and include output with support requests

### Success Indicators
✅ **Installation successful when:**
- Service status shows "active (running)"
- LEDs indicate normal operation (green solid, blue solid when GPS locked)
- Images being captured to dated directories with GPS coordinates
- Performance metrics show <2 second capture intervals
- All diagnostic tests pass without errors