#!/bin/bash
"""
Start Capture Script for BathyCat Seabed Imager
==============================================

Manual startup script for testing and deployment.

Author: BathyCat Systems
Date: August 2025
"""

# Configuration
INSTALL_DIR="/opt/bathycat"
CONFIG_DIR="/etc/bathycat"
LOG_DIR="/var/log/bathycat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking system prerequisites..."
    
    # Check if installation exists
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Installation directory not found: $INSTALL_DIR"
        print_error "Please run the installation script first"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -f "$INSTALL_DIR/venv/bin/python3" ]; then
        print_error "Python virtual environment not found"
        print_error "Please run the installation script first"
        exit 1
    fi
    
    # Check if configuration exists
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        print_error "Configuration file not found: $CONFIG_DIR/config.json"
        print_error "Creating default configuration..."
        
        sudo mkdir -p "$CONFIG_DIR"
        sudo cp "$INSTALL_DIR/config/bathycat_config.json" "$CONFIG_DIR/config.json"
        
        if [ $? -eq 0 ]; then
            print_success "Default configuration created"
        else
            print_error "Failed to create configuration"
            exit 1
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to check hardware
check_hardware() {
    print_status "Checking hardware components..."
    
    # Check USB GPS using updated detection
    print_status "Checking for USB GPS module..."
    GPS_FOUND=false
    
    # Check for USB GPS devices
    if lsusb | grep -i "GlobalSat\|u-blox\|GPS\|PA1010D" >/dev/null 2>&1; then
        print_success "USB GPS module detected via lsusb"
        GPS_FOUND=true
    fi
    
    # Check for serial ports that might be GPS
    if ls /dev/ttyACM* /dev/ttyUSB* >/dev/null 2>&1; then
        print_success "USB serial ports detected for GPS"
        ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | while read device; do
            echo "  Found: $device"
        done
        GPS_FOUND=true
    fi
    
    if [ "$GPS_FOUND" = false ]; then
        # Fallback: check legacy serial port
        if [ -e /dev/serial0 ]; then
            print_warning "Using legacy GPIO serial port (/dev/serial0)"
            GPS_FOUND=true
        else
            print_warning "No GPS device detected"
            print_warning "GPS functionality may not work"
        fi
    fi
    
    # Check camera
    if lsusb | grep -qi camera; then
        print_success "USB camera detected via lsusb"
    elif ls /dev/video* >/dev/null 2>&1; then
        CAMERA_DEV=$(ls /dev/video* | head -1)
        print_success "Camera device found: $CAMERA_DEV"
    else
        print_warning "No camera devices detected"
        print_warning "Camera functionality may not work"
    fi
    
    # Enhanced USB storage detection
    print_status "Checking for USB storage..."
    STORAGE_FOUND=false
    
    # Check common mount points
    USB_MOUNTS=(
        "/media/usb-storage"
        "/media/bathycat"
        "/media/bathyimager"
        "/mnt/usb"
    )
    
    for mount_point in "${USB_MOUNTS[@]}"; do
        if [ -d "$mount_point" ] && mountpoint -q "$mount_point" 2>/dev/null; then
            STORAGE_FREE=$(df -h "$mount_point" 2>/dev/null | awk 'NR==2 {print $4}')
            FILESYSTEM=$(df -T "$mount_point" 2>/dev/null | awk 'NR==2 {print $2}')
            print_success "USB storage mounted at $mount_point ($STORAGE_FREE free, $FILESYSTEM)"
            STORAGE_FOUND=true
            
            # Check BathyCat directory structure
            BATHYCAT_DIR="$mount_point/bathycat"
            if [ -d "$BATHYCAT_DIR" ]; then
                print_success "BathyCat directory structure exists"
            else
                print_warning "BathyCat directory structure missing"
                print_status "Creating directory structure..."
                mkdir -p "$BATHYCAT_DIR"/{images,metadata,previews,logs,exports}
                print_success "Directory structure created"
            fi
            break
        fi
    done
    
    if [ "$STORAGE_FOUND" = false ]; then
        # Check for any USB devices
        if lsblk | grep -E "sd[a-z]" | grep -v "disk" >/dev/null 2>&1; then
            print_warning "USB storage detected but not mounted"
            echo "Available USB devices:"
            lsblk | grep -E "sd[a-z]" | head -5
            print_warning "Run setup_usb_storage.sh to configure USB storage"
        else
            print_warning "No USB storage detected"
            print_warning "Images will be stored on SD card"
        fi
    fi
    
    print_success "Hardware check completed"
}

