#!/bin/bash
#
# BathyCat USB Auto-Mount Setup Script
# ===================================
# 
# This script sets up automatic mounting of the BathyCat USB drive
# with proper permissions and service dependencies.
#
# Usage: sudo ./setup_auto_mount.sh
#

set -e

echo "🔧 BathyCat USB Auto-Mount Setup"
echo "================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root"
    echo "   Usage: sudo ./setup_auto_mount.sh"
    exit 1
fi

# Get the bathyimager user UID and GID
BATHY_USER="bathyimager"
BATHY_UID=$(id -u $BATHY_USER 2>/dev/null || echo "")
BATHY_GID=$(id -g $BATHY_USER 2>/dev/null || echo "")

if [ -z "$BATHY_UID" ] || [ -z "$BATHY_GID" ]; then
    echo "❌ Error: User '$BATHY_USER' not found"
    echo "   Please create the bathyimager user first"
    exit 1
fi

echo "👤 User: $BATHY_USER (UID: $BATHY_UID, GID: $BATHY_GID)"

# USB drive details (update these if needed)
USB_UUID="FCDF-E63E"
USB_LABEL="BATHYCAT"  
MOUNT_POINT="/media/usb-storage"

echo "💾 USB Drive: $USB_LABEL (UUID: $USB_UUID)"
echo "📁 Mount Point: $MOUNT_POINT"

# Create mount point if it doesn't exist
echo "📁 Creating mount point..."
mkdir -p "$MOUNT_POINT"

# Create fstab entry for auto-mount
echo "⚙️ Configuring /etc/fstab..."

# Remove any existing entries for this UUID or mount point
sed -i.backup "/UUID=$USB_UUID/d" /etc/fstab
sed -i "\|$MOUNT_POINT|d" /etc/fstab

# Add new fstab entry with proper options for exfat
FSTAB_LINE="UUID=$USB_UUID $MOUNT_POINT exfat uid=$BATHY_UID,gid=$BATHY_GID,umask=0022,auto,user,rw,exec 0 0"
echo "$FSTAB_LINE" >> /etc/fstab

echo "✅ Added to /etc/fstab:"
echo "   $FSTAB_LINE"

# Create systemd mount unit for better control
echo "🔧 Creating systemd mount unit..."

MOUNT_UNIT_NAME="media-usb\\x2dstorage.mount"
MOUNT_UNIT_FILE="/etc/systemd/system/$MOUNT_UNIT_NAME"

cat > "$MOUNT_UNIT_FILE" << EOF
[Unit]
Description=BathyCat USB Storage Mount
After=multi-user.target
Before=bathycat-imager.service

[Mount]
What=UUID=$USB_UUID
Where=$MOUNT_POINT
Type=exfat
Options=uid=$BATHY_UID,gid=$BATHY_GID,umask=0022,rw,exec
TimeoutSec=30

[Install]
WantedBy=multi-user.target
RequiredBy=bathycat-imager.service
EOF

echo "✅ Created systemd mount unit: $MOUNT_UNIT_FILE"

# Create a pre-mount service to ensure the drive is ready
echo "🔧 Creating USB detection service..."

PRE_MOUNT_SERVICE="/etc/systemd/system/bathycat-usb-detect.service"

cat > "$PRE_MOUNT_SERVICE" << EOF
[Unit]
Description=BathyCat USB Drive Detection
DefaultDependencies=false
After=local-fs-pre.target
Before=local-fs.target media-usb\\x2dstorage.mount

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'timeout 30 bash -c "while ! blkid | grep -q $USB_UUID; do echo Waiting for USB drive...; sleep 1; done; echo USB drive detected"'
TimeoutStartSec=35

[Install]
WantedBy=local-fs.target
EOF

echo "✅ Created USB detection service: $PRE_MOUNT_SERVICE"

# Update BathyCat service to depend on USB mount
echo "🔧 Updating BathyCat service dependencies..."

BATHYCAT_SERVICE="/etc/systemd/system/bathycat-imager.service"

if [ -f "$BATHYCAT_SERVICE" ]; then
    # Backup original service file
    cp "$BATHYCAT_SERVICE" "$BATHYCAT_SERVICE.backup"
    
    # Update the [Unit] section to add dependencies
    sed -i '/^\[Unit\]/,/^\[/ {
        /^After=/c\After=multi-user.target network.target media-usb\\x2dstorage.mount
        /^Requires=/c\Requires=media-usb\\x2dstorage.mount
        /^Wants=/d
        /^\[Service\]/i Wants=bathycat-usb-detect.service
    }' "$BATHYCAT_SERVICE"
    
    # Add Requires and Wants if they don't exist
    if ! grep -q "^Requires=" "$BATHYCAT_SERVICE"; then
        sed -i '/^\[Unit\]/a Requires=media-usb\\x2dstorage.mount' "$BATHYCAT_SERVICE"
    fi
    
    if ! grep -q "^Wants=.*bathycat-usb-detect" "$BATHYCAT_SERVICE"; then
        sed -i '/^\[Unit\]/a Wants=bathycat-usb-detect.service' "$BATHYCAT_SERVICE"
    fi
    
    echo "✅ Updated BathyCat service dependencies"
