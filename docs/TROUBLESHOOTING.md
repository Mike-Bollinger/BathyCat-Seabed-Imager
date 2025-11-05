# BathyCat Seabed Imager Troubleshooting Guide

Comprehensive troubleshooting guide for the BathyCat Seabed Imager system with automated diagnostics and solutions.

## 🚀 Quick Start - Automated Troubleshooting

### Master Diagnostic Tool (Start Here)
```bash
# Run comprehensive system diagnostics
python3 tests/troubleshoot.py

# Quick 30-second health check
python3 tests/troubleshoot.py --quick

# Component-specific diagnostics
python3 tests/troubleshoot.py --component camera
python3 tests/troubleshoot.py --component gps
python3 tests/troubleshoot.py --component storage
python3 tests/troubleshoot.py --network
```

### System Health Analysis
```bash
# Comprehensive system status and performance
python3 tests/system_health_check.py

# Performance monitoring and analysis
python3 tests/performance_analyzer.py --analyze

# Real-time system monitoring
python3 tests/performance_analyzer.py --monitor --duration 60
```

### Quick Status Checks
```bash
# Service and system status
sudo systemctl status bathyimager

# Recent system logs (date-stamped logging)
sudo journalctl -u bathyimager --since "1 hour ago"

# Hardware and configuration validation
python3 tests/troubleshoot.py --config-check

# Storage and disk usage
df -h /media/usb/bathyimager/
```

### 🚨 LED Status Indicators

| LED | GPIO | Color | Pattern | Meaning | Troubleshooting Action |
|-----|------|-------|---------|---------|----------------------|
| **Power** | 18 | Green | Solid | System running normally | ✅ No action needed |
| Power | 18 | Green | Slow blink (1Hz) | System starting up | Wait for GPS acquisition |
| Power | 18 | Green | Off | System stopped or failed | Run: `python3 tests/troubleshoot.py` |
| **GPS** | 23 | Blue | Solid | GPS fix acquired | ✅ No action needed |
| GPS | 23 | Blue | Slow blink (0.5Hz) | Searching for GPS fix | Check GPS antenna, wait for fix |
| GPS | 23 | Blue | Off | GPS disabled or failed | Run: `python3 tests/gps_troubleshoot.py` |
| **Camera** | 24 | Yellow | Brief flash | Image captured | ✅ Normal operation |
| Camera | 24 | Yellow | Solid | Camera active/standby | ✅ Normal between captures |
| Camera | 24 | Yellow | SOS pattern | Camera error/failure | Run: `python3 tests/camera_troubleshoot.py` |
| **Error** | 25 | Red | Off | No critical errors | ✅ System healthy |
| Error | 25 | Red | Solid | Critical system error | **Run diagnostics immediately** |

### 🔴 Critical Error Conditions (Red LED Solid)
When the red error LED is solid, run diagnostics immediately:
```bash
# Identify critical errors
python3 tests/troubleshoot.py --critical-errors

# Check specific error conditions
python3 tests/system_health_check.py --errors-only
```

## 🔧 Problem Resolution Framework

### Step 1: Automated Problem Identification
```bash
# Always start with comprehensive diagnostics
python3 tests/troubleshoot.py

# The diagnostic tool will:
# ✅ Identify specific problems automatically
# ✅ Provide targeted solution recommendations  
# ✅ Test fixes and validate resolution
# ✅ Generate detailed problem reports
```

### Step 2: Component-Specific Troubleshooting
```bash
# For camera issues
python3 tests/camera_troubleshoot.py --detailed

# For GPS problems
python3 tests/gps_troubleshoot.py --detailed

# For storage issues
python3 tests/troubleshoot.py --component storage

# For network problems
python3 tests/troubleshoot.py --network
```

## 🚨 Common Problems and Solutions

### 1. Service Won't Start

#### 🔍 Automated Diagnosis
```bash
# Comprehensive service diagnostics
python3 tests/troubleshoot.py --service-check

# System health analysis
python3 tests/system_health_check.py --service-focus
```

