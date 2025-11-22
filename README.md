# BathyCat Seabed Imager

<img src="https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/blob/main/docs/BathyCat-Seabed-Imager_Image.png" alt="BathyCat Seabed Imager" width="50%">

**Autonomous underwater imaging system for marine research and seabed mapping**

## Overview

The BathyCat Seabed Imager captures high-quality geotagged underwater imagery from surface vessels. Originally designed for the BathyCat ASV, this system is modular and can be deployed on various marine platforms.

## Key Features

- **🎯 Precision Timing**: <10ms timestamp accuracy for fast vessel deployment
- **📍 GPS Integration**: High-precision EXIF geotagging with Adafruit GPS HAT
- **💾 Smart Storage**: Date-organized USB storage with automatic management
- **🔄 Autonomous Operation**: Systemd service with automatic startup and recovery
- **📊 Advanced Logging**: Date-stamped logging system with USB storage
- **🛠️ Self-Diagnostics**: Automated troubleshooting and health monitoring
- **💡 LED Status**: 4-LED real-time operational feedback system

## Hardware Requirements

### Core Components
- **Raspberry Pi 4 Model B** (4GB RAM recommended)
- **DWE StellarHD USB Camera** (1080p@30fps capable)  
- **Adafruit Ultimate GPS HAT** (#2324) - Precision GPS with PPS timing
- **SanDisk USB 3.0 Flash Drive** (512GB+ recommended)
- **MicroSD Card** (32GB+ Class 10)

### Optional Components  
- **Status LEDs** (4x with 220Ω resistors)
- **CR1220 Battery** (for GPS HAT RTC backup)
- **Shutdown Button** (Omron B3F-4055 or similar momentary pushbutton)

## 🚀 Quick Start

### 1. System Preparation
```bash
# Update system and clone repository
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager
```

### 2. Hardware Setup
1. **Install GPS HAT**: Power down Pi, install Adafruit Ultimate GPS HAT (#2324)
2. **Connect Camera**: USB 3.0 port (blue connector)
3. **Insert Storage**: USB 3.0 flash drive (512GB+ recommended)
4. **Optional LEDs**: Connect to GPIO pins 18, 23, 24, 25

### 3. Automated Installation
```bash
sudo chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

### 4. Start System
```bash
# Configure system
python3 tests/troubleshoot.py --quick
nano config/bathyimager_config.json  # Adjust settings if needed

# Start service
sudo systemctl start bathyimager
sudo systemctl enable bathyimager
```

### 5. Verify Operation
```bash
sudo systemctl status bathyimager        # Check service status
sudo journalctl -u bathyimager -f        # Monitor real-time logs
ls -la /media/usb/bathyimager/images/    # Verify image capture
```

### LED Status Quick Reference
- **Green (Power)**: Solid = Running | Off = Stopped
- **Blue (GPS)**: Solid = GPS fix | Blinking = Searching
- **Yellow (Camera)**: Flashes = Image captured | SOS = Camera error  
- **Red (Error)**: Off = Normal | Solid = System error

### Safe Shutdown Button (GPIO 17)
**Two-stage shutdown process to prevent accidental power-off:**
1. **First Press**: All LEDs blink (10s timeout) - system continues running
2. **Second Press** (within 10s): Stop service → shutdown system (Green LED blinks)
3. **Timeout**: Return to normal operation if no second press

## Storage Structure
```
# Images stored on USB for capacity
/media/usb/bathyimager/
├── images/
│   ├── 20251105/                    # Daily image directories
│   │   ├── IMG_20251105_143021_001.jpg
│   │   └── IMG_20251105_143022_002.jpg
│   └── 20251106/

# Logs stored on SD card for performance (daily directories)
/var/log/bathyimager/
├── 20251121/                        # Daily log directories
│   └── bathyimager.log              # Current day's log file
├── 20251120/
│   └── bathyimager.log
└── 20251119/
    └── bathyimager.log
```

## Common Operations

### Service Management
```bash
sudo systemctl start bathyimager      # Start service
sudo systemctl stop bathyimager       # Stop service
sudo systemctl restart bathyimager    # Restart service
sudo systemctl status bathyimager     # Check status
sudo journalctl -u bathyimager -f     # Monitor logs

# Safe shutdown button service
sudo systemctl status shutdown-button  # Check shutdown button status
sudo journalctl -u shutdown-button -f  # Monitor shutdown button logs
```

### Configuration
```bash
nano config/bathyimager_config.json           # Edit config
python3 tests/troubleshoot.py --config-check  # Validate config
```

### Diagnostics
```bash
python3 tests/troubleshoot.py        # Full diagnostics
python3 tests/troubleshoot.py --quick # Quick health check
```

### Log Transfer (WiFi/SSH)
```bash
# Transfer logs from Pi to local computer via WiFi
# Run from your local computer after SSH setup:

# Transfer today's log file (replace YYYYMMDD with actual date)
scp bathyimager@[PI_IP_ADDRESS]:/var/log/bathyimager/20251121/bathyimager.log ./bathyimager_20251121.log

# Transfer all log files (all daily directories)
scp -r bathyimager@[PI_IP_ADDRESS]:/var/log/bathyimager/ ./bathyimager_logs/

# Transfer specific date's logs
scp -r bathyimager@[PI_IP_ADDRESS]:/var/log/bathyimager/20251121/ ./logs_20251121/

# Compressed transfer for large logs
ssh bathyimager@[PI_IP_ADDRESS] "tar -czf - /var/log/bathyimager/" | tar -xzf - -C ./logs/

# List available log dates first
ssh bathyimager@[PI_IP_ADDRESS] "ls -la /var/log/bathyimager/"
```

## Configuration Examples

### High-Speed Deployment (2+ m/s)
```json
{
  "camera": { "capture_fps": 4.0, "jpeg_quality": 85 },
  "gps": { "require_gps_fix": true, "timeout": 1.0 },
  "timing_precision_mode": true
}
```

### Scientific Survey  
```json
{
  "camera": { "capture_fps": 2.0, "jpeg_quality": 98 },
  "gps": { "require_gps_fix": true },
  "storage": { "cleanup_days": 90 }
}
```

### Development/Testing
```json
{
  "camera": { "capture_fps": 1.0 },
  "gps": { "require_gps_fix": false, "mock_mode": true },
  "logging": { "log_level": "DEBUG" }
}
```

## Documentation

- **[Installation Guide](docs/INSTALL.md)**: Complete setup instructions
- **[GPS HAT Setup](docs/GPS_HAT_SETUP.md)**: GPS HAT installation and configuration
- **[Network Setup](docs/NETWORK_SETUP.md)**: Networking configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Problem resolution guide
- **[Logging System](docs/LOGGING_SYSTEM.md)**: Date-stamped logging details

## Support

### Quick Help
```bash
python3 tests/troubleshoot.py --generate-report
```

### Resources
- **Issues**: [GitHub Issues](https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/issues)
- **Logs**: `/var/log/bathyimager/YYYYMMDD/`

### System Health Check
✅ Service running: `systemctl status bathyimager` shows "active"  
✅ GPS fix: Blue LED solid, images have GPS coordinates  
✅ Images: New files in `/media/usb/bathyimager/images/YYYYMMDD/`  
✅ Performance: `python3 tests/troubleshoot.py --quick` passes

## Disclaimer

This repository is a scientific product and is not official communication of the National Oceanic and Atmospheric Administration, or the United States Department of Commerce. All NOAA GitHub project code is provided on an 'as is' basis and the user assumes responsibility for its use. Any claims against the Department of Commerce or Department of Commerce bureaus stemming from the use of this GitHub project will be governed by all applicable Federal law. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by the Department of Commerce. The Department of Commerce seal and logo, or the seal and logo of a DOC bureau, shall not be used in any manner to imply endorsement of any commercial product or activity by DOC or the United States Government.

## License

Software code created by U.S. Government employees is not subject to copyright in the United States (17 U.S.C. §105). The United States/Department of Commerce reserve all rights to seek and obtain copyright protection in countries other than the United States for Software authored in its entirety by the Department of Commerce. To this end, the Department of Commerce hereby grants to Recipient a royalty-free, nonexclusive license to use, copy, and create derivative works of the Software outside of the United States.
