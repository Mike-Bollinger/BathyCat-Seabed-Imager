# BathyCat Seabed Imager 🌊📷

A complete underwater imaging system for the Raspberry Pi 4, designed to capture high-frequency seabed images with GPS tagging and precise time synchronization.

> **🎉 System Status**: **FULLY OPERATIONAL!** All issues resolved and system tested at 4-5 images/second capture rate. See [SYSTEM_CORRECTIONS.md](SYSTEM_CORRECTIONS.md) for complete fix details.

## System Overview

This system captures seabed images using a USB camera, tags them with GPS coordinates and precise timestamps, and stores them on local USB storage for later retrieval.

### Hardware Components

- **Raspberry Pi 4 Model B (4GB)** - Main processing unit
- **StellarHD USB Camera (H.264)** - Underwater imaging (1080p@30fps capable)
- **512GB USB 3.0 Flash Drive** - High-speed local storage (exFAT/NTFS/ext4 supported)
- **Adafruit Mini GPS PA1010D - USB Version** - GPS positioning and time sync
- **Waterproof housing** - Protection for Pi and connections

### Key Features

- **✅ High-frequency capture**: 4+ images per second with fswebcam fallback
- **✅ GPS tagging**: Each image tagged with precise location
- **✅ Time synchronization**: GPS-based time sync for data correlation
- **✅ Efficient storage**: Organized file structure with metadata
- **✅ Robust logging**: Comprehensive system and error logging with emojis
- **✅ Auto-start capability**: Runs automatically on boot via systemd
- **✅ Error recovery**: Individual component error handling prevents system crashes
- **✅ Multi-filesystem USB**: Supports exFAT, VFAT, ext4, NTFS storage devices
- **✅ Integrated USB mounting**: Automatic USB detection and mounting within the application
- **✅ Comprehensive testing**: Full system verification with automated tests

## Quick Start

### 🚀 New Installation (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

# 2. Run complete installation
sudo ./scripts/install_complete.sh

# 3. Reboot system  
sudo reboot

# 4. Setup USB storage (after connecting hardware)
sudo /opt/bathycat/setup_usb_storage.sh

# 5. Start service
sudo systemctl start bathycat-imager
```

### 🔍 Verification
```bash
# Test all components
python3 tests/test_system.py

# Check system status
/opt/bathycat/status.sh

# View live logs
journalctl -u bathycat-imager -f
```

## Troubleshooting

### 🚨 Common Issues and Solutions

If you encounter issues during installation or operation, here are the most common problems and their solutions:

#### **Issue 1: Service Fails to Start - OpenCV Import Error**
**Symptoms**: `ImportError: libGL.so.1: cannot open shared object file`
```bash
# Solution: Install OpenGL libraries
sudo apt update
sudo apt install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev
```

#### **Issue 2: Missing Python Dependencies**
**Symptoms**: `ModuleNotFoundError: No module named 'piexif'` or `'psutil'`
```bash
# Solution: Install missing packages in virtual environment
source /home/bathyimager/bathycat-venv/bin/activate
pip install piexif psutil aiofiles
# Or install all requirements
pip install -r ~/BathyCat-Seabed-Imager/requirements.txt
```

#### **Issue 3: USB Storage Permission Denied**
**Symptoms**: `PermissionError: [Errno 13] Permission denied: '/media/usb-storage/bathycat'`
```bash
# NEW: The system now uses integrated USB management
# USB mounting is handled automatically by the application
# Check service logs for USB mounting status:
journalctl -u bathycat-imager | grep -i usb

# Legacy solution (if needed):
sudo umount /media/usb-storage
sudo mount -o uid=bathyimager,gid=bathyimager,umask=0022 /dev/sda1 /media/usb-storage
```

#### **Issue 4: USB Drive Not Detected**
**Symptoms**: No USB storage visible or "BathyCat USB drive not found"
```bash
# NEW: Check integrated USB detection logs
journalctl -u bathycat-imager | grep -E "(USB|FCDF-E63E|BATHYCAT)"

# Verify USB drive has correct label and UUID
lsblk -f | grep -E "BATHYCAT|FCDF-E63E"

# Check connected drives
lsblk
lsusb | grep -i storage

# Manual mount if auto-mount fails (legacy)
sudo mkdir -p /media/usb-storage
sudo mount /dev/sda1 /media/usb-storage
```

#### **Issue 5: GPS No Fix (Indoor Testing)**
**Symptoms**: GPS data shows `null` values
```bash
# This is normal indoors - GPS needs satellite signals
# For outdoor testing, check GPS status:
journalctl -u bathycat-imager | grep gps

