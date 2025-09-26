#!/bin/bash
#
# Camera Permission Fix Script for BathyCat
# Fixes common camera access issues on Raspberry Pi
#

echo "🔧 BathyCat Camera Permission Fix"
echo "================================"

# Get current user
CURRENT_USER=$(whoami)
echo "👤 Current user: $CURRENT_USER"

# Check if user is in video group
if groups $CURRENT_USER | grep -q video; then
    echo "✅ User $CURRENT_USER is already in video group"
else
    echo "❌ User $CURRENT_USER is NOT in video group"
    echo "🔧 Adding user to video group..."
    sudo usermod -a -G video $CURRENT_USER
    echo "✅ User added to video group"
    echo "⚠️  Please log out and back in for changes to take effect"
fi

# Check video device permissions
echo ""
echo "📹 Checking video device permissions..."
if [ -e /dev/video0 ]; then
    ls -la /dev/video0
    
    # Set proper permissions if needed
    echo "🔧 Setting camera device permissions..."
    sudo chmod 666 /dev/video0
    echo "✅ Camera permissions updated"
else
    echo "❌ /dev/video0 not found"
    echo "🔍 Listing all video devices:"
    ls -la /dev/video* 2>/dev/null || echo "No video devices found"
fi

# Check for camera processes
echo ""
echo "🔍 Checking for processes using camera..."
CAMERA_PROCS=$(lsof /dev/video* 2>/dev/null)
if [ -n "$CAMERA_PROCS" ]; then
    echo "🔒 Processes using camera:"
    echo "$CAMERA_PROCS"
    echo "⚠️  You may need to stop these processes"
else
    echo "✅ No processes currently using camera"
fi

# Check BathyCat service status
echo ""
echo "🔍 Checking BathyCat service status..."
if systemctl is-active --quiet bathycat-imager; then
    echo "🔄 BathyCat service is running - stopping it..."
    sudo systemctl stop bathycat-imager
    echo "✅ BathyCat service stopped"
else
    echo "✅ BathyCat service is not running"
fi

echo ""
echo "🏁 Camera permission fix complete!"
echo ""
echo "Next steps:"
echo "1. Run: python3 debug/camera_diagnostics.py"
echo "2. If still having issues, log out and back in"
echo "3. Test camera with: python3 debug/simple_camera_test.py"
echo "4. Start BathyCat: sudo systemctl start bathycat-imager"
