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
    
    # Check GPS
    if [ -e /dev/serial0 ]; then
        print_success "GPS serial port detected"
    else
        print_warning "GPS serial port not found (/dev/serial0)"
        print_warning "GPS functionality may not work"
    fi
    
    # Check camera
    if lsusb | grep -qi camera; then
        print_success "USB camera detected"
    else
        print_warning "No USB camera detected"
        print_warning "Camera functionality may not work"
    fi
    
    # Check storage
    if [ -d "/media/usb-storage" ]; then
        if mountpoint -q /media/usb-storage; then
            STORAGE_FREE=$(df -h /media/usb-storage 2>/dev/null | awk 'NR==2 {print $4}')
            print_success "Storage mounted ($STORAGE_FREE free)"
        else
            print_warning "Storage directory exists but not mounted"
        fi
    else
        print_warning "Storage mount point not found (/media/usb-storage)"
        print_warning "Images will be stored on SD card"
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
    print_status "Testing GPS functionality..."
    
    if command -v gpspipe >/dev/null 2>&1; then
        print_status "Checking for GPS data (10 second timeout)..."
        
        if timeout 10 gpspipe -r -n 5 >/dev/null 2>&1; then
            print_success "GPS data received"
            
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
            print_warning "No GPS data received (antenna or fix issue)"
        fi
    else
        print_warning "GPS tools not installed"
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
    
    # Storage
    if mountpoint -q /media/usb-storage 2>/dev/null; then
        STORAGE_INFO=$(df -h /media/usb-storage | tail -1)
        echo "Storage: $STORAGE_INFO"
    else
        ROOT_INFO=$(df -h / | tail -1)
        echo "Root FS: $ROOT_INFO"
    fi
    
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
    sudo chown pi:pi "$LOG_DIR"
    
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