# Function to check services
check_services() {
    print_status "Checking system services..."
    
    # Check if main service is running
    if systemctl is-active --quiet bathycat-imager; then
        print_warning "BathyCat service is already running"
        echo "Options:"
        echo "  1. Stop service and run manually"
        echo "  2. View service status"
        echo "  3. Exit"
        read -p "Choose option (1-3): " choice
        
        case $choice in
            1)
                print_status "Stopping service..."
                sudo systemctl stop bathycat-imager
                print_success "Service stopped"
                ;;
            2)
                systemctl status bathycat-imager --no-pager
                exit 0
                ;;
            3)
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
    fi
    
    # Check GPS service
    if systemctl is-active --quiet gpsd; then
        print_success "GPS service is running"
    else
        print_warning "GPS service is not running"
        print_status "Starting GPS service..."
        sudo systemctl start gpsd
        sleep 2
        if systemctl is-active --quiet gpsd; then
            print_success "GPS service started"
        else
            print_warning "Failed to start GPS service"
        fi
    fi
}

# Function to test GPS
test_gps() {
    print_status "Testing USB GPS functionality..."
    
    # First check for USB GPS devices
    GPS_DEVICE=""
    
    # Try to detect USB GPS device
    if ls /dev/ttyACM* >/dev/null 2>&1; then
        for device in /dev/ttyACM*; do
            print_status "Testing GPS device: $device"
            # Try to read NMEA data directly
            if timeout 5 cat "$device" 2>/dev/null | grep -q "^\$G"; then
                GPS_DEVICE="$device"
                print_success "USB GPS responding on $device"
                break
            fi
        done
    fi
    
    # Try ttyUSB devices if ACM didn't work
    if [ -z "$GPS_DEVICE" ] && ls /dev/ttyUSB* >/dev/null 2>&1; then
        for device in /dev/ttyUSB*; do
            print_status "Testing GPS device: $device"
            if timeout 5 cat "$device" 2>/dev/null | grep -q "^\$G"; then
                GPS_DEVICE="$device"
                print_success "USB GPS responding on $device"
                break
            fi
        done
    fi
    
    if [ -n "$GPS_DEVICE" ]; then
        print_status "Reading GPS data from $GPS_DEVICE..."
        
        # Read a few NMEA sentences
        GPS_DATA=$(timeout 10 cat "$GPS_DEVICE" 2>/dev/null | head -5)
        if [ -n "$GPS_DATA" ]; then
            print_success "GPS NMEA data received:"
            echo "$GPS_DATA" | while IFS= read -r line; do
                if [[ "$line" =~ ^\$G ]]; then
                    echo "  $line"
                fi
            done
            
            # Check for fix status in GGA sentences
            if echo "$GPS_DATA" | grep -q "\$G.GGA.*,[0-9]\+\.[0-9]\+,[NS],[0-9]\+\.[0-9]\+,[EW]"; then
                print_success "GPS appears to have position fix"
            else
                print_warning "GPS receiving data but no position fix yet"
                print_status "This is normal - GPS needs clear sky view and time to acquire satellites"
            fi
        else
            print_warning "GPS device found but no NMEA data received"
        fi
    else
        # Fallback to gpspipe if available
        if command -v gpspipe >/dev/null 2>&1; then
            print_status "Testing GPS with gpspipe (10 second timeout)..."
            
            if timeout 10 gpspipe -r -n 5 >/dev/null 2>&1; then
                print_success "GPS data received via gpsd"
                
                # Try to get a position
                print_status "Checking GPS fix status..."
                GPS_FIX=$(timeout 10 gpspipe -w -n 1 2>/dev/null | grep -o '"mode":[0-9]' | cut -d: -f2)
                
                case "$GPS_FIX" in
                    "3")
                        print_success "GPS has 3D fix"
                        ;;
                    "2")
                        print_success "GPS has 2D fix"
                        ;;
                    "1")
                        print_warning "GPS sees satellites but no fix yet"
                        ;;
                    *)
                        print_warning "GPS fix status unknown"
                        ;;
                esac
            else
                print_warning "No GPS data received via gpsd"
            fi
        else
            print_warning "No GPS device responding and gpspipe not available"
            print_status "GPS troubleshooting tips:"
            echo "  1. Ensure USB GPS module is connected"
            echo "  2. Check USB connection: lsusb | grep -i gps"
            echo "  3. Test devices manually: ls /dev/ttyACM* /dev/ttyUSB*"
            echo "  4. For GPS fix: ensure clear view of sky"
            echo "  5. Run: python3 tests/test_gps_debug.py"
        fi
    fi
}