#### 📋 Manual Diagnosis (if needed)
```bash
# Check service status details
sudo systemctl status bathyimager -l

# View service logs with timestamps
sudo journalctl -u bathyimager --since "1 hour ago" -f

# Test configuration validity
python3 src/config.py --validate --verbose
```

#### ✅ Automated Solutions
The diagnostic tools will automatically:
- Validate configuration and suggest fixes
- Check and repair permissions
- Test Python environment and dependencies
- Verify hardware connections
- Restart services with proper configuration

#### 🛠️ Manual Solutions (if automated tools don't resolve)
```bash
# Fix common permission issues
sudo chown -R bathyimager:bathyimager /opt/bathyimager
sudo usermod -a -G video,dialout,plugdev,gpio bathyimager

# Reinstall Python environment
cd /opt/bathyimager
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Reset service configuration
sudo systemctl daemon-reload
sudo systemctl restart bathyimager
```

### 2. Camera System Issues

#### 🔍 Automated Camera Diagnostics
```bash
# Comprehensive camera testing
python3 tests/camera_troubleshoot.py --detailed --benchmark

# Camera-specific problem identification
python3 tests/troubleshoot.py --component camera
```

#### 📊 What the Camera Diagnostics Test
- USB camera detection and enumeration
- Multiple backend testing (V4L2, GStreamer, FFmpeg)
- Resolution and framerate validation
- Image capture and processing pipeline
- Performance benchmarking and timing analysis
- EXIF metadata integration testing

#### ✅ Common Camera Issues and Auto-Fixes
The camera diagnostic tool automatically handles:
- **USB Connection Issues**: Tests multiple USB ports and power requirements
- **Backend Problems**: Tries different OpenCV backends automatically
- **Resolution Issues**: Validates and adjusts camera resolution settings
- **Permission Problems**: Checks and fixes camera access permissions
- **Performance Issues**: Identifies timing bottlenecks and suggests optimizations

### 3. GPS System Issues

#### 🔍 Automated GPS Diagnostics
```bash
# Comprehensive GPS testing and troubleshooting
python3 tests/gps_troubleshoot.py --detailed

# GPS-specific problem identification
python3 tests/troubleshoot.py --component gps
```

#### 📊 GPS Diagnostic Features
- **Device Detection**: Scans all USB serial ports for GPS devices
- **NMEA Parsing**: Validates GPS sentence parsing and coordinate extraction
- **Time Synchronization**: Tests GPS time accuracy and system time sync
- **Fix Quality**: Monitors GPS fix quality and satellite count
- **Mock GPS Testing**: Provides fallback testing without GPS hardware
- **EXIF Integration**: Validates GPS metadata embedding in images

#### ✅ Common GPS Issues and Auto-Fixes
The GPS diagnostic tool automatically:
- **Port Detection**: Finds GPS device on /dev/ttyUSB* or /dev/ttyACM*
- **Baud Rate**: Tests multiple baud rates (4800, 9600, 19200, 38400)
- **Permission Fixes**: Adds user to dialout group for serial access
- **NMEA Validation**: Verifies GPS sentence parsing and coordinate extraction
- **Time Sync Issues**: Diagnoses and fixes GPS time synchronization problems
- **Mock Mode**: Provides indoor testing capability when GPS unavailable

### 4. Storage and Logging Issues

#### 🔍 Automated Storage Diagnostics
```bash
# Storage system testing
python3 tests/troubleshoot.py --component storage

# Date-stamped logging validation
python3 tests/test_dated_logging.py

# Performance analysis with storage focus
python3 tests/performance_analyzer.py --storage-analysis
```

