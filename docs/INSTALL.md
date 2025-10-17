# BathyCat Installation Guide

This guide provides step-by-step instructions for installing the BathyCat Seabed Imager system on a Raspberry Pi.

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4 Model B (4GB RAM recommended)
- MicroSD card (32GB+ Class 10 or better)
- DWE StellarHD USB Camera or compatible USB camera
- Adafruit Ultimate GPS - USB Version or compatible GPS
- USB 3.0 flash drive (512GB+ recommended)
- Optional: LEDs for status indication

### Software Requirements
- Raspberry Pi OS Lite (64-bit recommended)
- Internet connection for initial setup
- SSH access (recommended for headless setup)

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Prepare Raspberry Pi**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install git
   sudo apt install git -y
   ```

2. **Clone Repository**
   ```bash
   git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
   cd BathyCat-Seabed-Imager
   ```

3. **Run Installation Script**
   ```bash
   chmod +x /scripts/install.sh
   sudo ./scripts/install.sh
   ```

   The installer will:
   - Install all required system packages
   - Set up Python virtual environment
   - Install Python dependencies
   - Create system user and directories
   - Configure systemd service
   - Set up USB auto-mounting
   - Configure log rotation
   - Run initial tests

4. **Configure System**
   ```bash
   # Edit configuration file to match your hardware setup
   nano config/bathyimager_config.json
   ```

   **Key settings to verify/adjust:**
   - **Camera device**: Update `camera_device_id` if camera not on `/dev/video0`
   - **GPS port**: Update `gps_port` if GPS not on `/dev/ttyUSB0`
   - **Storage path**: Verify `storage_base_path` matches your USB mount point
   - **Capture rate**: Adjust `capture_fps` for your survey needs
   - **GPS requirements**: Set `require_gps_fix` based on your environment

   **Quick hardware check:**
   ```bash
   # List cameras
   ls /dev/video*
   
   # List GPS/serial devices
   ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No serial devices found"
   
   # Check USB storage mount point
   lsblk -o NAME,MOUNTPOINT | grep -E "(sd|usb)"
   ```

   **Test configuration:**
   ```bash
   # Validate config syntax
   cd ~/BathyCat-Seabed-Imager
   source venv/bin/activate
   python -c "import json; json.load(open('config/bathyimager_config.json')); print('Configuration valid')"
   ```

5. **Start Service**
   ```bash
   # Start the service
   sudo systemctl start bathyimager
   
   # Enable auto-start on boot
   sudo systemctl enable bathyimager
   
   # Check status
   sudo systemctl status bathyimager
   ```

### Method 2: Manual Installation

1. **System Updates and Dependencies**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install system packages
   sudo apt install -y \
       python3 \
       python3-pip \
       python3-venv \
       python3-dev \
       git \
       cmake \
       build-essential \
       pkg-config \
       libjpeg-dev \
       libtiff5-dev \
       libpng-dev \
       libavcodec-dev \
       libavformat-dev \
       libswscale-dev \
       libv4l-dev \
       libxvidcore-dev \
       libx264-dev \
       libgtk-3-dev \
       libatlas-base-dev \
       gfortran \
       usbutils \
       gpsd \
       gpsd-clients
   ```

2. **Create System User**
   ```bash
   # Create bathycat user
   sudo useradd -r -s /bin/false bathycat
   
   # Add to required groups
   sudo usermod -a -G video,dialout,plugdev bathycat
   ```

3. **Create Directories**
   ```bash
   # Create installation directory
   sudo mkdir -p /opt/bathycat
   sudo chown pi:pi /opt/bathycat
   
   # Create configuration directory
   sudo mkdir -p /etc/bathycat
   
   # Create log directory
   sudo mkdir -p /var/log/bathycat
   sudo chown bathycat:bathycat /var/log/bathycat
   ```

4. **Install BathyCat**
   ```bash
   # Clone and install
   cd /opt
   sudo git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git bathycat-source
   sudo cp -r bathycat-source/src/bathycat /opt/bathycat/
   sudo cp -r bathycat-source/scripts /opt/bathycat/
   
   # Set permissions
   sudo chown -R pi:pi /opt/bathycat
   ```

5. **Python Environment**
   ```bash
   # Create virtual environment
   cd /opt/bathycat
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install opencv-python pynmea2 Pillow piexif pyserial RPi.GPIO
   ```

6. **System Service**
   ```bash
   # Copy service file
   sudo cp /opt/bathycat/scripts/bathyimager.service /etc/systemd/system/
   
   # Enable service
   sudo systemctl daemon-reload
   sudo systemctl enable bathycat
   ```

7. **USB Auto-mount**
   ```bash
   # Install udisks2
   sudo apt install udisks2 -y
   
   # Create udev rule
   sudo tee /etc/udev/rules.d/99-bathycat-usb.rules << EOF
   ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_USAGE}=="filesystem", ENV{ID_USB_DRIVER}=="usb-storage", RUN+="/bin/mkdir -p /media/usb", RUN+="/bin/mount -o defaults,uid=bathycat,gid=bathycat %N /media/usb"
   ACTION=="remove", SUBSYSTEM=="block", ENV{ID_USB_DRIVER}=="usb-storage", RUN+="/bin/umount /media/usb"
   EOF
   
   # Reload udev rules
   sudo udevadm control --reload-rules
   ```

## Hardware Setup