# Function to test camera
test_camera() {
    print_status "Testing camera functionality..."
    
    # Check if camera device exists
    if ls /dev/video* >/dev/null 2>&1; then
        CAMERA_DEV=$(ls /dev/video* | head -1)
        print_success "Camera device found: $CAMERA_DEV"
        
        # Test capture with fswebcam if available
        if command -v fswebcam >/dev/null 2>&1; then
            print_status "Testing camera capture..."
            if fswebcam -d "$CAMERA_DEV" --no-banner -q /tmp/camera_test.jpg 2>/dev/null; then
                print_success "Camera capture test successful"
                rm -f /tmp/camera_test.jpg
            else
                print_warning "Camera capture test failed"
            fi
        else
            print_warning "fswebcam not available for camera testing"
        fi
    else
        print_warning "No camera devices found"
    fi
}

# Function to show system status
show_status() {
    echo
    print_status "System Status Summary:"
    echo "----------------------------------------"
    
    # System info
    echo "System: $(uname -n) ($(uname -m))"
    echo "Uptime: $(uptime -p)"
    echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Temperature
    if command -v vcgencmd >/dev/null 2>&1; then
        TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2)
        echo "CPU Temperature: $TEMP"
    fi
    
    # Memory
    MEM_INFO=$(free -h | grep '^Mem:')
    echo "Memory: $MEM_INFO"
    
    # Storage - check multiple possible mount points
    STORAGE_STATUS="Not found"
    for mount_point in "/media/usb-storage" "/media/bathycat" "/media/bathyimager" "/mnt/usb"; do
        if mountpoint -q "$mount_point" 2>/dev/null; then
            STORAGE_INFO=$(df -h "$mount_point" | tail -1)
            FILESYSTEM=$(df -T "$mount_point" | tail -1 | awk '{print $2}')
            STORAGE_STATUS="$mount_point ($FILESYSTEM): $STORAGE_INFO"
            break
        fi
    done
    
    if [ "$STORAGE_STATUS" = "Not found" ]; then
        ROOT_INFO=$(df -h / | tail -1)
        STORAGE_STATUS="Root FS: $ROOT_INFO"
    fi
    
    echo "Storage: $STORAGE_STATUS"
    
    echo "----------------------------------------"
}

# Function to start the application
start_application() {
    print_status "Starting BathyCat Seabed Imager..."
    
    # Change to application directory
    cd "$INSTALL_DIR" || exit 1
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Add src to Python path
    export PYTHONPATH="$INSTALL_DIR/src:$PYTHONPATH"
    
    # Create log directory if it doesn't exist
    sudo mkdir -p "$LOG_DIR"
    
    # Set ownership based on current user or bathyimager
    if id "bathyimager" >/dev/null 2>&1; then
        sudo chown bathyimager:bathyimager "$LOG_DIR"
    else
        # Fallback to pi user if bathyimager doesn't exist
        sudo chown pi:pi "$LOG_DIR"
    fi
    
    print_success "Environment activated"
    print_status "Configuration: $CONFIG_DIR/config.json"
    print_status "Logs will be written to: $LOG_DIR/"
    print_status "Press Ctrl+C to stop"
    echo
    
    # Start the application with verbose output
    python3 src/bathycat_imager.py \
        --config "$CONFIG_DIR/config.json" \
        --verbose
}

# Function to show usage
show_usage() {
    echo "BathyCat Seabed Imager - Manual Start Script"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --no-checks    Skip hardware and service checks"
    echo "  --test-only    Run tests only, don't start application"
    echo "  --status-only  Show system status only"
    echo "  --help         Show this help message"
    echo
    echo "This script will:"
    echo "  1. Check system prerequisites"
    echo "  2. Verify hardware components"
    echo "  3. Test GPS and camera functionality"
    echo "  4. Start the BathyCat imaging application"
    echo
}

# Main script
main() {
    echo "========================================"
    echo "BathyCat Seabed Imager"
    echo "Manual Start Script"
    echo "========================================"
    
    # Parse command line arguments
    SKIP_CHECKS=false
    TEST_ONLY=false
    STATUS_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-checks)
                SKIP_CHECKS=true
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --status-only)
                STATUS_ONLY=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Always check prerequisites
    check_prerequisites
    
    # Show system status if requested
    if [ "$STATUS_ONLY" = true ]; then
        show_status
        exit 0
    fi
    
    # Run checks unless skipped
    if [ "$SKIP_CHECKS" = false ]; then
        check_hardware
        check_services
        test_gps
        test_camera
        show_status
    fi
    
    # Exit if test-only mode
    if [ "$TEST_ONLY" = true ]; then
        print_success "All tests completed"
        exit 0
    fi
    
    # Start the application
    echo
    print_status "All checks completed"
    read -p "Press Enter to start BathyCat Imager (or Ctrl+C to cancel)..."
    
    start_application
}

# Handle Ctrl+C gracefully
trap 'echo; print_status "Shutting down..."; exit 0' INT

# Run main function
main "$@"
