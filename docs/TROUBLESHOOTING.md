# BathyCat Seabed Imager - Troubleshooting Guide

This guide helps diagnose and resolve common issues with the BathyCat Seabed Imager system.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [GPS Issues](#gps-issues)
3. [Camera Problems](#camera-problems)
4. [Storage Issues](#storage-issues)
5. [Service and Software Issues](#service-and-software-issues)
6. [Power and Hardware Problems](#power-and-hardware-problems)
7. [Performance Issues](#performance-issues)
8. [Network and Communication](#network-and-communication)

---

## Quick Diagnostics

### System Status Check

Run the comprehensive status check script:

```bash
# Check overall system status
/opt/bathycat/status.sh

# Check service status
sudo systemctl status bathycat-imager

# View recent logs
journalctl -u bathycat-imager --no-pager -n 20
```

### Common Status Indicators

| LED Pattern | Meaning | Action |
|-------------|---------|--------|
| Solid Green | GPS Fix + Camera Active | Normal operation |
| Blinking Green | GPS searching | Wait for fix or check antenna |
| Solid Red | Critical error | Check logs and hardware |
| Blinking Red | Storage critical | Check disk space |
| No LEDs | No power or boot failure | Check power and SD card |

---

## GPS Issues

### Problem: GPS Not Acquiring Fix

**Symptoms:**
- "No GPS Fix" in status
- GPS timeout errors in logs
- Service fails to start

**Diagnostic Steps:**

1. **Check Hardware Connections**
   ```bash
   # Verify GPS HAT is detected
   sudo i2cdetect -y 1
   
   # Check serial port
   ls -la /dev/serial0
   
   # Test serial data
   sudo cat /dev/serial0
   # Should see NMEA sentences like $GPGGA...
   ```

2. **Test GPS Service**
   ```bash
   # Stop main service
   sudo systemctl stop bathycat-imager
   
   # Test GPSD directly
   sudo systemctl start gpsd
   cgps -s
   
   # Check GPS status
   gpsstat
   ```

3. **Check Antenna**
   ```bash
   # Test antenna connection
   sudo gpspipe -r -n 10 | grep GGA
   
   # Check for active antenna power
   # Some antennas need 3.3V or 5V power
   ```

**Solutions:**

1. **Antenna Issues**
   ```bash
   # Check antenna placement
   # - Clear sky view (no metal obstruction)
   # - Away from electronics
   # - Properly connected to GPS HAT
   
   # For active antennas, verify power
   sudo gpio mode 1 out
   sudo gpio write 1 1  # Enable antenna power
   ```

2. **Serial Port Configuration**
   ```bash
   # Check boot configuration
   sudo nano /boot/config.txt
   # Ensure these lines exist:
   enable_uart=1
   dtoverlay=disable-bt
   
   # Disable serial console
   sudo raspi-config
   # Advanced > Serial > No to console, Yes to hardware
   
   # Reboot after changes
   sudo reboot
   ```

3. **GPSD Configuration**
   ```bash
   # Edit GPSD config
   sudo nano /etc/default/gpsd
   
   # Correct configuration:
   START_DAEMON="true"
   USBAUTO="false"
   DEVICES="/dev/serial0"
   GPSD_OPTIONS="-n -s 9600"
   
   # Restart service
   sudo systemctl restart gpsd
   ```

### Problem: GPS Fix Lost During Operation

**Symptoms:**
- Intermittent GPS loss
- Position jumping
- Time sync errors

**Solutions:**

1. **Check Power Supply**
   ```bash
   # Monitor voltage during operation
   vcgencmd measure_volts
   # Should be close to 1.2V (core), 3.3V (sdram)
   
   # Check for voltage drops under load
   ```

2. **Improve Signal Reception**
   ```bash
   # Check satellite count
   cgps -s
   # Need minimum 4 satellites for 3D fix
   
   # Consider GPS antenna upgrade
   # Move antenna to higher position
   ```

---

## Camera Problems

### Problem: Camera Not Detected

**Symptoms:**
- Camera initialization failed in logs
- No video device found
- USB device not recognized

**Diagnostic Steps:**

1. **Check USB Connection**
   ```bash
   # List USB devices
   lsusb
   # Should see camera device
   
   # Check video devices
   ls /dev/video*
   
   # Get device details
   v4l2-ctl --list-devices
   ```

2. **Test Camera Directly**
   ```bash
   # Simple capture test
   fswebcam -d /dev/video0 test.jpg
   
   # Check supported formats
   v4l2-ctl -d /dev/video0 --list-formats-ext
   ```

**Solutions:**

1. **USB Issues**
   ```bash
   # Try different USB port
   # Check USB cable integrity
   # Test with shorter cable
   
   # Check USB power
   # High-resolution cameras need USB 3.0
   ```

2. **Driver Issues**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade
   
   # Install V4L2 utils
   sudo apt install v4l-utils
   
   # Check kernel modules
   lsmod | grep uvcvideo
   ```

### Problem: Poor Image Quality

**Symptoms:**
- Blurry images
- Wrong colors underwater
- Dark or overexposed images

**Solutions:**

1. **Underwater Optimization**
   ```python
   # Adjust camera settings in config.json
   {
     "camera_auto_exposure": false,
     "camera_exposure": -6,
     "camera_auto_white_balance": false,
     "camera_white_balance": 4000,
     "camera_contrast": 60,
     "camera_saturation": 70
   }
   ```

2. **Focus Adjustment**
   ```bash
   # Manual focus (if supported)
   v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0
   v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50
   
   # Check focus through water
   # Objects appear 25% closer underwater
   ```

### Problem: Low Frame Rate

**Symptoms:**
- Capture rate below target 4 FPS
- Frame drops in logs
- Performance warnings

**Solutions:**

1. **USB Bandwidth**
   ```bash
   # Check USB version
   lsusb -t
   # Ensure camera on USB 3.0 port
   
   # Reduce resolution if needed
   # Lower JPEG quality slightly
   ```

2. **System Performance**
   ```bash
   # Monitor CPU usage
   htop
   
   # Check I/O wait
   iostat -x 1
   
   # Optimize performance
   sudo systemctl disable unnecessary-service
   ```

---

## Storage Issues

### Problem: Storage Mount Failure

**Symptoms:**
- "Storage initialization failed"
- /media/ssd not accessible
- Permission denied errors

**Diagnostic Steps:**

1. **Check Mount Status**
   ```bash
   # Check if mounted
   mount | grep ssd
   
   # Check filesystem
   sudo fsck /dev/sda1
   
   # Check fstab entry
   cat /etc/fstab | grep ssd
   ```

**Solutions:**

1. **Manual Mount**
   ```bash
   # Create mount point
   sudo mkdir -p /media/ssd
   
   # Mount manually
   sudo mount /dev/sda1 /media/ssd
   
   # Fix permissions
   sudo chown -R pi:pi /media/ssd
   ```

2. **Fstab Configuration**
   ```bash
   # Get UUID
   sudo blkid /dev/sda1
   
   # Add to fstab
   echo "UUID=your-uuid /media/ssd ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
   
   # Test mount
   sudo mount -a
   ```

### Problem: Disk Space Critical

**Symptoms:**
- Low disk space warnings
- Auto-cleanup activated
- Write failures

**Solutions:**

1. **Immediate Cleanup**
   ```bash
   # Check space
   df -h /media/ssd
   
   # Manual cleanup
   sudo find /media/ssd/bathycat/images -type f -mtime +7 -delete
   
   # Clear logs
   sudo journalctl --vacuum-time=2d
   ```

2. **Configure Auto-Cleanup**
   ```json
   // In config.json
   {
     "auto_cleanup_enabled": true,
     "cleanup_threshold_gb": 10.0,
     "days_to_keep": 15
   }
   ```

---

## Service and Software Issues

### Problem: Service Won't Start

**Symptoms:**
- Service fails on boot
- "Active: failed" status
- Python errors in logs

**Diagnostic Steps:**

1. **Check Service Status**
   ```bash
   sudo systemctl status bathycat-imager
   
   # View detailed logs
   journalctl -u bathycat-imager --no-pager
   
   # Check service file
   cat /etc/systemd/system/bathycat-imager.service
   ```

2. **Test Manual Start**
   ```bash
   # Try manual start
   cd /opt/bathycat
   source venv/bin/activate
   python3 src/bathycat_imager.py --config /etc/bathycat/config.json --verbose
   ```

**Solutions:**

1. **Permission Issues**
   ```bash
   # Fix ownership
   sudo chown -R pi:pi /opt/bathycat
   
   # Fix permissions
   chmod +x /opt/bathycat/src/bathycat_imager.py
   ```

2. **Python Environment**
   ```bash
   # Reinstall virtual environment
   sudo rm -rf /opt/bathycat/venv
   sudo python3 -m venv /opt/bathycat/venv
   source /opt/bathycat/venv/bin/activate
   pip install --upgrade pip
   pip install opencv-python numpy pillow pyserial pynmea2 psutil piexif
   ```

### Problem: Configuration Errors

**Symptoms:**
- "Configuration validation failed"
- Invalid parameter errors
- Service exits immediately

**Solutions:**

1. **Validate Configuration**
   ```bash
   # Check JSON syntax
   python3 -m json.tool /etc/bathycat/config.json
   
   # Reset to defaults
   sudo cp /opt/bathycat/config/bathycat_config.json /etc/bathycat/config.json
   ```

2. **Common Configuration Fixes**
   ```json
   {
     "capture_fps": 4.0,           // Must be positive number
     "camera_device_id": 0,        // Check with v4l2-ctl --list-devices
     "storage_base_path": "/media/ssd/bathycat",  // Must exist
     "gps_port": "/dev/serial0"    // Check if exists
   }
   ```

---

## Power and Hardware Problems

### Problem: System Randomly Reboots

**Symptoms:**
- Unexpected system restarts
- Power-related log entries
- USB devices disconnecting

**Diagnostic Steps:**

1. **Check Power Supply**
   ```bash
   # Check voltage
   vcgencmd measure_volts
   
   # Monitor for under-voltage
   vcgencmd get_throttled
   # 0x0 = good, other values indicate throttling
   
   # Check power events in logs
   grep -i power /var/log/syslog
   ```

**Solutions:**

1. **Power Supply Upgrade**
   ```bash
   # Use official Raspberry Pi power supply (5V/3A)
   # Or marine-grade equivalent with same specs
   # Ensure adequate current capacity for all devices
   ```

2. **USB Power Management**
   ```bash
   # Disable USB autosuspend
   echo 'SUBSYSTEM=="usb", ACTION=="add", ATTR{idVendor}=="*", ATTR{idProduct}=="*", TEST=="power/control", ATTR{power/control}="on"' | sudo tee /etc/udev/rules.d/50-usb-power.rules
   ```

### Problem: Overheating

**Symptoms:**
- High CPU temperature (>80°C)
- Thermal throttling messages
- Performance degradation

**Solutions:**

1. **Cooling Improvements**
   ```bash
   # Check current temperature
   vcgencmd measure_temp
   
   # Install larger heat sinks
   # Add case fan if possible
   # Improve ventilation
   ```

2. **Performance Optimization**
   ```bash
   # Reduce GPU memory split
   echo "gpu_mem=64" | sudo tee -a /boot/config.txt
   
   # Lower CPU governor
   echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
   ```

---

## Performance Issues

### Problem: Slow Capture Rate

**Symptoms:**
- FPS below target
- High processing times
- CPU overload

**Diagnostic Steps:**

1. **Performance Monitoring**
   ```bash
   # Monitor real-time performance
   htop
   
   # Check I/O performance
   sudo iotop
   
   # Monitor capture statistics
   tail -f /var/log/bathycat/bathycat.log | grep "FPS"
   ```

**Solutions:**

1. **System Optimization**
   ```bash
   # Disable unnecessary services
   sudo systemctl disable bluetooth
   sudo systemctl disable wifi-country.service
   
   # Optimize scheduler
   echo "deadline" | sudo tee /sys/block/sda/queue/scheduler
   ```

2. **Application Tuning**
   ```json
   // Reduce processing overhead
   {
     "enable_preview": false,      // Disable if not needed
     "jpeg_quality": 80,           // Lower if acceptable
     "enable_metadata": false      // Disable if not critical
   }
   ```

---

## Network and Communication

### Problem: SSH Connection Issues

**Symptoms:**
- Cannot connect via SSH
- Connection timeouts
- Authentication failures

**Solutions:**

1. **Enable SSH**
   ```bash
   # Enable SSH service
   sudo systemctl enable ssh
   sudo systemctl start ssh
   
   # Check SSH status
   sudo systemctl status ssh
   ```

2. **Network Configuration**
   ```bash
   # Check IP address
   ip addr show
   
   # Test connectivity
   ping 8.8.8.8
   
   # Check SSH configuration
   sudo nano /etc/ssh/sshd_config
   ```

---

## Emergency Recovery

### Boot Issues

1. **SD Card Recovery**
   ```bash
   # Remove SD card and check on another computer
   # Run filesystem check
   # Re-flash if corrupted
   ```

2. **Safe Mode Boot**
   ```bash
   # Add to cmdline.txt for recovery boot
   # systemd.unit=rescue.target
   ```

### Factory Reset

1. **Clean Reinstall**
   ```bash
   # Backup configuration
   sudo cp /etc/bathycat/config.json ~/config_backup.json
   
   # Remove installation
   sudo rm -rf /opt/bathycat
   sudo rm -f /etc/systemd/system/bathycat-imager.service
   
   # Run installer again
   sudo ./scripts/install.sh
   
   # Restore configuration
   sudo cp ~/config_backup.json /etc/bathycat/config.json
   ```

---

## Getting Help

### Log Collection

When reporting issues, collect these logs:

```bash
# System information
uname -a > system_info.txt
lsusb >> system_info.txt
lsblk >> system_info.txt

# Service logs
journalctl -u bathycat-imager --no-pager > service_logs.txt

# Configuration
sudo cp /etc/bathycat/config.json config_copy.json

# Hardware status
/opt/bathycat/status.sh > status_output.txt

# Create support package
tar -czf bathycat_support_$(date +%Y%m%d_%H%M%S).tar.gz \
    system_info.txt service_logs.txt config_copy.json status_output.txt
```

### Contact Support

- **GitHub Issues**: [Project Repository]
- **Documentation**: Check docs/ directory
- **Community Forum**: [Link if available]

Include the support package and detailed description of:
- What you were trying to do
- What happened instead
- When the problem started
- Any recent changes to the system
