# BathyCat Test Results Access Guide

This guide explains how to access and analyze test results after running BathyCat camera tests on your Raspberry Pi.

## Test Result Locations

### USB Storage (Preferred)
Test results are automatically saved to USB storage when available:
```
/media/usb-storage/bathycat/test_images/test_session_YYYYMMDD_HHMMSS/
├── test_image_20250807_143022_0001.jpg
├── test_image_20250807_143022_0001.jpg.json
├── test_image_20250807_143023_0002.jpg  
├── test_image_20250807_143023_0002.jpg.json
├── test_summary.json
└── ... (more images and metadata)
```

### Local Storage (Fallback)
If no USB storage is found, results are saved locally:
```
./test_images/test_session_YYYYMMDD_HHMMSS/
├── (same structure as above)
```

## File Types

### 1. Test Images (.jpg)
- **Format**: High-quality JPEG (95% quality)
- **Resolution**: 1920x1080 (Full HD)
- **Naming**: `test_image_YYYYMMDD_HHMMSS_####.jpg`
- **Size**: Typically 800KB - 1.2MB per image

### 2. Image Metadata (.jpg.json)
Each image has a corresponding JSON metadata file:
```json
{
  "filename": "test_image_20250807_143022_0001.jpg",
  "timestamp": "2025-08-07T14:30:22.123456",
  "frame_number": 1,
  "file_size_bytes": 865280,
  "resolution": {
    "width": 1920,
    "height": 1080
  },
  "test_session": "test_session_20250807_143020"
}
```

### 3. Test Summary (test_summary.json)
Complete test session summary:
```json
{
  "test_completed": "2025-08-07T14:30:52.789012",
  "test_duration": 30.02,
  "images_captured": 60,
  "target_fps": 2.0,
  "actual_fps": 2.00,
  "success_rate": 100.0,
  "session_directory": "/media/usb-storage/bathycat/test_images/test_session_20250807_143020",
  "storage_type": "USB"
}
```

## Accessing Results on Raspberry Pi

### 1. Command Line Access

#### List Test Sessions
```bash
# On USB storage
ls -la /media/usb-storage/bathycat/test_images/

# Or local storage
ls -la ./test_images/
```

#### View Latest Test Results
```bash
# Find most recent test session
LATEST=$(ls -t /media/usb-storage/bathycat/test_images/ | head -1)
cd "/media/usb-storage/bathycat/test_images/$LATEST"

# List all files
ls -la

# Count images captured
ls *.jpg | wc -l
```

#### Check Test Summary
```bash
# View test summary
cat test_summary.json | jq '.'

# Or without jq formatting
cat test_summary.json
```

#### Check Individual Image Metadata
```bash
# View metadata for first image
cat test_image_*_0001.jpg.json | jq '.'
```

### 2. File Manager Access
1. Open file manager on Raspberry Pi
2. Navigate to `/media/usb-storage/bathycat/test_images/`
3. Double-click on test session folder
4. View images by double-clicking .jpg files

## Transferring Results Off Pi

### 1. USB Drive Copy
```bash
# Copy specific test session to USB drive
LATEST=$(ls -t /media/usb-storage/bathycat/test_images/ | head -1)
cp -r "/media/usb-storage/bathycat/test_images/$LATEST" /media/usb-backup/

# Or copy all test sessions
cp -r /media/usb-storage/bathycat/test_images/ /media/usb-backup/bathycat_tests/
```

### 2. Network Transfer (SCP)
From another computer on the same network:
```bash
# Copy latest test session
scp -r pi@raspberry-pi-ip:/media/usb-storage/bathycat/test_images/test_session_* ./downloads/

# Copy specific session
scp -r pi@raspberry-pi-ip:/media/usb-storage/bathycat/test_images/test_session_20250807_143020 ./downloads/
```

### 3. Create Archive for Transfer
```bash
# Create compressed archive of test results
cd /media/usb-storage/bathycat/test_images/
tar -czf ~/bathycat_test_results_$(date +%Y%m%d).tar.gz test_session_*

# Copy archive to USB drive
cp ~/bathycat_test_results_*.tar.gz /media/usb-backup/
```

## Result Analysis

### 1. Performance Analysis
```bash
# Check if target FPS was achieved
cat test_summary.json | grep -E "(target_fps|actual_fps|success_rate)"

# Count total images across all sessions
find /media/usb-storage/bathycat/test_images/ -name "*.jpg" | wc -l

# Check average file sizes
find /media/usb-storage/bathycat/test_images/ -name "*.jpg" -exec du -b {} \; | awk '{sum+=$1; n++} END {print "Average image size:", sum/n/1024, "KB"}'
```

### 2. Image Quality Check
```bash
# View image properties
identify test_image_*_0001.jpg

# Check for corrupt images
find . -name "*.jpg" -exec jpeginfo -c {} \; | grep -v OK
```

### 3. Timestamp Analysis
```bash
# Extract all timestamps and check timing consistency
jq -r '.timestamp' *.jpg.json | head -10

# Check frame intervals (requires python)
python3 -c "
import json, glob
from datetime import datetime
files = sorted(glob.glob('*.jpg.json'))
times = []
for f in files:
    with open(f) as fp:
        data = json.load(fp)
        times.append(datetime.fromisoformat(data['timestamp']))
        
for i in range(1, min(10, len(times))):
    interval = (times[i] - times[i-1]).total_seconds()
    print(f'Frame {i}: {interval:.3f}s interval')
"
```

## Storage Management

### 1. Check Storage Usage
```bash
# Check total space used by test results
du -sh /media/usb-storage/bathycat/test_images/

# Check space usage per test session
du -sh /media/usb-storage/bathycat/test_images/test_session_*
```

### 2. Clean Old Test Data
```bash
# Remove test sessions older than 7 days
find /media/usb-storage/bathycat/test_images/ -name "test_session_*" -type d -mtime +7 -exec rm -rf {} \;

# Keep only the 5 most recent test sessions
cd /media/usb-storage/bathycat/test_images/
ls -t test_session_* | tail -n +6 | xargs rm -rf
```

### 3. Archive Old Results
```bash
# Archive sessions older than 30 days
find /media/usb-storage/bathycat/test_images/ -name "test_session_*" -type d -mtime +30 | while read dir; do
    tar -czf "${dir}.tar.gz" "$dir"
    rm -rf "$dir"
done
```

## Troubleshooting Access Issues

### 1. Permission Problems
```bash
# Fix ownership issues
sudo chown -R pi:pi /media/usb-storage/bathycat/

# Fix permissions
sudo chmod -R 755 /media/usb-storage/bathycat/test_images/
```

### 2. USB Storage Not Mounted
```bash
# Check USB devices
lsblk

# Manual mount (replace sda1 with your device)
sudo mkdir -p /media/usb-storage
sudo mount /dev/sda1 /media/usb-storage

# Check mount
df -h /media/usb-storage
```

### 3. Missing Test Results
```bash
# Search for test files in common locations
find /home/pi /media /mnt -name "test_session_*" -type d 2>/dev/null

# Check for local fallback results
find . -name "test_images" -type d
```

## Integration with Main BathyCat System

Test results follow the same directory structure as the main BathyCat system:
- Images are stored with high-quality JPEG compression
- Metadata is saved in JSON format for easy processing
- Session-based organization allows easy data management
- Compatible with main system's data processing scripts

When ready to deploy the full system, test results can be:
- Used to validate camera performance
- Analyzed for optimal FPS settings
- Reviewed to confirm image quality meets requirements
- Referenced for troubleshooting deployment issues