### Camera Connection
1. Connect USB camera to Raspberry Pi USB port
2. Verify detection:
   ```bash
   lsusb | grep -i camera
   ls /dev/video*
   ```

### GPS Connection
1. Connect USB GPS to Raspberry Pi USB port
2. Verify detection:
   ```bash
   lsusb | grep -i gps
   ls /dev/ttyUSB* /dev/ttyACM*
   ```

### USB Storage
1. Format USB drive as exFAT or ext4
2. Label drive as "BATHYCAT" (optional)
3. Connect to Raspberry Pi USB port

### LED Indicators (Optional)
Connect LEDs to GPIO pins (with appropriate resistors):
- Status LED: GPIO 18 (Pin 12)
- Error LED: GPIO 19 (Pin 35)
- Activity LED: GPIO 20 (Pin 38)

## Configuration

### Basic Configuration
Edit `/etc/bathycat/config.json`:

```json
{
  "version": "1.0",
  "system": {
    "environment": "production",
    "capture_interval": 1.0
  },
  "camera": {
    "device_index": 0,
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "jpeg_quality": 95
  },
  "gps": {
    "port": "/dev/ttyUSB0",
    "baudrate": 9600,
    "mock_enabled": false
  },
  "storage": {
    "base_path": "/media/usb",
    "cleanup_days": 30,
    "min_free_space_mb": 1000
  },
  "leds": {
    "enabled": true,
    "status_pin": 18,
    "error_pin": 19,
    "activity_pin": 20
  }
}
```

### Environment-Specific Settings

**Development Environment:**
```json
{
  "system": {
    "environment": "development",
    "capture_interval": 5.0
  },
  "gps": {
    "mock_enabled": true
  },
  "logging": {
    "level": "DEBUG",
    "console_output": true
  }
}
```

**Production Environment:**
```json
{
  "system": {
    "environment": "production",
    "capture_interval": 1.0
  },
  "logging": {
    "level": "INFO",
    "console_output": false
  }
}
```

## Testing Installation

### Hardware Tests
```bash
# Test camera
ffplay /dev/video0

# Test GPS (should show NMEA sentences)
sudo cat /dev/ttyUSB0

# Test USB storage
df -h /media/usb
```

### Service Tests
```bash
# Check service status
sudo systemctl status bathycat

# View logs
sudo journalctl -u bathycat -f

# Manual test
cd /opt/bathycat
sudo -u bathycat ./venv/bin/python -m bathycat.main
```

### Configuration Tests
```bash
# Validate configuration
cd /opt/bathycat/src && sudo python3 -m config --validate

# Show detected hardware
cd /opt/bathycat/src && sudo python3 -m config --show-hardware

# Basic system test
python3 tests/run_basic_tests.py
```

## Troubleshooting Installation

### Common Issues

#### Permission Errors
```bash
# Fix ownership
sudo chown -R pi:pi /opt/bathycat
sudo chown -R bathycat:bathycat /var/log/bathycat

# Fix user groups
sudo usermod -a -G video,dialout,plugdev pi
sudo usermod -a -G video,dialout,plugdev bathycat
```

#### Camera Not Detected
```bash
# Check USB connection
lsusb

# Check video devices
ls -la /dev/video*

# Test camera permissions
sudo usermod -a -G video $USER
# (logout and login required)
```

#### GPS Not Working
```bash
# Check USB GPS
lsusb | grep -i gps

# Check serial devices
ls -la /dev/ttyUSB* /dev/ttyACM*

# Test GPS data
sudo cat /dev/ttyUSB0
# Should show NMEA sentences

# Fix permissions
sudo usermod -a -G dialout $USER
```

#### Python Dependencies
```bash
# Reinstall in virtual environment
cd /opt/bathycat
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Service Not Starting
```bash
# Check service logs
sudo journalctl -u bathycat --no-pager

# Check configuration
cd /opt/bathycat/src && sudo python3 -m config --validate

# Manual service test
sudo systemctl stop bathycat
cd /opt/bathycat
sudo -u bathycat ./venv/bin/python -m bathycat.main
```

#### Storage Issues
```bash
# Check USB mount
lsblk
mount | grep usb

# Manual mount
sudo mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb
sudo chown bathycat:bathycat /media/usb

# Check disk space
df -h /media/usb
```

### Recovery Procedures

#### Reset Configuration
```bash
# Backup current config
sudo cp /etc/bathycat/config.json /etc/bathycat/config.json.backup

# Create new default config
cd /opt/bathycat/src && sudo python3 -m config --create-default

# Restart service
sudo systemctl restart bathycat
```

#### Reinstall Service
```bash
# Stop and disable service
sudo systemctl stop bathycat
sudo systemctl disable bathycat

# Remove service file
sudo rm /etc/systemd/system/bathycat.service

# Reinstall
sudo cp /opt/bathycat/scripts/bathycat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bathycat
sudo systemctl start bathycat
```

#### Factory Reset
```bash
# Complete reinstallation
sudo ./scripts/install.sh --reset
```

## Next Steps

After successful installation:

1. **Configure for your environment** - Edit `/etc/bathycat/config.json`
2. **Test thoroughly** - Run system for several hours
3. **Monitor performance** - Check logs and storage usage
4. **Set up remote access** - Configure SSH and monitoring
5. **Plan maintenance** - Schedule regular updates and cleanup

## Support

- **GitHub Issues**: Report problems and request features
- **Documentation**: Check README.md for operational details  
- **Logs**: Always check `/var/log/bathycat/` for troubleshooting