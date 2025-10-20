#!/bin/bash
#
# BathyImager Hardware Diagnostic Suite
# ====================================
#
# Individual hardware tests for troubleshooting
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root - some tests may behave differently"
fi

print_header "BathyImager Hardware Diagnostic Suite"
echo "System: $(uname -a)"
echo "Date: $(date)"
echo "User: $(whoami)"
echo

# Function to run camera diagnostics
test_camera() {
    print_header "🎥 CAMERA DIAGNOSTICS"
    
    print_status "Checking for video devices..."
    if ls /dev/video* >/dev/null 2>&1; then
        for device in /dev/video*; do
            print_success "Found: $device"
            
            # Check device permissions
            if [ -r "$device" ] && [ -w "$device" ]; then
                print_success "  ✓ Device readable and writable"
            else
                print_error "  ✗ No read/write access to $device"
                print_status "  Try: sudo usermod -a -G video $USER"
            fi
            
            # Get device info if v4l2-ctl is available
            if command -v v4l2-ctl >/dev/null 2>&1; then
                print_status "  Device info:"
                v4l2-ctl --device="$device" --info 2>/dev/null | head -5 | sed 's/^/    /'
                
                print_status "  Supported formats:"
                v4l2-ctl --device="$device" --list-formats-ext 2>/dev/null | head -10 | sed 's/^/    /'
            else
                print_warning "  v4l2-ctl not available for detailed device info"
                print_status "  Install with: sudo apt install v4l-utils"
            fi
        done
    else
        print_error "No video devices found (/dev/video*)"
        print_status "Check USB camera connection"
    fi
    
    print_status "Testing OpenCV camera access..."
    python3 << 'EOF'
import sys
try:
    import cv2
    print(f"  ✓ OpenCV version: {cv2.__version__}")
    
    # Try to open camera
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            height, width = frame.shape[:2]
            print(f"  ✓ Camera capture successful: {width}x{height}")
        else:
            print("  ✗ Could not read frame from camera")
        cap.release()
    else:
        print("  ✗ Could not open camera with OpenCV")
except ImportError:
    print("  ✗ OpenCV not installed")
    print("  Install with: pip install opencv-python")
except Exception as e:
    print(f"  ✗ Camera test failed: {e}")
EOF
}

# Function to run GPS diagnostics
test_gps() {
    print_header "🛰️  GPS DIAGNOSTICS"
    
    print_status "Checking for serial/GPS devices..."
    for pattern in "/dev/ttyUSB*" "/dev/ttyACM*" "/dev/serial/by-id/usb-*GPS*"; do
        if ls $pattern >/dev/null 2>&1; then
            for device in $pattern; do
                print_success "Found: $device"
                
                # Check permissions
                if [ -r "$device" ] && [ -w "$device" ]; then
                    print_success "  ✓ Device readable and writable"
                else
                    print_error "  ✗ No read/write access to $device"
                    print_status "  Try: sudo usermod -a -G dialout $USER"
                fi
                
                # Check if it looks like GPS
                if [[ "$device" == *"GPS"* ]] || [[ "$device" == "/dev/ttyUSB"* ]]; then
                    print_status "  Testing GPS data stream (5 seconds)..."
                    timeout 5s cat "$device" 2>/dev/null | head -5 | while read line; do
                        if [[ "$line" == \$GP* ]] || [[ "$line" == \$GN* ]]; then
                            echo "    📡 $line"
                        fi
                    done || print_warning "  No GPS data received (normal if no fix)"
                fi
            done
        fi
    done
    
    if ! ls /dev/ttyUSB* /dev/ttyACM* >/dev/null 2>&1; then
        print_error "No serial devices found"
        print_status "Check USB GPS connection"
    fi
    
    print_status "Testing GPS libraries..."
    python3 << 'EOF'
try:
    import serial
    print("  ✓ PySerial available")
except ImportError:
    print("  ✗ PySerial not installed")
    print("  Install with: pip install pyserial")

try:
    import pynmea2
    print("  ✓ PyNMEA2 available")
except ImportError:
    print("  ✗ PyNMEA2 not installed")
    print("  Install with: pip install pynmea2")
EOF
}