#### 📊 Storage Diagnostic Features
- **USB Mount Detection**: Validates USB storage mounting and permissions
- **Date Directory Structure**: Tests automatic YYYYMMDD directory creation
- **Write Performance**: Measures image write speeds and identifies bottlenecks
- **Disk Space Monitoring**: Checks available space and cleanup requirements
- **Log File Rotation**: Validates date-stamped logging functionality
- **Backup and Recovery**: Tests storage failure recovery mechanisms

#### ✅ Storage Issues and Auto-Fixes
- **Mount Problems**: Automatically mounts USB storage and fixes permissions
- **Directory Creation**: Creates proper date-stamped directory structure
- **Space Management**: Implements automatic cleanup based on configuration
- **Write Failures**: Identifies and resolves storage write permission issues
- **Log Rotation**: Ensures proper daily log file rotation and organization

### 5. Network Connectivity Issues

#### 🔍 Automated Network Diagnostics
```bash
# Comprehensive network testing
python3 tests/troubleshoot.py --network

# Network performance and stability analysis
./tests/network_test.sh --full

# Continuous network monitoring
python3 tests/performance_analyzer.py --network --monitor
```

#### 📊 Network Diagnostic Features
- **Dual Interface Testing**: Tests both Ethernet and WiFi connectivity
- **Failover Validation**: Verifies automatic failover between interfaces
- **DNS Resolution**: Tests DNS configuration and resolution speed
- **Routing Analysis**: Validates metric-based route prioritization
- **Performance Testing**: Measures latency, throughput, and stability
- **Configuration Validation**: Checks dhcpcd and wpa_supplicant settings

### 6. Performance and Timing Issues

#### 🔍 Performance Analysis and Monitoring
```bash
# Comprehensive performance analysis
python3 tests/performance_analyzer.py --analyze --benchmark

# Real-time performance monitoring
python3 tests/performance_analyzer.py --monitor --duration 300

# Timing precision analysis
python3 tests/performance_analyzer.py --timing-analysis
```

#### 📊 Performance Diagnostic Features
- **Capture Timing Analysis**: Measures precise timing from GPS to image storage
- **Pipeline Performance**: Identifies bottlenecks in the imaging pipeline
- **System Resource Monitoring**: Tracks CPU, memory, and I/O usage
- **Throughput Analysis**: Measures images per second and data rates
- **Storage Performance**: Tests USB write speeds and latency
- **Network Performance**: Analyzes connectivity impact on timing

#### ✅ Performance Optimization
The performance analyzer automatically:
- **Identifies Bottlenecks**: Pinpoints slow components in the imaging pipeline
- **Timing Optimization**: Validates <10ms timestamp precision for vehicle deployment
- **Resource Monitoring**: Tracks system resource usage and suggests optimizations
- **Storage Optimization**: Tests and optimizes USB storage write performance
- **Network Impact**: Measures network operations impact on imaging performance

## 🔧 Advanced Troubleshooting

### System Recovery Procedures

#### Configuration Reset
```bash
# Backup current configuration
cp config/bathyimager_config.json config/bathyimager_config.json.backup

# Run automated configuration recovery
python3 tests/troubleshoot.py --recover-config

# Manual configuration reset if needed
python3 src/config.py --create-default --output config/bathyimager_config.json
```

#### Service Recovery
```bash
# Automated service recovery
python3 tests/troubleshoot.py --recover-service

# Manual service reset if needed
sudo systemctl stop bathyimager
sudo systemctl daemon-reload
sudo systemctl start bathyimager
```

#### Complete System Recovery
```bash
# Full automated system recovery
python3 tests/troubleshoot.py --full-recovery

# Nuclear option - complete reinstallation
sudo ./scripts/install.sh --reset
```

### Log Analysis and Debugging

#### Date-Stamped Log Analysis
```bash
# Analyze recent logs
python3 tests/system_health_check.py --log-analysis

# View today's logs
tail -f /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Search for specific errors
grep -r "ERROR\|CRITICAL" /media/usb/bathyimager/logs/

# Performance log analysis
python3 tests/performance_analyzer.py --analyze-logs --days 7
```

