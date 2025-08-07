# BathyCat Testing on Raspberry Pi

This guide helps you test the BathyCat camera system on your Raspberry Pi.

## Quick Test Steps

### 1. Copy files to your Raspberry Pi

```bash
# Option A: Git clone (if Pi has internet)
git clone https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git
cd BathyCat-Seabed-Imager

# Option B: Copy via USB/SCP if already downloaded
# Copy the entire project folder to your Pi
```

### 2. Run System Check

First, check if your system is ready:

```bash
cd BathyCat-Seabed-Imager
python3 tests/system_check.py
```

This will:
- ✅ Check if required Python packages are installed
- ✅ Look for connected cameras
- ✅ Verify USB storage and space availability
- ✅ Check file permissions
- ✅ Create a test configuration file

### 3. Install Missing Dependencies (if needed)

If the system check shows missing packages:

```bash
# Install OpenCV and other dependencies
pip3 install opencv-python numpy pillow

# OR using apt (alternative method)
sudo apt update
sudo apt install python3-opencv python3-numpy python3-pil
```

### 4. Connect Your Camera and USB Storage

- Plug your USB camera into any USB port
- Connect your USB storage device (flash drive, SSD, etc.)
- Run system check again to verify detection:
  ```bash
  python3 tests/system_check.py
  ```

### 5. Run Camera Capture Test

Now test actual image capture:

```bash
# Basic test (30 seconds, 2 FPS) - saves to USB storage automatically
python3 tests/test_camera_capture.py

# Custom test (60 seconds, 4 FPS)
python3 tests/test_camera_capture.py --duration 60 --fps 4

# Quick test (10 seconds, 1 FPS)
python3 tests/test_camera_capture.py --duration 10 --fps 1
```

### 6. Check Results

The test will:
- 📸 Capture images at the specified rate
- 💾 Save them to USB storage: `/media/usb-storage/bathycat/test_images/test_session_YYYYMMDD_HHMMSS/`
- 📊 Show real-time capture statistics
- ✅ Report success/failure and actual FPS achieved
- 📄 Create metadata files for each image
- 📋 Generate a test summary report

Check your captured images:
```bash
# Find latest test session
LATEST=$(ls -t /media/usb-storage/bathycat/test_images/ | head -1)
ls -la "/media/usb-storage/bathycat/test_images/$LATEST"

# Or check local fallback if no USB storage
ls -la test_images/test_session_*/
```

📖 **For detailed information on accessing and managing test results, see: [RESULTS_ACCESS_GUIDE.md](RESULTS_ACCESS_GUIDE.md)**

## Expected Results

### Successful Test Output
```
BathyCat Camera Test
==================
Using USB storage: /media/usb-storage/bathycat/test_images
Session directory: /media/usb-storage/bathycat/test_images/test_session_20250807_143020
Target FPS: 2
Test duration: 30 seconds

Searching for cameras...
Found camera 0: 1920x1080 @ 30fps
Setting up camera 0...
Camera configured: 1920x1080 @ 30fps
Warming up camera...
Camera ready!

Starting capture test...
Will capture for 30 seconds at 2 FPS

Captured: test_image_20250807_143022_0001.jpg (845.2KB)
Captured: test_image_20250807_143023_0002.jpg (832.1KB)
...
Progress: 10.0s, 20 images, 2.00 fps actual
...

==================================================
TEST RESULTS
==================================================
Duration: 30.02 seconds
Images captured: 60
Target FPS: 2
Actual FPS: 2.00
Success rate: 100.0%
Session directory: /media/usb-storage/bathycat/test_images/test_session_20250807_143020

✅ SUCCESS: Camera is working!
Check the images in: /media/usb-storage/bathycat/test_images/test_session_20250807_143020
Test summary saved: /media/usb-storage/bathycat/test_images/test_session_20250807_143020/test_summary.json
```

## Troubleshooting

### No USB Storage Found
```bash
# Check mounted storage devices
lsblk
df -h

# Check for automount locations
ls -la /media/
ls -la /mnt/

# Manual mount USB storage (replace sda1 with your device)
sudo mkdir -p /media/usb-storage
sudo mount /dev/sda1 /media/usb-storage

# Create BathyCat directory structure
sudo mkdir -p /media/usb-storage/bathycat/test_images
sudo chown -R pi:pi /media/usb-storage/bathycat/
```

### No Cameras Found
```bash
# Check USB devices
lsusb | grep -i camera

# Check video devices
ls -l /dev/video*

# Check permissions
groups $USER
# Should include 'video' group

# Add to video group if missing
sudo usermod -a -G video $USER
# Then logout and login again
```

### Permission Denied
```bash
# Add user to video group
sudo usermod -a -G video $USER
newgrp video

# Check device permissions
ls -l /dev/video0
```

### Low FPS Performance
```bash
# Check CPU usage during test
htop

# Check USB version (should be USB 3.0 for best performance)
lsusb -t

# Try lower resolution in test
# Edit scripts/test_camera_capture.py line 69-70:
# self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
# self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
```

### Missing OpenCV
```bash
# Method 1: pip install
pip3 install opencv-python

# Method 2: apt install (Raspberry Pi OS)
sudo apt update
sudo apt install python3-opencv

# Method 3: Build from source (if needed)
# See: https://docs.opencv.org/4.x/d7/d9f/tutorial_linux_install.html
```

## What This Tests

✅ **Camera Detection**: Finds your USB camera  
✅ **Image Capture**: Takes photos at specified intervals  
✅ **USB Storage**: Automatically uses USB storage when available
✅ **File Writing**: Saves images and metadata to disk
✅ **Performance**: Measures actual vs target FPS
✅ **Quality**: Uses high JPEG quality settings (95%)
✅ **Timing**: Precise frame timing control
✅ **Session Management**: Organizes results by test session
✅ **Metadata Generation**: Creates JSON metadata for each image

## Next Steps

If the test succeeds:
1. 🎉 Your camera system is working!
2. Review results using the [Results Access Guide](RESULTS_ACCESS_GUIDE.md)
3. Install the full BathyCat system: `sudo scripts/install.sh`
4. Configure for your specific hardware
5. Test with GPS when outdoors

If the test fails:
1. Check the troubleshooting section above
2. Verify hardware connections
3. Check system logs: `dmesg | grep -i usb`
4. Try a different USB port or camera

## Test File Locations

All test files are in the `tests/` directory:

- **tests/system_check.py** - System diagnostic script
- **tests/test_camera_capture.py** - Camera capture test
- **tests/TESTING_GUIDE.md** - This guide
- **tests/RESULTS_ACCESS_GUIDE.md** - Detailed results access instructions
- **tests/test_components.py** - Component integration tests

## Test Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--duration` | 30 | Test duration in seconds |
| `--fps` | 2.0 | Target frames per second |
| `--output` | Auto-detect USB | Output directory for images |

Example:
```bash
python3 tests/test_camera_capture.py --duration 120 --fps 4 --output /media/custom-storage/test
```

This creates a comprehensive test that doesn't require GPS and verifies your camera system is working properly with USB storage management!
