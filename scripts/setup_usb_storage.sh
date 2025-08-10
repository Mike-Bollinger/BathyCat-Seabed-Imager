#!/bin/bash
"""
USB Storage Setup Script for BathyCat
====================================

This script helps set up USB storage for BathyCat image storage.
Run this on your Raspberry Pi to ensure USB storage is properly mounted.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to detect USB storage devices
detect_usb_devices() {
    print_status "Detecting USB storage devices..."
    
    # List all USB storage devices
    USB_DEVICES=$(lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "disk|part" | grep -v "loop\|boot\|root")
    
    if [ -z "$USB_DEVICES" ]; then
        print_error "No USB storage devices found!"
        echo "Please ensure your USB storage device is connected."
        exit 1
    fi
    
    echo "Found storage devices:"
    echo "$USB_DEVICES"
    echo
    
    # Try to identify likely USB devices (not the SD card)
    CANDIDATE_DEVICES=$(lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -n | grep -E "sd[a-z][0-9]" | head -5)
    
    if [ -z "$CANDIDATE_DEVICES" ]; then
        print_warning "No obvious USB devices found. Showing all available devices:"
        lsblk
        echo
        read -p "Enter the device name (e.g., sda1): " USB_DEVICE
    else
        echo "USB device candidates:"
        echo "$CANDIDATE_DEVICES"
        echo
        
        # Auto-select first candidate or let user choose
        FIRST_DEVICE=$(echo "$CANDIDATE_DEVICES" | head -1 | awk '{print $1}')
        read -p "Enter device name (default: $FIRST_DEVICE): " USB_DEVICE
        USB_DEVICE=${USB_DEVICE:-$FIRST_DEVICE}
    fi
    
    echo "Selected device: /dev/$USB_DEVICE"
}

# Function to create mount point and mount device
setup_mount() {
    MOUNT_POINT="/media/usb-storage"
    
    print_status "Setting up mount point: $MOUNT_POINT"
    
    # Create mount point
    sudo mkdir -p "$MOUNT_POINT"
    
    # Check if already mounted
    if mountpoint -q "$MOUNT_POINT"; then
        print_warning "Device already mounted at $MOUNT_POINT"
        ALREADY_MOUNTED=true
    else
        # Mount the device
        print_status "Mounting /dev/$USB_DEVICE to $MOUNT_POINT..."
        sudo mount "/dev/$USB_DEVICE" "$MOUNT_POINT"
        ALREADY_MOUNTED=false
    fi
    
    # Verify mount was successful
    if mountpoint -q "$MOUNT_POINT"; then
        print_success "USB storage mounted successfully"
        
        # Show space information
        df -h "$MOUNT_POINT"
        echo
    else
        print_error "Failed to mount USB storage"
        exit 1
    fi
}

# Function to create BathyCat directory structure
create_directories() {
    print_status "Creating BathyCat directory structure..."
    
    BATHYCAT_DIR="/media/usb-storage/bathycat"
    
    # Create directory structure
    sudo mkdir -p "$BATHYCAT_DIR"/{images,metadata,previews,logs,exports,test_images}
    
    # Set ownership
    if [ -n "$SUDO_USER" ]; then
        USER_NAME="$SUDO_USER"
    else
        USER_NAME=$(whoami)
    fi
    
    print_status "Setting ownership to $USER_NAME..."
    sudo chown -R "$USER_NAME:$USER_NAME" "$BATHYCAT_DIR"
    
    # Set permissions
    sudo chmod -R 755 "$BATHYCAT_DIR"
    
    # Test write permissions
    TEST_FILE="$BATHYCAT_DIR/test_images/.write_test"
    if echo "test" > "$TEST_FILE" 2>/dev/null; then
        rm -f "$TEST_FILE"
        print_success "Write permissions verified"
    else
        print_error "Failed to write to USB storage"
        exit 1
    fi
    
    print_success "BathyCat directories created successfully"
    ls -la "$BATHYCAT_DIR"
}

# Function to add to fstab for automatic mounting
setup_auto_mount() {
    read -p "Do you want to set up automatic mounting on boot? (y/N): " AUTO_MOUNT
    
    if [[ "$AUTO_MOUNT" =~ ^[Yy]$ ]]; then
        print_status "Setting up automatic mounting..."
        
        # Get UUID of the device
        UUID=$(sudo blkid "/dev/$USB_DEVICE" -o value -s UUID)
        
        if [ -n "$UUID" ]; then
            FSTAB_LINE="UUID=$UUID /media/usb-storage ext4 defaults,noatime,nofail 0 2"
            
            # Check if entry already exists
            if ! grep -q "$UUID" /etc/fstab; then
                echo "$FSTAB_LINE" | sudo tee -a /etc/fstab
                print_success "Added to /etc/fstab for automatic mounting"
            else
                print_warning "Entry already exists in /etc/fstab"
            fi
        else
            print_error "Could not determine UUID of device"
        fi
    fi
}

# Function to test the setup
test_setup() {
    print_status "Testing BathyCat storage setup..."
    
    # Test directory creation
    TEST_DIR="/media/usb-storage/bathycat/test_images/setup_test_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$TEST_DIR"
    
    # Test file creation
    TEST_FILE="$TEST_DIR/test_image.txt"
    echo "BathyCat USB Storage Test - $(date)" > "$TEST_FILE"
    
    if [ -f "$TEST_FILE" ]; then
        print_success "Test file created successfully: $TEST_FILE"
        
        # Show storage usage
        echo
        print_status "Storage information:"
        df -h /media/usb-storage
        echo
        
        # Clean up test
        rm -rf "$TEST_DIR"
        print_success "Cleanup completed"
        
    else
        print_error "Failed to create test file"
        exit 1
    fi
}

# Main function
main() {
    echo "BathyCat USB Storage Setup"
    echo "========================="
    echo
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run with sudo"
        echo "Usage: sudo $0"
        exit 1
    fi
    
    # Detect and select USB device
    detect_usb_devices
    
    # Set up mounting
    setup_mount
    
    # Create directories
    create_directories
    
    # Optional auto-mount setup
    setup_auto_mount
    
    # Test the setup
    test_setup
    
    # Final summary
    echo
    echo "========================="
    print_success "USB Storage Setup Complete!"
    echo "========================="
    echo
    echo "Your BathyCat system is now configured to use:"
    echo "📁 Storage Path: /media/usb-storage/bathycat/"
    echo "🖼️  Test Images: /media/usb-storage/bathycat/test_images/"
    echo "🎥 Main Images: /media/usb-storage/bathycat/images/"
    echo
    echo "You can now run camera tests and they will save to USB storage."
    echo "Run: python3 tests/test_camera_capture.py"
    echo
}

# Run main function
main "$@"
