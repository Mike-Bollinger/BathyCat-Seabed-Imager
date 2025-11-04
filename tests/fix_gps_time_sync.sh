#!/bin/bash
#
# BathyCat GPS Time Sync Fix Script  
# =================================
#
# Fixes GPS time sync issues and permission problems
#

echo "🔧 BathyCat GPS Time Sync Fix"
echo "============================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Not in BathyCat project directory"
    echo "   Please run this script from the project root"
    exit 1
fi

# Check if running as root (needed for some operations)
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root"
    echo "   Run: sudo $0"
    exit 1
fi

echo ""
echo "🔒 Fixing script permissions..."

# Fix all script permissions
chmod +x scripts/*.sh
chmod +x update
chmod +x run_bathyimager.sh 2>/dev/null || true

echo "   ✅ Script permissions fixed"

echo ""
echo "🔧 Fixing GPS time sync permissions..."

# Run the device permissions setup
if [ -f "scripts/setup_device_permissions.sh" ]; then
    bash scripts/setup_device_permissions.sh
    echo "   ✅ Device permissions configured"
else
    echo "   ❌ Device permissions script not found"
fi

echo ""
echo "🌐 Configuring NTP for GPS time sync..."

# Check if NTP is active
if timedatectl status | grep -q "NTP service: active"; then
    echo "   ⚠️  NTP is currently active"
    echo "   GPS time sync will temporarily disable NTP during sync operations"
    echo "   This is normal and automatic"
else
    echo "   ✅ NTP is not active - GPS time sync should work normally"
fi

echo ""
echo "🧪 Testing GPS time sync..."

# Test GPS time sync script
if [ -f "scripts/gps_set_time.sh" ] && [ -x "scripts/gps_set_time.sh" ]; then
    TEST_TIME=$(date -u '+%Y-%m-%d %H:%M:%S')
    echo "   Testing with time: $TEST_TIME UTC"
    
    if ./scripts/gps_set_time.sh "$TEST_TIME"; then
        echo "   ✅ GPS time sync test: SUCCESS"
    else
        echo "   ❌ GPS time sync test: FAILED"
        echo "   Check NTP status and permissions"
    fi
else
    echo "   ❌ GPS time sync script not found or not executable"
    echo "   Expected: scripts/gps_set_time.sh"
fi

echo ""
echo "🔄 Restarting BathyImager service..."

# Stop service if running
systemctl stop bathyimager 2>/dev/null || true

# Wait a moment
sleep 2

# Start service
if systemctl start bathyimager; then
    echo "   ✅ Service started successfully"
    
    # Wait for initialization
    sleep 5
    
    echo ""
    echo "📊 Service status:"
    systemctl status bathyimager --no-pager -l
    
    echo ""
    echo "📝 Recent logs:"
    journalctl -u bathyimager --since "1 minute ago" --no-pager
    
else
    echo "   ❌ Service failed to start"
    echo ""
    echo "📊 Service status:"
    systemctl status bathyimager --no-pager -l
    
    echo ""
    echo "📝 Error logs:"
    journalctl -u bathyimager --since "1 minute ago" --no-pager
fi

echo ""
echo "💡 Monitoring Commands:"
echo "   • Watch logs: sudo journalctl -u bathyimager -f"
echo "   • Service status: sudo systemctl status bathyimager"
echo "   • GPS diagnostic: ./scripts/gps_time_diagnostic.sh"
echo "   • Hardware check: ./scripts/hardware_diagnostics.sh all"

echo ""
echo "✨ Fix complete!"