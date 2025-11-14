# BathyCat Seabed Imager

![BathyCat Seabed Imager](https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/blob/main/docs/BathyCat-Seabed-Imager_Image.png)

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

## Storage Structure
```
/media/usb/bathyimager/
├── images/
│   ├── 20251105/                    # Daily image directories
│   │   ├── IMG_20251105_143021_001.jpg
│   │   └── IMG_20251105_143022_002.jpg
│   └── 20251106/
└── logs/
    ├── 20251105/                    # Daily log directories  
    │   └── bathyimager.log
    └── 20251106/
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

## Configuration Examples

### High-Speed Deployment (2+ m/s)
```json
{
  "camera": { "capture_interval": 0.5, "jpeg_quality": 85 },
  "gps": { "require_gps_fix": true, "timeout": 1.0 },
  "timing_precision_mode": true
}
```

### Scientific Survey  
```json
{
  "camera": { "capture_interval": 2.0, "jpeg_quality": 98 },
  "gps": { "require_gps_fix": true },
  "storage": { "cleanup_days": 90 }
}
```

### Development/Testing
```json
{
  "camera": { "capture_interval": 5.0 },
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
- **Logs**: `/media/usb/bathyimager/logs/YYYYMMDD/`

### System Health Check
✅ Service running: `systemctl status bathyimager` shows "active"  
✅ GPS fix: Blue LED solid, images have GPS coordinates  
✅ Images: New files in `/media/usb/bathyimager/images/YYYYMMDD/`  
✅ Performance: `python3 tests/troubleshoot.py --quick` passes

---

The BathyCat Seabed Imager is a production-ready autonomous imaging system optimized for marine research, seabed mapping, and scientific data collection applications.
