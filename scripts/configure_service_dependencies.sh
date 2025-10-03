#!/bin/bash
#
# BathyCat Service Dependencies Configuration
# ==========================================
# 
# This script updates the BathyCat systemd service to properly depend
# on USB storage being mounted before starting.
#

set -e

echo "🔧 BathyCat Service Dependencies Setup"
echo "======================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root"
    echo "   Usage: sudo ./configure_service_dependencies.sh"
    exit 1
fi

BATHYCAT_SERVICE="/etc/systemd/system/bathycat-imager.service"

# Check if BathyCat service exists
if [ ! -f "$BATHYCAT_SERVICE" ]; then
    echo "❌ Error: BathyCat service not found at $BATHYCAT_SERVICE"
    echo "   Please install the BathyCat service first"
    exit 1
fi

echo "📋 Found BathyCat service: $BATHYCAT_SERVICE"

# Backup the original service file
BACKUP_FILE="$BATHYCAT_SERVICE.backup-$(date +%Y%m%d-%H%M%S)"
cp "$BATHYCAT_SERVICE" "$BACKUP_FILE"
echo "💾 Backup created: $BACKUP_FILE"

# Create the updated service configuration
echo "🔧 Updating service configuration..."

cat > "$BATHYCAT_SERVICE" << 'EOF'
[Unit]
Description=BathyCat Seabed Imager
After=multi-user.target network.target media-usb\x2dstorage.mount
Requires=media-usb\x2dstorage.mount
Wants=bathycat-usb-detect.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=bathyimager
Group=bathyimager
WorkingDirectory=/opt/bathycat
Environment=PYTHONPATH=/opt/bathycat
ExecStartPre=/opt/bathycat/check_usb_mount.sh
ExecStart=/home/bathyimager/bathycat-venv/bin/python /opt/bathycat/bathycat_imager.py --config /etc/bathycat/bathycat_config.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bathycat-imager

# Resource limits
LimitNOFILE=65536
MemoryAccounting=true
MemoryMax=1G

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/media/usb-storage /tmp /var/tmp
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service configuration updated"

# Show the differences
echo "📋 Configuration changes:"
echo "   • Added USB mount dependency (media-usb\x2dstorage.mount)"
echo "   • Added USB detection service dependency"
echo "   • Added pre-start USB mount check"
echo "   • Added resource limits and security settings"
echo "   • Configured proper restart behavior"

# Reload systemd
echo "🔄 Reloading systemd configuration..."
systemctl daemon-reload

# Re-enable the service to update dependencies
echo "🔧 Re-enabling BathyCat service..."
systemctl disable bathycat-imager.service
systemctl enable bathycat-imager.service

echo "✅ Service dependencies configured successfully!"
echo ""
echo "📋 Service Status:"
systemctl status bathycat-imager.service --no-pager -l || true
echo ""
echo "🔍 Service Dependencies:"
systemctl list-dependencies bathycat-imager.service --no-pager || true
echo ""
echo "💡 The BathyCat service will now:"
echo "   • Wait for USB storage to be mounted before starting"
echo "   • Verify USB mount and permissions before starting"
echo "   • Restart automatically if it fails"
echo "   • Run with proper security restrictions"