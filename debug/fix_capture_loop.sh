#!/bin/bash
# Quick update script to fix the capture loop issues

echo "🔧 Applying capture loop fixes..."

# Create a backup first
cp src/bathycat_imager.py src/bathycat_imager.py.backup.$(date +%Y%m%d_%H%M%S)
cp src/camera_controller.py src/camera_controller.py.backup.$(date +%Y%m%d_%H%M%S)

echo "📦 Backups created"

# Apply the main fix - replace the problematic 'if image_data:' line
sed -i 's/if image_data:/if image_data is not None:/g' src/bathycat_imager.py

# Add debugging to see what's happening
echo "✅ Applied NumPy array fix"

echo "🧪 Testing the fixes..."
python3 -c "
import sys
sys.path.append('src')
try:
    from bathycat_imager import BathyCatImager
    print('✅ bathycat_imager module loads successfully')
except Exception as e:
    print(f'❌ Error loading bathycat_imager: {e}')

try:
    from camera_controller import CameraController
    print('✅ camera_controller module loads successfully')
except Exception as e:
    print(f'❌ Error loading camera_controller: {e}')
"

echo ""
echo "🚀 Fixes applied! Now test with:"
echo "   ./scripts/start_capture.sh"
