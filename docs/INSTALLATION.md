# BathyCat Seabed Imager - Complete Installation Guide

This guide provides step-by-step instructions for setting up the BathyCat Seabed Imager system on a Raspberry Pi 4.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Raspberry Pi OS Installation](#raspberry-pi-os-installation)
3. [Hardware Assembly](#hardware-assembly)
4. [Software Installation](#software-installation)
5. [System Configuration](#system-configuration)
6. [Testing and Validation](#testing-and-validation)
7. [Deployment](#deployment)
8. [Maintenance](#maintenance)

---

## Hardware Requirements

### Core Components

1. **Raspberry Pi 4 Model B (4GB)** - [SparkFun Link](https://www.sparkfun.com/raspberry-pi-4-model-b-4-gb.html)
   - 4GB RAM model recommended for optimal performance
   - Includes power supply (5V/3A USB-C)

2. **StellarHD USB Camera** - [DWE.ai Link](https://dwe.ai/products/stellarhd)
   - 1080p@30fps capable
   - USB 3.0 for high-speed data transfer
   - Waterproof housing included

3. **512GB SSD Storage Kit** - [SparkFun Link](https://www.sparkfun.com/raspberry-pi-ssd-kit-for-raspberry-pi-512gb.html)
   - High-speed storage for image data
   - Includes USB 3.0 to SATA adapter

4. **Adafruit Ultimate GPS HAT** - [Adafruit Link](https://www.adafruit.com/product/5440)
   - GPS positioning and time synchronization
   - Built-in battery backup
   - PPS (Pulse Per Second) support

### Additional Requirements

- **MicroSD Card**: 32GB Class 10 (for Raspberry Pi OS)
- **Ethernet Cable**: For initial setup and data transfer
- **Waterproof Enclosure**: For marine environment protection
- **USB Extension Cable**: For camera deployment (marine-grade)
- **Power Bank**: Marine-grade 12V to 5V converter or battery system

---

## Raspberry Pi OS Installation

### Recommended OS

**Raspberry Pi OS Lite (64-bit)** - Bullseye or newer
- Lightweight without desktop environment
- Better performance for headless operation
- Full 64-bit support for better performance

### Installation Steps

1. **Download Raspberry Pi Imager**
   ```bash
   # On Windows/Mac/Linux
   # Download from: https://www.raspberrypi.org/software/
   ```

2. **Flash OS to MicroSD**
   - Insert 32GB+ microSD card
   - Run Raspberry Pi Imager
   - Choose "Raspberry Pi OS Lite (64-bit)"
   - Select your microSD card
   - Click "Write"

3. **Enable SSH (Headless Setup)**
   ```bash
   # After flashing, on the boot partition, create:
   touch /boot/ssh
   
   # For WiFi, create wpa_supplicant.conf:
   nano /boot/wpa_supplicant.conf
   ```

   ```conf
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   
   network={
       ssid="YourWiFiName"
       psk="YourWiFiPassword"
   }
   ```

4. **First Boot Setup**
   ```bash
   # Insert SD card and boot Pi
   # SSH into the Pi (default password: raspberry)
   ssh pi@raspberrypi.local
   
   # Change default password
   passwd
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Enable interfaces
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   # Navigate to: Interface Options > Serial Port > Enable
   # Reboot when prompted
   ```

---

## Hardware Assembly

### 1. Raspberry Pi Setup

1. **Install GPS HAT**
   - Power down Raspberry Pi
   - Carefully attach GPS HAT to GPIO pins
   - Ensure proper alignment and connection

2. **Connect SSD Storage**
   - Connect SSD to USB 3.0 port (blue port)
   - Ensure secure connection

3. **Connect Camera**
   - Connect StellarHD camera to remaining USB 3.0 port
   - If using extension cable, ensure marine-grade waterproofing

### 2. Waterproof Enclosure Setup

1. **Enclosure Selection**
   - Choose marine-grade IP67+ rated enclosure
   - Ensure space for heat dissipation
   - Include cable glands for connections

2. **Cable Management**
   - Use marine-grade cable glands
   - Seal all penetrations properly
   - Leave service loop for maintenance

3. **Ventilation and Cooling**
   - Install heat sinks on Raspberry Pi
   - Consider small fan for active cooling
   - Ensure moisture protection

### 3. Power System

1. **Marine Power Supply**
   - 12V to 5V DC converter (marine grade)
   - Minimum 4A output capacity
   - Overcurrent and reverse polarity protection

2. **Backup Power (Optional)**
   - UPS for continuous operation
   - Battery backup for GPS clock
   - Auto-shutdown on low power

---

## Software Installation

### Automated Installation

1. **Download Project**
   ```bash
   # Clone or download the project
   wget https://github.com/your-repo/bathycat-seabed-imager/archive/main.zip
   unzip main.zip
   cd bathycat-seabed-imager-main
   ```

2. **Run Installation Script**
   ```bash
   # Make script executable
   chmod +x scripts/install.sh
   
   # Run installation (requires sudo)
   sudo scripts/install.sh
   ```

3. **Installation Process**
   The script will automatically:
   - Update system packages
   - Install Python dependencies
   - Configure GPS and camera
   - Set up storage structure
   - Create systemd service
   - Configure logging
   - Create utility scripts

### Manual Installation (Alternative)

If automated installation fails, follow these manual steps:

1. **System Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv \
                       python3-opencv libopencv-dev \
                       gpsd gpsd-clients chrony \
                       git cmake pkg-config
   ```

2. **Python Environment**
   ```bash
   # Create virtual environment
   sudo mkdir -p /opt/bathycat
   sudo python3 -m venv /opt/bathycat/venv
   sudo /opt/bathycat/venv/bin/pip install --upgrade pip
   
   # Install Python packages
   sudo /opt/bathycat/venv/bin/pip install \
       opencv-python numpy pillow pyserial \
       pynmea2 psutil piexif asyncio-mqtt aiofiles
   ```

3. **Copy Application Files**
   ```bash
   sudo cp -r src/ /opt/bathycat/
   sudo cp config/bathycat_config.json /etc/bathycat/config.json
   sudo chown -R pi:pi /opt/bathycat
   ```

---

## System Configuration

### 1. Storage Configuration

1. **Mount SSD Storage**
   ```bash
   # Find SSD device
   lsblk
   
   # Format SSD (if new)
   sudo mkfs.ext4 /dev/sda1
   
   # Create mount point
   sudo mkdir -p /media/ssd
   
   # Get UUID
   sudo blkid /dev/sda1
   
   # Add to fstab
   sudo nano /etc/fstab
   # Add line: UUID=your-uuid /media/ssd ext4 defaults,noatime 0 2
   
   # Mount
   sudo mount -a
   ```

2. **Create Directory Structure**
   ```bash
   sudo mkdir -p /media/ssd/bathycat/{images,metadata,previews,logs,exports}
   sudo chown -R pi:pi /media/ssd/bathycat
   ```

### 2. GPS Configuration

1. **Configure Serial Port**
   ```bash
   # Edit boot config
   sudo nano /boot/config.txt
   
   # Add these lines:
   enable_uart=1
   dtoverlay=disable-bt
   ```

2. **Configure GPSD**
   ```bash
   sudo nano /etc/default/gpsd
   ```
   
   ```bash
   START_DAEMON="true"
   USBAUTO="false"
   DEVICES="/dev/serial0"
   GPSD_OPTIONS="-n -s 9600"
   ```

3. **Test GPS**
   ```bash
   sudo systemctl start gpsd
   cgps -s
   # Should show GPS data when fix is acquired
   ```

### 3. Camera Configuration

1. **Test Camera**
   ```bash
   # List USB devices
   lsusb
   
   # Test with v4l2
   v4l2-ctl --list-devices
   
   # Test capture
   ffmpeg -f v4l2 -i /dev/video0 -frames 1 test.jpg
   ```

2. **Optimize Camera Settings**
   ```bash
   # Set camera parameters for underwater
   v4l2-ctl --set-ctrl=exposure_auto=1
   v4l2-ctl --set-ctrl=white_balance_temperature_auto=0
   v4l2-ctl --set-ctrl=white_balance_temperature=4000
   ```

### 4. System Service Configuration

1. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/bathycat-imager.service
   ```

   ```ini
   [Unit]
   Description=BathyCat Seabed Imager
   After=network.target gpsd.service
   Wants=gpsd.service

   [Service]
   Type=simple
   User=pi
   Group=pi
   WorkingDirectory=/opt/bathycat
   Environment=PATH=/opt/bathycat/venv/bin
   ExecStart=/opt/bathycat/venv/bin/python3 /opt/bathycat/src/bathycat_imager.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable Service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable bathycat-imager
   ```

---

## Testing and Validation

### 1. Component Testing

1. **GPS Test**
   ```bash
   # Check GPS fix
   /opt/bathycat/status.sh
   
   # Manual GPS test
   gpspipe -r -n 10
   ```

2. **Camera Test**
   ```bash
   # Test camera capture
   python3 -c "
   import cv2
   cap = cv2.VideoCapture(0)
   ret, frame = cap.read()
   if ret:
       cv2.imwrite('test_image.jpg', frame)
       print('Camera test successful')
   else:
       print('Camera test failed')
   cap.release()
   "
   ```

3. **Storage Test**
   ```bash
   # Check storage space
   df -h /media/ssd
   
   # Test write permissions
   echo "test" > /media/ssd/bathycat/test.txt
   cat /media/ssd/bathycat/test.txt
   rm /media/ssd/bathycat/test.txt
   ```

### 2. System Integration Test

1. **Manual Test Run**
   ```bash
   # Run manually for testing
   cd /opt/bathycat
   source venv/bin/activate
   python3 src/bathycat_imager.py --config /etc/bathycat/config.json --verbose
   ```

2. **Service Test**
   ```bash
   # Start service
   sudo systemctl start bathycat-imager
   
   # Check status
   sudo systemctl status bathycat-imager
   
   # View logs
   journalctl -u bathycat-imager -f
   ```

### 3. Performance Validation

1. **Capture Rate Test**
   ```bash
   # Monitor capture performance
   tail -f /var/log/bathycat/bathycat.log | grep "images captured"
   ```

2. **Resource Monitoring**
   ```bash
   # Monitor system resources
   htop
   iotop
   ```

---

## Deployment

### 1. Pre-Deployment Checklist

- [ ] All hardware connections secure and waterproofed
- [ ] GPS acquiring fix within 5 minutes
- [ ] Camera capturing at target resolution and frame rate
- [ ] Storage mounted and accessible with sufficient free space
- [ ] Service starting automatically on boot
- [ ] Logging system operational
- [ ] Network connectivity (if required)

### 2. Field Deployment

1. **Power System**
   - Connect to boat's 12V system
   - Verify power consumption (expect ~15-20W)
   - Test auto-start on power application

2. **Camera Deployment**
   - Mount camera for optimal seabed viewing
   - Ensure waterproof seal integrity
   - Test focus and image quality

3. **GPS Antenna**
   - Position for clear sky view
   - Verify GPS fix acquisition
   - Test time synchronization

### 3. Operation Verification

1. **Start-up Sequence**
   ```bash
   # Power on and wait for boot
   # Service should start automatically
   
   # Check status via SSH (if available)
   ssh pi@bathycat.local
   /opt/bathycat/status.sh
   ```

2. **Monitor Initial Operation**
   - Verify GPS fix acquisition
   - Confirm image capture start
   - Check storage utilization
   - Monitor system performance

---

## Maintenance

### 1. Regular Maintenance

1. **Weekly Checks**
   - Storage space utilization
   - System logs for errors
   - GPS fix consistency
   - Image capture statistics

2. **Monthly Maintenance**
   - Clean camera lens
   - Check waterproof seals
   - Update system packages
   - Backup critical configurations

### 2. Data Management

1. **Data Retrieval**
   ```bash
   # Export session data
   /opt/bathycat/venv/bin/python3 -c "
   from src.storage_manager import StorageManager
   from src.config import Config
   
   config = Config()
   storage = StorageManager(config)
   
   # List sessions
   sessions = storage.get_session_directories()
   for session in sessions:
       print(f'{session[\"name\"]}: {session[\"file_count\"]} images')
   "
   
   # Manual data copy
   rsync -av /media/ssd/bathycat/ user@shore-computer:/path/to/backup/
   ```

2. **Automated Cleanup**
   ```bash
   # Configure auto-cleanup in config.json
   {
     "auto_cleanup_enabled": true,
     "cleanup_threshold_gb": 10.0,
     "days_to_keep": 30
   }
   ```

### 3. Troubleshooting

Common issues and solutions:

1. **GPS Not Acquiring Fix**
   - Check antenna connection
   - Verify serial port configuration
   - Test with `cgps -s`

2. **Camera Not Detected**
   - Check USB connections
   - Verify camera with `lsusb`
   - Test with `v4l2-ctl --list-devices`

3. **Storage Issues**
   - Check mount status: `mount | grep ssd`
   - Verify permissions: `ls -la /media/ssd/bathycat`
   - Check disk space: `df -h`

4. **Service Not Starting**
   - Check logs: `journalctl -u bathycat-imager`
   - Verify configuration: `sudo systemctl status bathycat-imager`
   - Test manual start: `/opt/bathycat/manual_start.sh`

### 4. System Updates

1. **Software Updates**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Update Python packages
   sudo /opt/bathycat/venv/bin/pip install --upgrade opencv-python numpy pillow
   
   # Restart service
   sudo systemctl restart bathycat-imager
   ```

2. **Configuration Updates**
   ```bash
   # Edit configuration
   sudo nano /etc/bathycat/config.json
   
   # Restart service to apply changes
   sudo systemctl restart bathycat-imager
   ```

---

## Support and Documentation

- **Project Repository**: [GitHub Link]
- **Hardware Documentation**: See `docs/HARDWARE_SETUP.md`
- **API Documentation**: See `docs/API.md`
- **Troubleshooting Guide**: See `docs/TROUBLESHOOTING.md`

For additional support, create an issue in the project repository with:
- System information (`uname -a`)
- Service logs (`journalctl -u bathycat-imager`)
- Configuration file (`/etc/bathycat/config.json`)
- Hardware setup description
