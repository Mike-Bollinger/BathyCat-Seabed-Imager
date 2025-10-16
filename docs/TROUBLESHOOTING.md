# BathyImager Troubleshooting Guide

This guide helps diagnose and resolve common issues with the BathyImager Seabed Imager system.

## Quick Diagnostics

### System Health Check
```bash
# Check service status
sudo systemctl status bathyimager

# View recent logs
sudo journalctl -u bathyimager --since "1 hour ago"

# Check hardware detection
cd /opt/bathyimager/src && sudo python3 -m config --show-hardware

# Validate configuration
cd /opt/bathyimager/src && sudo python3 -m config --validate

# Check disk usage
df -h /media/usb
```

### LED Status Indicators

| LED | Pattern | Meaning | Action |
|-----|---------|---------|---------|
| Status (Green) | Solid | Normal operation | None needed |
| Status (Green) | Slow blink | Starting/GPS acquiring | Wait for GPS fix |
| Status (Green) | Off | System stopped | Check service status |
| Error (Red) | Off | No errors | Normal |
| Error (Red) | Solid | Critical error | Check logs |
| Error (Red) | Fast blink | Warning condition | Monitor system |
| Activity (Blue) | Blink on capture | Image captured | Normal |

## Common Problems

### 1. Service Won't Start

#### Symptoms
- `systemctl status bathyimager` shows failed
- No LED activity
- No log entries

#### Diagnosis
```bash
# Check detailed service status
sudo systemctl status bathyimager -l

# Check service logs
sudo journalctl -u bathyimager --no-pager

# Test manual startup
cd /opt/bathyimager
sudo -u bathyimager ./venv/bin/python -m bathyimager.main
```

#### Solutions

**Configuration Error:**
```bash
# Validate configuration
cd /opt/bathyimager/src && sudo python3 -m config --validate

# Reset to defaults if needed
cd /opt/bathyimager/src && sudo python3 -m config --create-default
```

**Permission Issues:**
```bash
# Fix ownership
sudo chown -R bathyimager:bathyimager /var/log/bathyimager
sudo chown -R pi:pi /opt/bathyimager

# Fix user groups
sudo usermod -a -G video,dialout,plugdev bathyimager
```

**Missing Dependencies:**
```bash
# Reinstall Python packages
cd /opt/bathyimager
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Camera Not Working

#### Symptoms
- Error LED solid red
- Log messages about camera initialization failure
- No image capture

#### Diagnosis
```bash
# Check USB camera detection
lsusb | grep -i camera

# Check video devices
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

## Advanced Troubleshooting

### Debug Mode

Enable debug logging:
```bash
sudo nano /etc/bathycat/config.json
```

Set logging level to DEBUG:
```json
{
  "logging": {
    "level": "DEBUG",
    "console_output": true
  }
}
```

Restart service:
```bash
sudo systemctl restart bathycat
```

### Manual Component Testing

**Test GPS Module:**
```bash
cd /opt/bathycat/src
source ../venv/bin/activate
python3 -c "
from gps import GPS
from config import GPSConfig

config = GPSConfig()
config.mock_enabled = False  # Use real GPS
gps = GPS(config)

if gps.connect():
    print('GPS connected')
    fix = gps.wait_for_fix(timeout=30)
    if fix and fix.valid:
        print(f'GPS Fix: {fix.latitude}, {fix.longitude}')
    else:
        print('No GPS fix obtained')
else:
    print('GPS connection failed')
"
```

**Test Camera Module:**
```bash
cd /opt/bathycat/src
source ../venv/bin/activate
python3 -c "
from camera import Camera  
from config import CameraConfig

config = CameraConfig()
camera = Camera(config)

if camera.initialize():
    print('Camera initialized')
    frame = camera.capture_frame()
    if frame is not None:
        print('Frame captured successfully')
        print(f'Frame shape: {frame.shape}')
    else:
        print('Frame capture failed')
    camera.close()
else:
    print('Camera initialization failed')
"
```

### Performance Monitoring

Create monitoring script:
```bash
sudo tee /opt/bathycat/monitor.sh << 'EOF'
#!/bin/bash
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