#### Debug Mode Operation
```bash
# Run system in debug mode
cd /opt/bathyimager
source venv/bin/activate
python3 src/main.py --config config/bathyimager_config.json --debug

# Enable debug logging in configuration
# Edit config: "log_level": "DEBUG"
```

### Hardware Debugging

#### USB and Power Issues
```bash
# Check USB power and enumeration
lsusb -v | grep -E "(Camera|GPS|Power)"
dmesg | grep -i usb | tail -20

# Test USB power requirements
python3 tests/troubleshoot.py --usb-power-test

# Check system power supply
vcgencmd measure_volts
vcgencmd get_throttled
```

#### GPIO and LED Diagnostics
```bash
# Test LED functionality
python3 tests/troubleshoot.py --test-leds

# GPIO status check
gpio readall    # If available
```

### Remote Troubleshooting

#### SSH Remote Diagnostics
```bash
# Run diagnostics remotely via SSH
ssh pi@bathycat-ip "cd /opt/bathyimager && python3 tests/troubleshoot.py --remote"

# Monitor system remotely
ssh pi@bathycat-ip "python3 /opt/bathyimager/tests/performance_analyzer.py --monitor"

# Generate remote diagnostic report
ssh pi@bathycat-ip "python3 /opt/bathyimager/tests/system_health_check.py --report > diagnostic_report.txt"
```

#### Remote Log Monitoring
```bash
# Stream logs remotely
ssh pi@bathycat-ip "sudo journalctl -u bathyimager -f"

# Download log files
scp pi@bathycat-ip:/media/usb/bathyimager/logs/$(date +%Y%m%d)/* ./local_logs/
```
ls -la /dev/video*

# Test camera manually
ffplay /dev/video0
# Press 'q' to quit

# Check permissions
groups bathyimager | grep video
```

#### Solutions

**Camera Not Detected:**
```bash
# Reconnect USB camera
sudo dmesg | tail -20

# Check different USB port
# Verify camera power requirements
```

**Permission Issues:**
```bash
# Add user to video group
sudo usermod -a -G video bathycat
sudo systemctl restart bathycat
```

**Wrong Device Index:**
```bash
# Find correct video device
v4l2-ctl --list-devices

# Update configuration
sudo nano /etc/bathycat/config.json
# Set correct device_index
```

**USB Power Issues:**
```bash
# Check USB power config
echo 'max_usb_current=1' | sudo tee -a /boot/config.txt
sudo reboot
```

### 3. GPS Not Working

#### Symptoms
- Status LED slow blinking (never solid)
- Log messages about GPS timeout
- Mock GPS coordinates in images

#### Diagnosis
```bash
# Check GPS device detection
lsusb | grep -i gps

# Check serial devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# Test GPS data stream
sudo cat /dev/ttyUSB0
# Should show NMEA sentences like $GPGGA...

# Check permissions
groups bathycat | grep dialout
```

#### Solutions

**GPS Device Not Found:**
```bash
# Check USB connection
sudo dmesg | tail -20

# Try different USB port
# Check GPS power LED (if available)
```

**Wrong Serial Port:**
```bash
# Find GPS device
dmesg | grep tty | grep USB

# Update configuration
sudo nano /etc/bathycat/config.json
# Set correct port (e.g., "/dev/ttyACM0")
```

**Permission Issues:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout bathycat
sudo systemctl restart bathycat
```

**GPS Signal Issues:**
```bash
# Move to open area with sky view
# Wait 5-10 minutes for cold start
# Check GPS status with gpsd tools:
sudo apt install gpsd-clients -y
cgps -s
```

**Baud Rate Issues:**
```bash
# Try different baud rates in config:
# Common values: 4800, 9600, 19200, 38400
sudo nano /etc/bathycat/config.json
```

### 4. Storage Problems

#### Symptoms
- Error LED blinking
- Log messages about storage unavailable
- No images being saved

