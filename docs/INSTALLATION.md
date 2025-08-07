# BathyCat Seabed Imager - Complete Installation Guide

This guide provides step-by-step instructions for setting up the BathyCat Seabed Imager system on a Raspberry Pi 4.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Raspberry Pi OS Installation](#raspberry-pi-os-installation)
3. [Hardware Assembly](#hardware-assembly)
4. [Software Installation](#software-installation)
5. [System Configuration](#system-configuration)
6. [Testing and Validation](#testing-and-validation)
7. [Deployment](#dep4. **Storage Issues**
   - Check mount status: `mount | grep usb-storage`
   - Verify permissions: `ls -la /media/usb-storage/bathycat`
   - Check disk space: `df -h`ent)
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

3. **512GB USB 3.0 Flash Drive** - High-speed marine-grade recommended
   - High-speed storage for image data
   - USB 3.0 interface for optimal transfer rates
   - Marine-grade waterproof housing preferred

4. **Adafruit Mini GPS PA1010D - USB Version** - [Adafruit Link](https://www.adafruit.com/product/4279)
   - GPS positioning and time synchronization  
   - USB interface for easy connection
   - Built-in antenna with uFL connector for external antenna

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
   - **BEFORE clicking "Write"**, click the **gear icon (⚙️)** for advanced options

3. **Configure Advanced Settings (Recommended)**
   
   **In the Advanced Options dialog:**
   
   **SSH Configuration:**
   - ✅ **Enable SSH**
   - Select **"Use password authentication"**
   
   **User Account:**
   - ✅ **Set username and password**
   - Username: `bathyimager` (or your preferred username)
   - Password: `bathyimager` (or your secure password)
   - *Note: This replaces the default pi/raspberry credentials*
   
   **WiFi Configuration:**
   - ✅ **Configure WiFi**
   - SSID: `YourWiFiName` (e.g., "Nacho_Wifi")
   - Password: `YourWiFiPassword`
   - WiFi country: `US` (or your country)
   
   **Locale Settings:**
   - ✅ **Set locale settings**
   - Time zone: Select your timezone
   - Keyboard layout: `us` (or your layout)
   
   **Other Options:**
   - ✅ **Enable telemetry** (optional, helps Raspberry Pi Foundation)
   - Click **"SAVE"**
   
   - Click **"Write"** to flash the card

4. **Alternative Setup Methods**

   **Method A - Modern Raspberry Pi Imager (Recommended Above)**
   - All configuration done before flashing
   - No manual file creation needed
   - WiFi and SSH configured automatically
   
   **Method B - Manual File Configuration (Legacy/Backup)**
   
   *Use this if the advanced options don't work or for older Raspberry Pi Imager versions:*
   
   ```bash
   # After flashing, on the boot partition, create:
   touch ssh
   
   # For WiFi, create wpa_supplicant.conf:
   nano wpa_supplicant.conf
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

5. **First Boot Setup**

   **Connection Methods:**

   **Method 1 - WiFi Connection (Using Raspberry Pi Imager Advanced Options)**
   
   *If you configured WiFi in the Raspberry Pi Imager (recommended):*
   
   1. **Insert SD card** into Raspberry Pi and power on
   2. **Wait 2-3 minutes** for boot and WiFi connection
   3. **Find Pi on your network** using one of these methods:

   **Finding the Raspberry Pi IP Address:**
   
   **Option A - Router Admin Panel (Easiest):**
   ```
   1. Access your router's admin interface:
      - Common addresses: http://192.168.1.1, http://192.168.0.1, http://10.0.0.1
      - Check router label for login credentials
   2. Look for "Connected Devices", "DHCP Clients", or "Device List"
   3. Find device named "bathyimager" (your custom hostname) or "raspberrypi"
   4. Note the assigned IP address (e.g., 192.168.1.100)
   ```
   
   **Option B - Advanced IP Scanner (Windows):**
   ```
   1. Download: https://www.advanced-ip-scanner.com/
   2. Install and run Advanced IP Scanner
   3. Scan your network range (it auto-detects)
   4. Look for device with manufacturer "Raspberry Pi Foundation"
   5. Note the IP address
   ```
   
   **Option C - Network Scan (Windows PowerShell):**
   ```powershell
   # First check your network range
   ipconfig
   # Look for your WiFi adapter's network (e.g., 192.168.1.x)
   
   # Scan for Pi (replace network range as needed)
   1..254 | ForEach-Object { 
       if (Test-Connection -ComputerName "192.168.1.$_" -Count 1 -Quiet -TimeoutSeconds 1) { 
           Write-Host "192.168.1.$_ is responding" 
       } 
   }
   ```

   **Option D - Try Hostname Resolution:**
   ```powershell
   # Try pinging the hostname
   ping bathyimager.local     # Your custom hostname
   ping raspberrypi.local     # Default hostname
   
   # If ping responds, use that for SSH
   ```

   **Method 2 - Direct Ethernet Connection (Alternative)**
   
   *Use this if WiFi setup fails or for isolated setup:*

   **Step 1: Configure Your Windows PC**
   1. **Open Network Settings:** Press `Windows + R`, type `ncpa.cpl`, press Enter
   2. **Right-click Ethernet adapter** → Properties
   3. **Double-click "Internet Protocol Version 4 (TCP/IPv4)"**
   4. **Select "Use the following IP address":**
      ```
      IP address: 192.168.100.1
      Subnet mask: 255.255.255.0
      Default gateway: (leave blank)
      DNS servers: (leave blank)
      ```
   5. **Click OK** twice

   **Step 2: Configure Pi for Static IP**
   1. **Power down Pi**, remove SD card, insert in PC
   2. **Edit cmdline.txt** on boot partition
   3. **Add to END of line** (don't create new line):
      ```
      ip=192.168.100.2::192.168.100.1:255.255.255.0:rpi:eth0:off
      ```
   4. **Connect Ethernet cable** between PC and Pi
   5. **Power on Pi**, wait 2-3 minutes
   6. **Test connection:** `ping 192.168.100.2`
   7. **SSH to:** `192.168.100.2`

   **Method 3 - Router Ethernet Connection (Standard)**
   
   *Traditional Ethernet connection through router:*
   1. **Connect Pi to router** with Ethernet cable
   2. **Power on Pi**, wait 2-3 minutes
   3. **Find IP** using router admin panel or network scan
   4. **SSH to discovered IP**

   **SSH Connection:**
   
   **Using PuTTY (Windows):**
   ```
   1. Download PuTTY from: https://www.putty.org/
   2. Launch PuTTY
   3. Configuration:
      - Host Name: [IP address found above] or bathyimager.local
      - Port: 22
      - Connection Type: SSH
   4. Click "Open"
   5. Security Alert: Click "Accept" (first time only)
   6. Login credentials:
      - Username: bathyimager (or your custom username)
      - Password: bathyimager (or your custom password)
   ```
   
   **Using Windows PowerShell/Command Prompt:**
   ```powershell
   # Windows 10/11 has built-in SSH client
   ssh bathyimager@192.168.1.100    # Replace with actual IP
   # OR try hostname resolution
   ssh bathyimager@bathyimager.local
   # OR fallback to default if not changed
   ssh pi@raspberrypi.local
   ```
   
   **Using Linux/macOS Terminal:**
   ```bash
   # Standard SSH command
   ssh bathyimager@192.168.1.100    # Replace with actual IP
   # OR try hostname resolution  
   ssh bathyimager@bathyimager.local
   ```

   **Initial System Setup:**
   ```bash
   # After successful SSH connection:
   
   # If using custom username/password (bathyimager), you can optionally change it again
   passwd
   # Enter new password when prompted (twice for confirmation)
   
   # If using default pi/raspberry credentials, CHANGE PASSWORD IMMEDIATELY:
   passwd
   # Enter new secure password
   
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Enable required interfaces
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   # Navigate to: Interface Options > Serial Port > Enable
   # Navigate to: Interface Options > SSH > Enable (should already be enabled)
   # Select "Finish" and reboot when prompted
   
   # System will reboot - reconnect after ~2 minutes
   ```

   **Troubleshooting SSH Connection:**
   
   **If using custom username/password (bathyimager/bathyimager):**
   - Try both the hostname: `ssh bathyimager@bathyimager.local`
   - And the IP address: `ssh bathyimager@192.168.1.100`
   - Ensure you're using YOUR custom credentials, not pi/raspberry
   
   **If using default credentials or fallback:**
   - Username: `pi`, Password: `raspberry`
   - Try: `ssh pi@raspberrypi.local`
   
   **Common Issues:**
   - **Wrong credentials**: Double-check username/password you set in Raspberry Pi Imager
   - **Hostname not resolving**: Use IP address instead of .local hostname
   - **WiFi connection failed**: Check router's connected devices list
   - **SSH not enabled**: If using manual setup, verify SSH file exists on boot partition
   
   **If connection is refused:**
   - Wait longer (Pi might still be booting)
   - Check Pi's power LED (should be solid red when fully booted)
   - Verify Pi appears in router's device list
   
   **If login fails:**
   - Verify the exact username/password you configured in Raspberry Pi Imager
   - Username and password are case-sensitive
   - Try default pi/raspberry if you didn't change credentials

---

### SSH Connection Troubleshooting

**Important Note: Custom Username Configuration**

If you changed the default username from `pi` to `bathyimager` (or another custom name), you'll need to update several configuration files during the software installation process:

```bash
# After SSH connection, verify your username
whoami
# Should show: bathyimager (or your custom username)

# During software installation, you may need to update:
# - Service user in systemd files
# - File ownership commands
# - Directory permissions
```

**Problem: Cannot find Raspberry Pi IP address**

Solutions:
1. **Check router DHCP reservations**: Many routers allow you to reserve IP addresses for specific MAC addresses
2. **Use Raspberry Pi IP Scanner**: Download "Angry IP Scanner" or similar network scanning tool
3. **Check Pi is actually connected**: 
   - Ethernet: Look for link lights on Pi and switch/router
   - WiFi: Check router's wireless client list

**Problem: "Connection refused" or "Host unreachable"**

Solutions:
1. **Verify SSH is enabled**: 
   ```bash
   # Check if SSH file exists on SD card boot partition
   ls /boot/ssh  # Should exist and be empty
   ```
2. **Wait for full boot**: Pi needs 1-2 minutes to fully boot and start SSH service
3. **Check network connectivity**:
   ```bash
   # From your computer, ping the Pi
   ping 192.168.1.100  # Replace with Pi's IP
   ```

**Problem: "Permission denied" or login failures**

Solutions:
1. **Verify credentials**:
   - Default username: `pi` (lowercase)
   - Default password: `raspberry` (lowercase)
   - Both are case-sensitive
2. **SSH keys conflict** (if you've used SSH keys before):
   ```bash
   # Remove old host key entry
   ssh-keygen -R raspberrypi.local
   ssh-keygen -R 192.168.1.100  # Replace with actual IP
   ```

**Problem: PuTTY-specific issues**

Solutions:
1. **Font/Display issues**: Use default settings, avoid unusual fonts
2. **Connection hanging**: Check firewall settings on Windows
3. **Key exchange failures**: 
   - In PuTTY, go to Connection > SSH > KEX
   - Move "diffie-hellman-group14-sha1" to top of list

**Recommended PuTTY Configuration:**
```
Connection > Data:
- Auto-login username: pi
- Terminal-type string: xterm

Connection > SSH:
- SSH protocol version: 2 only
- Enable compression: Yes

Session:
- Save session as "BathyCat-Pi" for future use
```

## Hardware Assembly

### 1. Raspberry Pi Setup

1. **Connect USB GPS**
   - Connect Adafruit Mini GPS PA1010D to any available USB port
   - GPS will be auto-detected by the software

2. **Connect USB Storage**
   - Connect 512GB USB 3.0 flash drive to USB 3.0 port (blue port)
   - Ensure secure connection and waterproof protection if external

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
   
   **Option A: Git Clone (Recommended)**
   ```bash
   # Install Git if not present
   sudo apt update
   sudo apt install -y git
   
   # Clone the repository
   git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
   cd BathyCat-Seabed-Imager
   ```
   
   **Option B: Download ZIP Archive**
   ```bash
   # Install wget and unzip if not present
   sudo apt update
   sudo apt install -y wget unzip
   
   # Download and extract project
   wget https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/archive/main.zip
   unzip main.zip
   cd BathyCat-Seabed-Imager-main
   ```
   
   **Option C: Manual Transfer (if GitHub not accessible)**
   ```bash
   # Transfer files from your development computer using SCP
   # On Windows PowerShell:
   # scp -r "C:\Users\Mike.Bollinger\Documents\Python\BathyCat-Seabed-Imager" bathyimager@[PI_IP]:~/
   
   # On Raspberry Pi:
   cd ~/BathyCat-Seabed-Imager
   ```

2. **Run Installation Script**
   ```bash
   # Ensure you're in the project directory
   # For Git clone: cd BathyCat-Seabed-Imager
   # For ZIP download: cd BathyCat-Seabed-Imager-main
   
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
                       chrony \
                       git cmake pkg-config
   ```
   
   **Note:** GPSD is no longer required with USB GPS - the software communicates directly with the GPS device.

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

1. **Mount USB Flash Drive**
   ```bash
   # Find USB flash drive device
   lsblk
   
   # Format USB drive (if new) - WARNING: This will erase all data
   sudo mkfs.ext4 /dev/sda1
   
   # Create mount point
   sudo mkdir -p /media/usb-storage
   
   # Get UUID
   sudo blkid /dev/sda1
   
   # Add to fstab
   sudo nano /etc/fstab
   # Add line: UUID=your-uuid /media/usb-storage ext4 defaults,noatime 0 2
   
   # Mount
   sudo mount -a
   ```

2. **Create Directory Structure**
   ```bash
   sudo mkdir -p /media/usb-storage/bathycat/{images,metadata,previews,logs,exports}
   sudo chown -R pi:pi /media/usb-storage/bathycat
   ```

### 2. GPS Configuration

**USB GPS Setup (Automatic Detection)**

The Adafruit Mini GPS PA1010D connects via USB and is automatically detected by the software.

1. **Verify GPS Connection**
   ```bash
   # Check if GPS device is detected
   lsusb
   # Look for Adafruit device or USB-Serial adapter
   
   # Check available serial ports  
   ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No USB serial devices found"
   
   # List detailed USB serial devices
   python3 -c "
   import serial.tools.list_ports
   for port in serial.tools.list_ports.comports():
       print(f'{port.device}: {port.description}')
   "
   ```

2. **Test GPS Communication** 
   ```bash
   # If GPS is detected as /dev/ttyUSB0 or /dev/ttyACM0, test it:
   sudo cat /dev/ttyUSB0
   # You should see NMEA sentences like $GPGGA, $GPRMC, etc.
   # Press Ctrl+C to stop
   ```

3. **Optional: Manual GPS Port Configuration**
   
   *Only needed if auto-detection fails:*
   ```bash
   # Edit configuration to specify exact port
   sudo nano /etc/bathycat/config.json
   
   # Change "gps_port": "auto" to specific port:
   # "gps_port": "/dev/ttyUSB0"    # or whatever port your GPS uses
   ```

**Note:** Unlike the GPS HAT, the USB GPS does not require:
- UART configuration in `/boot/config.txt`
- GPSD installation or configuration
- Disabling Bluetooth on UART

The USB GPS is plug-and-play!

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
   After=network.target

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
   df -h /media/usb-storage
   
   # Test write permissions
   echo "test" > /media/usb-storage/bathycat/test.txt
   cat /media/usb-storage/bathycat/test.txt
   rm /media/usb-storage/bathycat/test.txt
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
   rsync -av /media/usb-storage/bathycat/ user@shore-computer:/path/to/backup/
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
   - Check mount status: `mount | grep usb-storage`
   - Verify permissions: `ls -la /media/usb-storage/bathycat`
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
