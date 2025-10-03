#!/bin/bash
#
# BathyCat USB Storage Setup Script
# =================================
# 
# Robust USB storage detection and mounting for BathyCat

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Constants
MOUNT_POINT="/media/usb-storage" 
BATHYCAT_DIR="$MOUNT_POINT/bathycat"

# Check if running as root for mount operations
check_permissions() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script requires sudo privileges for mounting"
        print_status "Please run: sudo $0"
        exit 1
    fi
}

# Detect USB storage devices
detect_usb_storage() {
    print_status "Detecting USB storage devices..."
    
    # Look for USB storage devices
    USB_DEVICES=($(lsblk -no NAME,TRAN | grep usb | awk '{print $1}' | grep -E '^sd[a-z]$'))
    
    if [ ${#USB_DEVICES[@]} -eq 0 ]; then
        print_error "No USB storage devices found"
        print_status "Please connect a USB flash drive and try again"
        exit 1
    fi
    
    print_success "Found ${#USB_DEVICES[@]} USB storage device(s):"
    for device in "${USB_DEVICES[@]}"; do
        size=$(lsblk -no SIZE "/dev/$device" | head -1)
        print_status "  /dev/$device ($size)"
    done
    
    # Use the first USB device
    USB_DEVICE="${USB_DEVICES[0]}"
    
    # Look for the first partition
    PARTITION=$(lsblk -no NAME "/dev/$USB_DEVICE" | grep -E "${USB_DEVICE}[0-9]+" | head -1)
    
    if [ -z "$PARTITION" ]; then
        print_error "No partitions found on /dev/$USB_DEVICE"
        print_status "The USB drive may need to be formatted"
        exit 1
    fi
    
    USB_PARTITION="/dev/$PARTITION"
    print_success "Using partition: $USB_PARTITION"
}

# Create mount point and mount USB storage
mount_usb_storage() {
    print_status "Setting up USB storage mount..."
    
    # Create mount point
    mkdir -p "$MOUNT_POINT"
    
    # Check if already mounted
    if mountpoint -q "$MOUNT_POINT"; then
        print_warning "USB storage already mounted at $MOUNT_POINT"
        return 0
    fi
    
    # Attempt to mount
    print_status "Mounting $USB_PARTITION to $MOUNT_POINT..."
    
    # Try multiple filesystem types
    for fs_type in exfat vfat ext4 ntfs; do
        if mount -t "$fs_type" "$USB_PARTITION" "$MOUNT_POINT" 2>/dev/null; then
            print_success "Mounted as $fs_type filesystem"
            return 0
        fi
    done
    
    # Try without specifying filesystem type
    if mount "$USB_PARTITION" "$MOUNT_POINT" 2>/dev/null; then
        print_success "Mounted with auto-detected filesystem"
        return 0
    fi
    
    print_error "Failed to mount USB storage"
    print_status "The drive may need formatting or repair"
    exit 1
}

# Create BathyCat directory structure
create_bathycat_directories() {
    print_status "Creating BathyCat directory structure..."
    
    # Create directories
    directories=(
        "$BATHYCAT_DIR"
        "$BATHYCAT_DIR/images"
        "$BATHYCAT_DIR/metadata"
        "$BATHYCAT_DIR/previews"
        "$BATHYCAT_DIR/logs"
        "$BATHYCAT_DIR/exports"
        "$BATHYCAT_DIR/test_images"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created: $dir"
    done
    
    # Set ownership to the user who ran sudo
    if [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" "$BATHYCAT_DIR"
        print_success "Set ownership to $SUDO_USER"
    else
        # Fallback to pi user
        chown -R pi:pi "$BATHYCAT_DIR" 2>/dev/null || true
        print_warning "Set ownership to pi user (fallback)"
    fi
    
    # Set permissions
    chmod -R 755 "$BATHYCAT_DIR"
    print_success "Set permissions to 755"
}

# Test write access
test_write_access() {
    print_status "Testing write access..."
    
    test_file="$BATHYCAT_DIR/.write_test"
    
    if echo "BathyCat write test $(date)" > "$test_file" 2>/dev/null; then
        rm -f "$test_file"
        print_success "Write access confirmed"
    else
        print_error "Write access failed"
        print_status "Check permissions and filesystem type"
        exit 1
    fi
}

# Show storage information
show_storage_info() {
    print_status "USB Storage Information:"
    
    # Show mount info
    df -h "$MOUNT_POINT" | tail -1 | while read filesystem size used avail percent mount; do
        echo "  Filesystem: $filesystem"
        echo "  Size: $size"
        echo "  Used: $used"
        echo "  Available: $avail"
        echo "  Mount Point: $mount"
    done
    
    # Show directory structure
    echo ""
    print_status "BathyCat Directory Structure:"
    ls -la "$BATHYCAT_DIR"
}

# Setup automatic mounting (optional)
setup_auto_mount() {
    print_status "Setting up automatic mounting..."
    
    # Get UUID of the device
    UUID=$(blkid "$USB_PARTITION" -o value -s UUID 2>/dev/null)
    
    if [ -n "$UUID" ]; then
        # Check if entry already exists
        if ! grep -q "$UUID" /etc/fstab 2>/dev/null; then
            # Add to fstab
            echo "# BathyCat USB Storage - Added $(date)" >> /etc/fstab
            echo "UUID=$UUID $MOUNT_POINT auto defaults,noatime,nofail,uid=1000,gid=1000 0 0" >> /etc/fstab
            print_success "Added automatic mounting to /etc/fstab"
        else
            print_warning "Automatic mounting already configured"
        fi
    else
        print_warning "Could not determine UUID - automatic mounting not configured"
    fi
}

# Main function
main() {
    echo "🚀 BathyCat USB Storage Setup"
    echo "============================"
    echo ""
    
    check_permissions
    detect_usb_storage
    mount_usb_storage
    create_bathycat_directories
    test_write_access
    show_storage_info
    
    echo ""
    read -p "Do you want to set up automatic mounting on boot? (y/N): " setup_auto
    if [[ "$setup_auto" =~ ^[Yy]$ ]]; then
        setup_auto_mount
    fi
    
    echo ""
    print_success "BathyCat USB storage setup complete!"
    echo ""
    print_status "Next steps:"
    echo "  1. Test with: python3 tests/test_camera_capture.py --usb-only"
    echo "  2. Run BathyCat: python3 src/bathycat_imager.py"
    echo ""
}

# Run main function
main "$@"