#### Diagnosis
```bash
# Check USB storage detection
lsblk

# Check mount status
mount | grep usb

# Check available space
df -h /media/usb

# Check permissions
ls -la /media/usb
```

#### Solutions

**USB Drive Not Mounted:**
```bash
# Manual mount
sudo mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Check auto-mount rules
cat /etc/udev/rules.d/99-bathycat-usb.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Insufficient Space:**
```bash
# Clean old files
sudo find /media/usb -name "*.jpg" -mtime +30 -delete

# Or use larger USB drive
```

**Permission Issues:**
```bash
# Fix permissions
sudo chown -R bathycat:bathycat /media/usb
sudo chmod -R 755 /media/usb
```

**Filesystem Corruption:**
```bash
# Check filesystem (unmount first)
sudo umount /media/usb
sudo fsck /dev/sda1

# Reformat if needed (WILL ERASE DATA)
sudo mkfs.ext4 /dev/sda1 -L "BATHYCAT"
```

### 5. High CPU/Memory Usage

#### Symptoms
- System sluggish
- High temperature
- Capture errors due to performance

#### Diagnosis
```bash
# Check system resources
htop

# Check BathyCat process
ps aux | grep bathycat

# Check temperature
vcgencmd measure_temp

# Check capture timing
sudo journalctl -u bathycat | grep "Capture time"
```

#### Solutions

**Reduce Camera Resolution:**
```bash
sudo nano /etc/bathycat/config.json
# Set lower resolution (e.g., 1280x720)
# Reduce FPS if needed
```

**Increase Capture Interval:**
```bash
sudo nano /etc/bathycat/config.json
# Increase capture_interval (e.g., 2.0 seconds)
```

**Optimize JPEG Quality:**
```bash
sudo nano /etc/bathycat/config.json
# Reduce jpeg_quality (e.g., 85 instead of 95)
```

**Cooling Issues:**
```bash
# Add heatsink or fan
# Check case ventilation
# Reduce overclocking if enabled
```

### 6. Log File Issues

#### Symptoms
- Disk full errors
- Cannot write logs
- Service stops unexpectedly

#### Diagnosis
```bash
# Check log directory space
du -sh /var/log/bathycat/

# Check log rotation
ls -la /etc/logrotate.d/bathycat

# Check systemd journal size
journalctl --disk-usage
```

#### Solutions

**Log Directory Full:**
```bash
# Clean old logs
sudo find /var/log/bathycat -name "*.log.*" -mtime +7 -delete

# Set up log rotation
sudo tee /etc/logrotate.d/bathycat << EOF
/var/log/bathycat/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 bathycat bathycat
}
EOF
```

**Journal Too Large:**
```bash
# Clean old journal entries
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=100M

# Limit journal size
sudo nano /etc/systemd/journald.conf
# Add: SystemMaxUse=100M
```

### 7. Network/SSH Issues

#### Symptoms
- Cannot connect via SSH
- Network configuration problems
- Remote monitoring not working

#### Diagnosis
```bash
# Check network status
ip addr show

# Check SSH service
sudo systemctl status ssh

# Check WiFi connection
iwconfig
```

#### Solutions

**SSH Not Working:**
```bash
# Enable SSH service
sudo systemctl enable ssh
sudo systemctl start ssh

# Check SSH configuration
sudo nano /etc/ssh/sshd_config
```

**WiFi Issues:**
```bash
# Configure WiFi
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf

# Add network:
# network={
#     ssid="YourNetworkName"
#     psk="YourPassword"
# }