# Function to run storage diagnostics
test_storage() {
    print_header "💾 USB STORAGE DIAGNOSTICS"
    
    print_status "Checking mounted filesystems..."
    df -h | grep -E "(Filesystem|/dev/sd|/dev/mmcblk|/media|/mnt)" | while read line; do
        echo "  $line"
    done
    
    print_status "Checking for USB storage devices..."
    lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT | grep -E "(NAME|sd|mmcblk)" | while read line; do
        echo "  $line"
    done
    
    print_status "Checking USB device connections..."
    lsusb | grep -i "mass storage\|disk\|flash\|usb" | while read line; do
        print_success "  USB: $line"
    done
    
    # Check common mount points
    for mount_point in "/media/usb" "/mnt/usb" "/media/$USER" "/mnt"; do
        if mountpoint -q "$mount_point" 2>/dev/null; then
            print_success "Storage mounted at: $mount_point"
            df -h "$mount_point" | tail -1 | while read fs size used avail percent mount; do
                echo "    Size: $size, Used: $used, Available: $avail ($percent full)"
            done
            
            # Test write permissions
            if touch "$mount_point/bathyimager_test" 2>/dev/null; then
                print_success "  ✓ Write permission OK"
                rm "$mount_point/bathyimager_test"
            else
                print_error "  ✗ No write permission"
                ls -la "$mount_point" | head -2
            fi
        fi
    done
    
    # Check for unmounted USB devices
    print_status "Checking for unmounted USB storage..."
    for device in /dev/sd[a-z][0-9]*; do
        if [ -b "$device" ]; then
            if ! mountpoint -q "$(lsblk -no MOUNTPOINT "$device" 2>/dev/null)"; then
                print_warning "Unmounted storage device: $device"
                lsblk -o NAME,SIZE,FSTYPE,LABEL "$device" 2>/dev/null | tail -1 | while read name size fstype label; do
                    echo "    Size: $size, Type: $fstype, Label: $label"
                    if [ -n "$fstype" ]; then
                        print_status "    Manual mount: sudo mkdir -p /media/usb && sudo mount $device /media/usb"
                    fi
                done
            fi
        fi
    done 2>/dev/null
}

# Function to test system dependencies
test_dependencies() {
    print_header "📦 SYSTEM DEPENDENCIES"
    
    print_status "Checking Python environment..."
    python3 --version | sed 's/^/  /'
    
    print_status "Checking required Python packages..."
    python3 << 'EOF'
required_packages = [
    ('cv2', 'opencv-python'),
    ('serial', 'pyserial'), 
    ('pynmea2', 'pynmea2'),
    ('PIL', 'Pillow'),
    ('piexif', 'piexif')
]

optional_packages = [
    ('RPi.GPIO', 'RPi.GPIO'),
    ('gpiozero', 'gpiozero')
]

print("Required packages:")
for module, package in required_packages:
    try:
        __import__(module)
        print(f"  ✓ {package}")
    except ImportError:
        print(f"  ✗ {package} - pip install {package}")

print("\nOptional packages:")
for module, package in optional_packages:
    try:
        __import__(module)
        print(f"  ✓ {package}")
    except ImportError:
        print(f"  ✗ {package} - pip install {package}")
EOF
    
    print_status "Checking system packages..."
    for pkg in "v4l-utils" "gpsd" "gpsd-clients"; do
        if dpkg -l | grep -q "^ii  $pkg "; then
            print_success "  ✓ $pkg installed"
        else
            print_warning "  ✗ $pkg not installed - sudo apt install $pkg"
        fi
    done
}

# Main execution
case "${1:-all}" in
    "camera"|"cam")
        test_camera
        ;;
    "gps")
        test_gps
        ;;
    "storage"|"usb")
        test_storage
        ;;
    "deps"|"dependencies")
        test_dependencies
        ;;
    "all"|"")
        test_dependencies
        echo
        test_camera
        echo
        test_gps  
        echo
        test_storage
        ;;
    *)
        echo "Usage: $0 [camera|gps|storage|dependencies|all]"
        echo "  camera      - Test camera hardware and OpenCV"
        echo "  gps         - Test GPS device and serial communication" 
        echo "  storage     - Test USB storage mounting and permissions"
        echo "  dependencies- Check required Python packages"
        echo "  all         - Run all tests (default)"
        exit 1
        ;;
esac

print_header "🏁 DIAGNOSTIC COMPLETE"
echo "If issues found, check the specific test output above."
echo "For service issues, also check: sudo journalctl -u bathyimager -f"
echo