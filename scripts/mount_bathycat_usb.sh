#!/bin/bash
#
# BathyCat USB Quick Mount Script
# ==============================
# 
# Quick script to mount the BathyCat USB drive with proper permissions
# Use this for immediate mounting without setting up auto-mount
#
# Usage: sudo ./mount_bathycat_usb.sh
#

set -e

echo "💾 BathyCat USB Quick Mount"
echo "==========================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root"
    echo "   Usage: sudo ./mount_bathycat_usb.sh"
    exit 1
fi

# Configuration
USB_UUID="FCDF-E63E"
USB_LABEL="BATHYCAT"
MOUNT_POINT="/media/usb-storage"
BATHY_USER="bathyimager"

# Get user ID and group ID
BATHY_UID=$(id -u $BATHY_USER 2>/dev/null || echo "")
BATHY_GID=$(id -g $BATHY_USER 2>/dev/null || echo "")

if [ -z "$BATHY_UID" ] || [ -z "$BATHY_GID" ]; then
    echo "❌ Error: User '$BATHY_USER' not found"
    exit 1
fi

echo "👤 User: $BATHY_USER (UID: $BATHY_UID, GID: $BATHY_GID)"
echo "💾 Looking for USB: $USB_LABEL (UUID: $USB_UUID)"

# Check if USB drive is connected
if ! blkid | grep -q "$USB_UUID"; then
    echo "❌ Error: BathyCat USB drive not detected"
    echo "   Expected UUID: $USB_UUID"
    echo "   Expected Label: $USB_LABEL"
    echo ""
    echo "📋 Connected USB devices:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID | grep -E "(NAME|usb|sda)" || echo "   No USB storage found"
    echo ""
    echo "💡 Make sure the BathyCat USB drive is connected"
    exit 1
fi

# Find the device path
USB_DEVICE=$(blkid | grep "$USB_UUID" | cut -d: -f1)
echo "✅ Found USB device: $USB_DEVICE"

# Create mount point
echo "📁 Creating mount point: $MOUNT_POINT"
mkdir -p "$MOUNT_POINT"

# Unmount if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    echo "📤 Unmounting existing mount..."
    umount "$MOUNT_POINT" || {
        echo "❌ Failed to unmount - device may be busy"
        echo "💡 Try: sudo fuser -km $MOUNT_POINT"
        exit 1
    }
fi

# Mount with proper permissions for exFAT
echo "📥 Mounting USB drive..."
if mount -t exfat -o uid=$BATHY_UID,gid=$BATHY_GID,umask=0022 "$USB_DEVICE" "$MOUNT_POINT"; then
    echo "✅ Successfully mounted $USB_DEVICE to $MOUNT_POINT"
else
    echo "❌ Failed to mount USB drive"
    echo "💡 Trying alternative mount options..."
    
    # Try with auto filesystem detection
    if mount -o uid=$BATHY_UID,gid=$BATHY_GID,umask=0022 "$USB_DEVICE" "$MOUNT_POINT"; then
        echo "✅ Successfully mounted with auto-detection"
    else
        echo "❌ Mount failed completely"
        echo "🔍 Device info:"
        file -s "$USB_DEVICE"
        exit 1
    fi
fi

# Verify mount
echo "🔍 Verifying mount..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "✅ Mount point is active"
    
    # Show mount details
    echo "📋 Mount details:"
    df -h "$MOUNT_POINT"
    echo ""
    mount | grep "$MOUNT_POINT"
    echo ""
    
    # Check permissions
    echo "🔒 Checking permissions..."
    ls -la "$MOUNT_POINT/"
    
    # Create BathyCat directory structure if needed
    BATHYCAT_DIR="$MOUNT_POINT/bathycat"
    if [ ! -d "$BATHYCAT_DIR" ]; then
        echo "📁 Creating BathyCat directory structure..."
        mkdir -p "$BATHYCAT_DIR"/{images,metadata,previews,logs,exports,test_images}
        echo "✅ Directory structure created"
    else
        echo "✅ BathyCat directory exists"
    fi
    
    # Test write permissions
    echo "🧪 Testing write permissions..."
    TEST_FILE="$BATHYCAT_DIR/mount_test_$(date +%s)"
    if su - "$BATHY_USER" -c "touch '$TEST_FILE'" 2>/dev/null; then
        rm -f "$TEST_FILE"
        echo "✅ Write permissions OK for user $BATHY_USER"
        echo ""
        echo "🎉 BathyCat USB storage is ready!"
        echo "📁 Available at: $MOUNT_POINT"
        echo "💾 Free space: $(df -h '$MOUNT_POINT' | tail -1 | awk '{print $4}')"
        echo ""
        echo "🚀 You can now start the BathyCat service:"
        echo "   sudo systemctl start bathycat-imager"
    else
        echo "❌ Write permission test failed"
        echo "🔒 Current ownership:"
        ls -la "$MOUNT_POINT/"
        echo ""
        echo "🔧 Trying to fix permissions..."
        chown -R "$BATHY_USER:$BATHY_USER" "$BATHYCAT_DIR" 2>/dev/null && echo "✅ Permissions fixed" || echo "❌ Permission fix failed"
    fi
else
    echo "❌ Mount verification failed"
    exit 1
fi