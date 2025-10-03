# BathyCat Fresh Install Guide - H264 Camera Edition

## 🚀 Quick Setup After Fresh Pi Flash

### 1. Initial SSH Setup
After flashing and first boot:
```bash
# SSH into the fresh Pi (use the IP from your router or pi finder)
ssh pi@192.168.50.xxx

# Update the default password immediately
passwd

# Create bathyimager user for consistency
sudo useradd -m -s /bin/bash bathyimager
sudo passwd bathyimager
sudo usermod -aG sudo,video,dialout bathyimager

# Switch to bathyimager user
sudo su - bathyimager
```

### 2. Install BathyCat
```bash
# First install git (not included by default)
sudo apt update
sudo apt install -y git

# Clone the repository
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

# Run the safe install script
sudo ./scripts/safe_install.sh
```

**Alternative if git fails:**
```bash
# Download as ZIP instead
wget https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/archive/refs/heads/main.zip
sudo apt install -y unzip
unzip main.zip
cd BathyCat-Seabed-Imager-main
sudo ./scripts/safe_install.sh
```

### 3. Camera Fix Application
The safe install automatically applies our H264 camera fixes:
- Adds user to video group
- Sets camera permissions
- Creates boot-time permission fix service
- Copies all diagnostic tools

### 4. USB Storage Setup
```bash
# Format USB drive as exFAT with label BATHYCAT-DATA on Windows before connecting
# Or format on Pi:
sudo mkfs.exfat -n BATHYCAT-DATA /dev/sda1

# Mount and test
sudo mount /dev/sda1 /media/usb-storage
ls -la /media/usb-storage/
```

### 5. Test Camera Before Starting Service
```bash
# Test fswebcam (should work)
fswebcam -d /dev/video0 --no-banner -r 1920x1080 test.jpg

# Run our diagnostic
python3 /opt/bathycat/camera_diagnostics.py

# Apply any additional fixes if needed
/opt/bathycat/fix_camera_permissions.sh
```

### 6. Start BathyCat Service
```bash
# Start the service
sudo systemctl start bathycat-imager

# Check status
sudo systemctl status bathycat-imager

# Follow logs
journalctl -u bathycat-imager -f
```

### 7. If Camera Still Fails
We have the fswebcam integration ready to deploy:
```bash
# The safe install includes all our camera fix scripts
# If OpenCV still fails, we can switch to fswebcam integration
python3 /opt/bathycat/fswebcam_integration.py
```

## 🔧 Key Improvements in Safe Install

1. **No Boot Partition Changes** - Avoids bricking
2. **Virtual Environment** - Isolated Python packages  
3. **H264 Camera Fixes** - Pre-applied camera solutions
4. **Proper Permissions** - All files owned by bathyimager user
5. **USB GPS Support** - Works with your USB GPS setup
6. **Diagnostic Tools** - All our debugging scripts included

## 📋 What's Different from Original Install

- **Safer**: No risky boot configuration changes
- **Camera-Ready**: H264 USB camera fixes pre-applied
- **USB-First**: Designed for your USB GPS + USB camera setup
- **Diagnostic-Enabled**: All troubleshooting tools included
- **Recovery-Ready**: fswebcam integration available

## 🆘 If Something Goes Wrong

The diagnostic tools are installed at `/opt/bathycat/`:
- `camera_diagnostics.py` - Full camera analysis
- `fix_camera_permissions.sh` - Camera permission fixes  
- `fswebcam_integration.py` - OpenCV bypass solution

This should get you back up and running quickly with all our camera fixes applied!