# Restart networking
sudo systemctl restart networking
```

## Error Codes Reference

| Code | Description | Cause | Solution |
|------|-------------|-------|----------|
| E001 | Camera initialization failed | Hardware/driver issue | Check camera connection |
| E002 | GPS timeout | No GPS signal/device | Check GPS hardware and antenna |
| E003 | Storage unavailable | USB drive issue | Check drive connection and mount |
| E004 | Configuration invalid | Bad config file | Validate and fix configuration |
| E005 | Insufficient disk space | Storage full | Clean files or add storage |
| E006 | Permission denied | File/device permissions | Fix ownership and permissions |
| E007 | Service startup failed | System configuration | Check service configuration |
| E008 | Hardware not detected | USB device missing | Reconnect hardware |

## 📞 Support and Getting Help

### Before Requesting Support
Always run automated diagnostics first:
```bash
# Generate comprehensive diagnostic report
python3 tests/troubleshoot.py --generate-report

# For urgent issues, include this output with your support request
python3 tests/troubleshoot.py --support-package
```

### Support Resources

#### 🤖 Automated Problem Resolution
- **Master Troubleshoot Tool**: `python3 tests/troubleshoot.py`
- **Component Diagnostics**: Individual tools for camera, GPS, storage, network
- **Performance Analysis**: `python3 tests/performance_analyzer.py`
- **System Health Monitoring**: `python3 tests/system_health_check.py`

#### 📚 Documentation Resources
- **Installation Guide**: `docs/INSTALL.md` - Complete setup instructions
- **Network Setup**: `docs/NETWORK_SETUP.md` - Network configuration and troubleshooting
- **Logging System**: `docs/LOGGING_SYSTEM.md` - Date-stamped logging details
- **Main README**: `README.md` - Complete system overview and usage

#### 🛠️ Developer Support
- **GitHub Issues**: https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/issues
- **System Architecture**: See `src/` directory for component implementations
- **Configuration Examples**: `config/` directory for sample configurations

### Creating Support Requests

#### 📋 Information to Include
```bash
# Run this command and include output with support requests:
python3 tests/troubleshoot.py --support-info

# This automatically includes:
# ✅ System configuration and hardware detection
# ✅ Service status and recent logs
# ✅ Performance metrics and timing analysis
# ✅ Error codes and diagnostic results
# ✅ Network configuration and connectivity tests
```

#### 🔍 Log File Locations
All logs are automatically organized by date:
- **Application Logs**: `/media/usb/bathyimager/logs/YYYYMMDD/bathyimager.log`
- **System Logs**: `sudo journalctl -u bathyimager --since "24 hours ago"`
- **Performance Logs**: Generated by performance analyzer
- **Diagnostic Reports**: Created by troubleshooting tools

### Emergency Troubleshooting

#### 🚨 System Not Responding
```bash
# Check if system is completely frozen
ping bathycat-ip-address

# If responsive, run emergency diagnostics
ssh pi@bathycat-ip "python3 /opt/bathyimager/tests/troubleshoot.py --emergency"

# If not responsive, power cycle and run recovery
sudo reboot
# After reboot:
python3 tests/troubleshoot.py --post-recovery
```

#### 🔄 Quick Recovery Commands
```bash
# Service recovery
sudo systemctl restart bathyimager

# Configuration recovery
python3 tests/troubleshoot.py --recover-config

# Full system recovery
python3 tests/troubleshoot.py --full-recovery

# Nuclear option - complete reset
sudo ./scripts/install.sh --reset
```

## 📊 Success Indicators

### ✅ System Operating Normally
- **LEDs**: Green power (solid), blue GPS (solid), yellow camera (brief flashes)
- **Service**: `systemctl status bathyimager` shows "active (running)"
- **Images**: New images appear in `/media/usb/bathyimager/images/YYYYMMDD/` every 1-2 seconds
- **GPS**: Images contain GPS coordinates in EXIF metadata
- **Logs**: No ERROR or CRITICAL messages in recent logs
- **Performance**: `python3 tests/performance_analyzer.py --quick` shows normal timing

### 🔧 Maintenance Reminders
```bash
# Run weekly system health check
python3 tests/system_health_check.py --weekly-report

# Monthly performance analysis
python3 tests/performance_analyzer.py --monthly-analysis

# Update system (smart dependency checking)
./update