else
    echo "⚠️ Warning: BathyCat service file not found at $BATHYCAT_SERVICE"
    echo "   You may need to install the service first"
fi

# Create a mount check script
echo "🔧 Creating mount verification script..."

MOUNT_CHECK_SCRIPT="/opt/bathycat/check_usb_mount.sh"
mkdir -p /opt/bathycat

cat > "$MOUNT_CHECK_SCRIPT" << 'EOF'
#!/bin/bash
#
# BathyCat USB Mount Check Script
# Verifies USB storage is properly mounted with write permissions
#

MOUNT_POINT="/media/usb-storage"
BATHYCAT_DIR="$MOUNT_POINT/bathycat"

echo "🔍 Checking USB mount status..."

# Check if mount point exists and is mounted
if ! mountpoint -q "$MOUNT_POINT"; then
    echo "❌ USB storage not mounted at $MOUNT_POINT"
    echo "🔧 Attempting to mount..."
    
    # Try to mount using fstab entry
    if mount "$MOUNT_POINT" 2>/dev/null; then
        echo "✅ Successfully mounted USB storage"
    else
        echo "❌ Failed to mount USB storage"
        echo "💡 Try: sudo mount -a"
        exit 1
    fi
else
    echo "✅ USB storage is mounted"
fi

# Check if BathyCat directory structure exists
if [ ! -d "$BATHYCAT_DIR" ]; then
    echo "📁 Creating BathyCat directory structure..."
    mkdir -p "$BATHYCAT_DIR"/{images,metadata,previews,logs,exports,test_images}
    echo "✅ Directory structure created"
else
    echo "✅ BathyCat directory exists"
fi

# Test write permissions
TEST_FILE="$BATHYCAT_DIR/mount_test_$(date +%s)"
if touch "$TEST_FILE" 2>/dev/null; then
    rm -f "$TEST_FILE"
    echo "✅ Write permissions OK"
    echo "🎉 USB storage is ready for BathyCat!"
    exit 0
else
    echo "❌ No write permissions to $BATHYCAT_DIR"
    echo "🔧 Current permissions:"
    ls -la "$MOUNT_POINT/"
    exit 1
fi
EOF

chmod +x "$MOUNT_CHECK_SCRIPT"
echo "✅ Created mount check script: $MOUNT_CHECK_SCRIPT"

# Reload systemd and enable services
echo "🔄 Reloading systemd configuration..."
systemctl daemon-reload

echo "🔧 Enabling services..."
systemctl enable bathycat-usb-detect.service
systemctl enable "$MOUNT_UNIT_NAME"

# Test the mount immediately if USB is connected
echo "🧪 Testing USB mount..."
if blkid | grep -q "$USB_UUID"; then
    echo "✅ USB drive is connected"
    
    # Unmount if currently mounted (to test fresh mount)
    if mountpoint -q "$MOUNT_POINT"; then
        echo "📤 Unmounting current mount for fresh test..."
        umount "$MOUNT_POINT" || echo "⚠️ Could not unmount (may be in use)"
    fi
    
    # Test mount using new configuration
    echo "📥 Testing mount with new configuration..."
    if mount -a && mountpoint -q "$MOUNT_POINT"; then
        echo "✅ Mount test successful!"
        
        # Run mount check script
        if bash "$MOUNT_CHECK_SCRIPT"; then
            echo "🎉 USB auto-mount setup completed successfully!"
            echo ""
            echo "📋 Summary:"
            echo "   • USB UUID: $USB_UUID"
            echo "   • Mount Point: $MOUNT_POINT"
            echo "   • Auto-mount: Enabled"
            echo "   • Permissions: bathyimager user"
            echo "   • Service Dependencies: Configured"
            echo ""
            echo "🔄 Reboot the system to test automatic mounting"
            echo "🚀 After reboot, BathyCat service will wait for USB mount"
        else
            echo "❌ Mount check failed - please review configuration"
            exit 1
        fi
    else
        echo "❌ Mount test failed"
        echo "💡 Check USB connection and filesystem type"
        exit 1
    fi
else
    echo "⚠️ USB drive not detected"
    echo "   Connect the BathyCat USB drive and run this script again"
    echo "   Or reboot to test automatic mounting when USB is connected"
fi

echo ""
echo "✅ Auto-mount setup complete!"