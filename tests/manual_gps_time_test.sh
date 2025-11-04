#!/bin/bash
#
# Quick GPS Time Sync Manual Test
# ===============================
#
# Run this to manually test GPS time sync and debug the exact issue
#

echo "🧪 Manual GPS Time Sync Test"
echo "============================="

# Check current directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Not in BathyCat project directory"
    echo "   Current directory: $(pwd)"
    echo "   Please run from the project root"
    exit 1
fi

echo ""
echo "📍 System Status:"
echo "   Current time: $(date)"
echo "   UTC time: $(date -u)"
echo "   User: $(whoami)"
echo "   Groups: $(groups)"

echo ""
echo "🔍 GPS Script Check:"
GPS_SCRIPT="./scripts/gps_set_time.sh"

if [ ! -f "$GPS_SCRIPT" ]; then
    echo "❌ GPS script not found: $GPS_SCRIPT"
    exit 1
fi

if [ ! -x "$GPS_SCRIPT" ]; then
    echo "❌ GPS script not executable: $GPS_SCRIPT"
    echo "   Fixing permissions..."
    chmod +x "$GPS_SCRIPT"
fi

echo "✅ GPS script found and executable: $GPS_SCRIPT"

echo ""
echo "🧪 Manual Time Sync Test:"
TEST_TIME=$(date -u '+%Y-%m-%d %H:%M:%S')
echo "   Test time: $TEST_TIME UTC"
echo "   Running: sudo $GPS_SCRIPT '$TEST_TIME'"

echo ""
echo "--- GPS Script Output ---"
if sudo "$GPS_SCRIPT" "$TEST_TIME"; then
    RESULT_CODE=$?
    echo "--- End GPS Script Output ---"
    echo ""
    echo "✅ GPS time sync test: SUCCESS (exit code: $RESULT_CODE)"
else
    RESULT_CODE=$?
    echo "--- End GPS Script Output ---"
    echo ""
    echo "❌ GPS time sync test: FAILED (exit code: $RESULT_CODE)"
    
    echo ""
    echo "🔧 Debugging Information:"
    echo "   • Exit code meanings:"
    echo "     - 1: General error (permissions, NTP conflicts, etc.)"
    echo "     - 126: Script not executable"
    echo "     - 127: Script not found"
    echo "   • Check NTP status: timedatectl status | grep NTP"
    echo "   • Check permissions: ls -la $GPS_SCRIPT"
    echo "   • Manual time set test: sudo timedatectl set-time '$TEST_TIME'"
fi

echo ""
echo "⚙️  Current System Configuration:"
echo "--- Timedatectl Status ---"
timedatectl status
echo "--- End Timedatectl Status ---"

echo ""
echo "🔐 Sudoers Configuration:"
if [ -f "/etc/sudoers.d/bathyimager-gps" ]; then
    echo "✅ GPS sudoers file exists"
    echo "--- Sudoers Content ---"
    sudo cat /etc/sudoers.d/bathyimager-gps
    echo "--- End Sudoers Content ---"
else
    echo "❌ GPS sudoers file not found: /etc/sudoers.d/bathyimager-gps"
    echo "   This may require password entry for GPS time sync"
fi

echo ""
echo "📊 Service Status:"
if systemctl is-active bathyimager >/dev/null 2>&1; then
    echo "✅ BathyImager service is running"
    echo ""
    echo "📝 Recent service logs (time sync related):"
    echo "--- Service Logs ---"
    sudo journalctl -u bathyimager --since "10 minutes ago" | grep -i "time sync\|gps.*time" | tail -10
    echo "--- End Service Logs ---"
else
    echo "⚠️  BathyImager service is not running"
    echo "   Start with: sudo systemctl start bathyimager"
fi

echo ""
echo "💡 Next Steps:"
if [ $RESULT_CODE -eq 0 ]; then
    echo "   ✅ Manual GPS time sync works!"
    echo "   • If service still fails, check GPS device connection"
    echo "   • Monitor service logs: sudo journalctl -u bathyimager -f"
    echo "   • Test GPS fix: ./tests/quick_gps_check.py"
else
    echo "   ❌ Manual GPS time sync failed"
    echo "   • Check NTP conflicts: sudo timedatectl set-ntp false"
    echo "   • Check script permissions: ls -la $GPS_SCRIPT"
    echo "   • Test minimal time set: sudo date '$TEST_TIME'"
    echo "   • Run full diagnostic: ./tests/test_gps_time_sync.py"
fi

echo ""
echo "🔄 Service Operations:"
echo "   • Restart service: sudo systemctl restart bathyimager"
echo "   • Watch logs live: sudo journalctl -u bathyimager -f"
echo "   • Stop service: sudo systemctl stop bathyimager"

echo ""
echo "✨ Manual test complete!"