# Check storage usage
df -h /media/usb/bathyimager/
```

### 🎯 Performance Targets
- **Image Capture Interval**: 1-2 seconds (configurable)
- **Timestamp Precision**: <10ms accuracy for vehicle deployment
- **GPS Fix Time**: <2 minutes in clear sky conditions
- **Storage Write Speed**: >10 MB/s USB 3.0 performance
- **System Response**: Diagnostic tools complete in <30 seconds
- **Memory Usage**: <1GB RAM usage during normal operation

The BathyCat troubleshooting framework is designed to resolve most issues automatically. When problems occur, always start with `python3 tests/troubleshoot.py` for comprehensive automated diagnosis and resolution.
while true; do
    echo "$(date): CPU: $(vcgencmd measure_temp) Memory: $(free -m | awk 'NR==2{printf "%.1f%%\n", $3*100/$2}')"
    sleep 60
done
EOF

chmod +x /opt/bathycat/monitor.sh
```

Run monitoring:
```bash
./monitor.sh | tee performance.log
```

### System Recovery

**Safe Mode Startup:**
```bash
# Stop service
sudo systemctl stop bathycat

# Create minimal config
sudo tee /etc/bathycat/config.json << EOF
{
  "version": "1.0",
  "system": {"environment": "development"},
  "gps": {"mock_enabled": true},
  "leds": {"enabled": false},
  "logging": {"level": "DEBUG", "console_output": true}
}
EOF

# Test manually
cd /opt/bathycat/src
sudo -u bathycat ../venv/bin/python -m main
```

**Factory Reset:**
```bash
# Complete system reset
sudo ./scripts/install.sh --reset

# Or manual reset:
sudo systemctl stop bathycat
sudo rm -rf /opt/bathycat
sudo rm -rf /etc/bathycat
sudo rm /etc/systemd/system/bathycat.service
# Then reinstall
```

## Preventive Maintenance

### Regular Checks (Weekly)
```bash
# System health
sudo systemctl status bathycat
df -h /media/usb
vcgencmd measure_temp

# Log review
sudo journalctl -u bathycat --since "1 week ago" | grep ERROR

# Hardware check
lsusb
ls /dev/video* /dev/ttyUSB*
```

### Monthly Maintenance
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Check for BathyCat updates
sudo ./scripts/bathycat-update --check

# Clean logs
sudo journalctl --vacuum-time=30d

# Check storage
du -sh /media/usb/*
```

### Backup Procedures
```bash
# Backup configuration
sudo cp /etc/bathycat/config.json ~/bathycat-config-backup.json

# Backup images (to external storage)
rsync -av /media/usb/ /external/backup/bathycat-images/

# System backup (if needed)
sudo dd if=/dev/mmcblk0 of=/external/pi-backup.img bs=4M status=progress
```

## Getting Help

### Information to Collect
Before seeking help, collect:

1. **System Information:**
   ```bash
   uname -a
   cat /etc/os-release
   python3 --version
   ```

2. **Service Status:**
   ```bash
   sudo systemctl status bathycat
   ```

3. **Recent Logs:**
   ```bash
   sudo journalctl -u bathycat --since "1 hour ago"
   ```

4. **Hardware Status:**
   ```bash
   lsusb
   ls /dev/video* /dev/ttyUSB*
   df -h
   ```

5. **Configuration:**
   ```bash
   sudo cat /etc/bathycat/config.json
   ```

### Support Channels
- **GitHub Issues**: For bugs and feature requests
- **Documentation**: Check README.md and INSTALL.md  
- **Community**: GitHub Discussions for general help

### Emergency Recovery
If system is completely unresponsive:

1. **Hardware Reset**: Power cycle the Raspberry Pi
2. **SSH Recovery**: Connect via SSH and check logs
3. **SD Card Recovery**: Remove SD card and check filesystem on another computer
4. **Fresh Install**: Reinstall system from backup or start over

Remember: Most issues are resolved by checking connections, permissions, and configuration files. Start with the simple solutions first!