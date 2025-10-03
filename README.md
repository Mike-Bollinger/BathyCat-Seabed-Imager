# BathyCat Seabed Imager 🌊📷

A complete underwater imaging system for the Raspberry Pi 4, designed to capture high-frequency seabed images with GPS tagging and precise time synchronization.

> **🔧 System Status**: All major issues have been resolved! See [SYSTEM_CORRECTIONS.md](SYSTEM_CORRECTIONS.md) for details.

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