# GPS typically takes 30-60 seconds to get first fix outdoors
```

### 📋 **Complete Troubleshooting Checklist**

If the service won't start, work through these steps:

1. **Check service status**:
   ```bash
   sudo systemctl status bathycat-imager
   journalctl -u bathycat-imager -n 20
   ```

2. **Verify dependencies**:
   ```bash
   # System dependencies
   dpkg -l | grep -E "libgl1|libglib2.0-0|libsm6"
   
   # Python dependencies
   source /home/bathyimager/bathycat-venv/bin/activate
   python3 -c "import cv2, piexif, psutil, aiofiles; print('All imports OK')"
   ```

3. **Check USB storage**:
   ```bash
   df -h | grep usb-storage
   ls -la /media/usb-storage/bathycat/
   touch /media/usb-storage/bathycat/test_write  # Test write permissions
   ```

4. **Manual test run**:
   ```bash
   cd /opt/bathycat
   source /home/bathyimager/bathycat-venv/bin/activate
   python3 bathycat_imager.py --config /etc/bathycat/bathycat_config.json --verbose
   ```

### ✅ **Expected Working Status**

When everything is working correctly, you should see:

```bash
$ sudo systemctl status bathycat-imager
● bathycat-imager.service - BathyCat Seabed Imager
     Active: active (running)
     
$ journalctl -u bathycat-imager -n 5
# Should show image capture logs like:
# "Camera configured: 1920x1080 @ 5.0fps"
# "Image OK, shape: (1080, 1920, 3)"
# "GPS data type: <class 'dict'>"
# "Image processing complete"

$ ls /media/usb-storage/bathycat/images/$(date +%Y%m%d_%H)/ | wc -l
# Should show growing number of .jpg files
```

**Performance Indicators**:
- **Capture Rate**: ~4-5 images per second
- **Image Size**: 35-40KB per 1920x1080 JPEG
- **File Organization**: Date/time folders (YYYYMMDD_HH)
- **Metadata**: JSON files with timestamps and GPS data structure

## Updates

### 🔄 Updating Existing Installation

To update the BathyCat system on your Raspberry Pi:

```bash
./update --force
```

This will:
- ✅ Check for new updates from GitHub (fixed bash syntax)
- ✅ Backup your configuration  
- ✅ Pull the latest code
- ✅ Update dependencies
- ✅ Restart services automatically
- ✅ Test the update

### 🆕 Fresh Installation (Recommended for v2.0+)

If you're upgrading from an older version or want a clean install:

```bash
# Complete system installation with all fixes
sudo ./scripts/install_complete.sh
```

This provides:
- ✅ All system corrections applied
- ✅ Proper error handling and logging
- ✅ Robust USB storage detection
- ✅ Service integration fixes
- ✅ Comprehensive system testing

### Development Updates (Windows)

When developing on Windows, use:

```powershell
# PowerShell
.\update.ps1

# Or Command Prompt
update.bat
```

Then push changes to make them available on the Pi:

```bash
git add .
git commit -m "Your update message"
git push origin main
```

## Project Structure

```
BathyCat-Seabed-Imager/
├── src/
│   ├── bathycat_imager.py     # Main application
│   ├── camera_controller.py   # Camera interface
│   ├── gps_controller.py      # GPS handling
│   ├── image_processor.py     # Image processing and tagging
│   ├── storage_manager.py     # File management
│   └── config.py             # Configuration settings
├── scripts/
│   ├── install.sh            # Installation script
│   ├── setup_services.sh     # Service configuration
│   ├── setup_usb_storage.sh  # USB storage setup
│   └── start_capture.sh      # Startup script
├── tests/
│   ├── test_components.py    # System tests
│   └── test_camera_capture.py # Camera testing with USB storage
├── config/
│   ├── bathycat_config.json  # Main configuration
│   └── logging.conf          # Logging configuration
├── docs/
│   ├── INSTALLATION.md       # Detailed setup guide
│   ├── HARDWARE_SETUP.md     # Hardware configuration
│   ├── TROUBLESHOOTING.md    # Common issues and solutions
│   └── API.md               # Code documentation
├── update                    # Quick update script (Linux/Pi)
├── update.ps1               # Update script (Windows PowerShell)
├── update.bat               # Update script (Windows Batch)
└── README.md                # This file
```

## Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Complete setup instructions
- **[Hardware Setup](docs/HARDWARE_SETUP.md)** - Physical configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[API Documentation](docs/API.md)** - Code reference

## System Requirements

- Raspberry Pi 4 Model B (4GB recommended)
- Raspberry Pi OS Lite (64-bit) - Bullseye or later
- 32GB+ microSD card (for OS)
- 512GB USB 3.0 Flash Drive (for image storage)
- USB 3.0 camera (StellarHD or compatible)
- USB GPS module with antenna

## Disclaimer

This repository is a scientific product and is not official communication of the National Oceanic and Atmospheric Administration, or the United States Department of Commerce. All NOAA GitHub project code is provided on an 'as is' basis and the user assumes responsibility for its use. Any claims against the Department of Commerce or Department of Commerce bureaus stemming from the use of this GitHub project will be governed by all applicable Federal law. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by the Department of Commerce. The Department of Commerce seal and logo, or the seal and logo of a DOC bureau, shall not be used in any manner to imply endorsement of any commercial product or activity by DOC or the United States Government.

## License

Software code created by U.S. Government employees is not subject to copyright in the United States (17 U.S.C. §105). The United States/Department of Commerce reserve all rights to seek and obtain copyright protection in countries other than the United States for Software authored in its entirety by the Department of Commerce. To this end, the Department of Commerce hereby grants to Recipient a royalty-free, nonexclusive license to use, copy, and create derivative works of the Software outside of the United States.
