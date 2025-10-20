#!/bin/bash
#
# USB Storage Auto-Mount for BathyImager
# ====================================
#
# Mounts USB storage at /media/usb for BathyImager
#

set -e

# Colors
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

echo "💾 BathyImager USB Storage Setup"
echo "==============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

MOUNT_POINT="/media/usb"
SERVICE_USER="bathyimager"

# Create mount point
print_status "Creating mount point: $MOUNT_POINT"
mkdir -p "$MOUNT_POINT"

# Find USB storage device
print_status "Looking for USB storage device..."
USB_DEVICE=""

# Look for the BATHYCAT labeled device first
for device in /dev/sd[a-z][0-9]*; do
    if [ -b "$device" ]; then
        # Check if it's the BATHYCAT device
        LABEL=$(lsblk -no LABEL "$device" 2>/dev/null || echo "")
        if [ "$LABEL" = "BATHYCAT" ]; then
            USB_DEVICE="$device"
            print_success "Found BATHYCAT device: $USB_DEVICE"
            break
        fi
    fi
done

# If no BATHYCAT device found, look for any USB storage
if [ -z "$USB_DEVICE" ]; then
    for device in /dev/sda1 /dev/sdb1 /dev/sdc1; do
        if [ -b "$device" ]; then
            # Check if it's removable storage
            PARENT=$(echo "$device" | sed 's/[0-9]*$//')
            if [ -f "/sys/block/$(basename $PARENT)/removable" ]; then
                REMOVABLE=$(cat "/sys/block/$(basename $PARENT)/removable")
                if [ "$REMOVABLE" = "1" ]; then
                    USB_DEVICE="$device"
                    print_warning "Found USB device: $USB_DEVICE (not labeled BATHYCAT)"
                    break
                fi
            fi
        fi
    done
fi

if [ -z "$USB_DEVICE" ]; then
    print_error "No USB storage device found!"
    print_status "Available devices:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT
    exit 1
fi

# Check if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    CURRENT_DEVICE=$(findmnt -n -o SOURCE "$MOUNT_POINT")
    if [ "$CURRENT_DEVICE" = "$USB_DEVICE" ]; then
        print_success "USB device already mounted at $MOUNT_POINT"
    else
        print_warning "Different device mounted at $MOUNT_POINT, unmounting..."
        umount "$MOUNT_POINT"
    fi
fi

# Mount the USB device
if ! mountpoint -q "$MOUNT_POINT"; then
    print_status "Mounting $USB_DEVICE at $MOUNT_POINT..."
    
    # Determine filesystem type
    FSTYPE=$(lsblk -no FSTYPE "$USB_DEVICE" 2>/dev/null || echo "")
    
    case "$FSTYPE" in
        "exfat")
            mount -t exfat -o defaults,uid=1000,gid=1000,umask=0002 "$USB_DEVICE" "$MOUNT_POINT"
            ;;
        "vfat"|"fat32")
            mount -t vfat -o defaults,uid=1000,gid=1000,umask=0002 "$USB_DEVICE" "$MOUNT_POINT"
            ;;
        "ext4"|"ext3"|"ext2")
            mount -t "$FSTYPE" "$USB_DEVICE" "$MOUNT_POINT"
            ;;
        *)
            print_warning "Unknown filesystem type: $FSTYPE, trying auto-mount..."
            mount "$USB_DEVICE" "$MOUNT_POINT"
            ;;
    esac
    
    print_success "USB device mounted successfully"
fi

# Set permissions for bathyimager user
print_status "Setting permissions for user: $SERVICE_USER"
chown -R "$SERVICE_USER:$SERVICE_USER" "$MOUNT_POINT" 2>/dev/null || {
    print_warning "Could not change ownership (normal for some filesystems)"
    # For filesystems that don't support ownership changes, ensure mount options handle permissions
}

# Test write access
print_status "Testing write access..."
if su -c "touch $MOUNT_POINT/bathyimager_test" "$SERVICE_USER" 2>/dev/null; then
    su -c "rm $MOUNT_POINT/bathyimager_test" "$SERVICE_USER"
    print_success "Write access confirmed for $SERVICE_USER"
else
    print_error "Write access failed for $SERVICE_USER"
    print_status "Current mount info:"
    mount | grep "$MOUNT_POINT"
    ls -la "$MOUNT_POINT"
fi

# Show final status
print_status "Final mount status:"
df -h "$MOUNT_POINT"
echo
print_success "USB storage setup complete!"
echo "Mount point: $MOUNT_POINT"
echo "Device: $USB_DEVICE"
echo "Available for BathyImager service"

# Create auto-mount service (optional)
read -p "Create systemd auto-mount service? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Creating auto-mount service..."
    
    cat > /etc/systemd/system/bathyimager-usb.service << EOF
[Unit]
Description=BathyImager USB Storage Auto-Mount
Before=bathyimager.service
After=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash $(pwd)/scripts/mount_usb.sh
ExecStop=/bin/umount $MOUNT_POINT
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable bathyimager-usb.service
    print_success "Auto-mount service created and enabled"
fi