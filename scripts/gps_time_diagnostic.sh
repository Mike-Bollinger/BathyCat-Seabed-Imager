#!/bin/bash
#
# GPS Time Sync Diagnostic Script
# ===============================
#
# Tests GPS time synchronization capabilities
#

echo "🕐 GPS Time Sync Diagnostics"
echo "============================"

# Check current user and permissions
echo ""
echo "👤 User and Permissions:"
echo "   Current user: $(whoami)"
echo "   User ID: $(id)"

# Check if user can run sudo
if sudo -n true 2>/dev/null; then
    echo "   ✅ Sudo access: Available"
else
    echo "   ❌ Sudo access: Not available (may need password)"
fi

# Check GPS time sync script
echo ""
echo "📄 GPS Time Sync Script:"
SCRIPT_PATH="$(dirname "$0")/gps_set_time.sh"
if [ -f "$SCRIPT_PATH" ]; then
    echo "   ✅ Script exists: $SCRIPT_PATH"
    if [ -x "$SCRIPT_PATH" ]; then
        echo "   ✅ Script executable: Yes"
    else
        echo "   ❌ Script executable: No"
        echo "   Fix: chmod +x $SCRIPT_PATH"
    fi
else
    echo "   ❌ Script missing: $SCRIPT_PATH"
fi

# Check system commands
echo ""
echo "🛠️  System Commands:"
if command -v timedatectl >/dev/null 2>&1; then
    echo "   ✅ timedatectl: Available"
else
    echo "   ❌ timedatectl: Not available"
fi

if command -v date >/dev/null 2>&1; then
    echo "   ✅ date: Available"
else
    echo "   ❌ date: Not available"
fi

# Check current time settings
echo ""
echo "⏰ Current Time Configuration:"
echo "   System time: $(date)"
echo "   UTC time: $(date -u)"

if command -v timedatectl >/dev/null 2>&1; then
    echo ""
    echo "🔧 Timedatectl Status:"
    timedatectl status 2>/dev/null | head -10 || echo "   Error: Cannot read timedatectl status"
fi

# Test GPS time sync with a fake GPS time (current time + 1 second)
echo ""
echo "🧪 Testing GPS Time Sync:"
if [ -f "$SCRIPT_PATH" ] && [ -x "$SCRIPT_PATH" ]; then
    TEST_TIME=$(date -u -d '+1 second' '+%Y-%m-%d %H:%M:%S')
    echo "   Test GPS time: $TEST_TIME UTC"
    echo "   Running: sudo $SCRIPT_PATH '$TEST_TIME'"
    
    if sudo "$SCRIPT_PATH" "$TEST_TIME"; then
        echo "   ✅ GPS time sync test: SUCCESS"
        echo "   New system time: $(date -u)"
        
        # Reset to current time
        CURRENT_TIME=$(date -u '+%Y-%m-%d %H:%M:%S')
        sudo "$SCRIPT_PATH" "$CURRENT_TIME" >/dev/null 2>&1 || true
    else
        echo "   ❌ GPS time sync test: FAILED"
    fi
else
    echo "   ⚠️  Cannot test - script not available or not executable"
fi

# Check sudoers configuration for GPS time sync
echo ""
echo "🔐 Sudoers Configuration:"
if [ -f "/etc/sudoers.d/bathyimager-gps-sync" ]; then
    echo "   ✅ GPS sync sudoers file exists"
    echo "   Content:"
    cat /etc/sudoers.d/bathyimager-gps-sync 2>/dev/null | sed 's/^/      /' || echo "      Error reading file"
else
    echo "   ❌ GPS sync sudoers file missing: /etc/sudoers.d/bathyimager-gps-sync"
    echo "   This may cause GPS time sync to fail"
fi

# Check NTP status
echo ""
echo "🌐 NTP Status:"
if command -v timedatectl >/dev/null 2>&1; then
    NTP_STATUS=$(timedatectl status 2>/dev/null | grep -E "NTP|synchronization" || echo "NTP status unknown")
    echo "   $NTP_STATUS"
    
    if echo "$NTP_STATUS" | grep -q "active\|yes"; then
        echo "   ⚠️  NTP is active - may interfere with manual time setting"
        echo "   Consider disabling NTP temporarily during GPS sync"
    fi
else
    echo "   ⚠️  Cannot check NTP status (timedatectl not available)"
fi

# Recommendations
echo ""
echo "💡 Troubleshooting Tips:"
echo "   • Check GPS fix status: ./tests/quick_gps_check.py"
echo "   • Run with debug logging: LOG_LEVEL=DEBUG ./run_bathyimager.sh"
echo "   • Manual time sync test: sudo ./scripts/gps_set_time.sh \"\$(date -u '+%Y-%m-%d %H:%M:%S')\""
echo "   • Check system logs: sudo journalctl -u bathyimager | grep -i time"

echo ""
echo "✨ Diagnostic complete!"