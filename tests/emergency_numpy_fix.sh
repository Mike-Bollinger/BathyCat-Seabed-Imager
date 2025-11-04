#!/bin/bash
#
# BathyCat Seabed Imager - Emergency Numpy Loop Fix
# =================================================
# 
# Fixes the infinite loop issue during numpy installation by:
# 1. Killing any hanging pip processes
# 2. Clearing pip cache
# 3. Installing numpy from piwheels first
# 4. Then installing remaining dependencies
#
# Usage: 
#   ./scripts/emergency_numpy_fix.sh
#
# Author: Mike Bollinger
# Date: November 2025

set -e

echo "🚨 BathyImager Emergency Numpy Fix"
echo "================================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Not in BathyImager project directory"
    echo "   Please run this script from the project root"
    exit 1
fi

# Kill any hanging pip processes
echo "🛑 Stopping any hanging pip processes..."
pkill -f "pip.*numpy" 2>/dev/null || true
pkill -f "python.*setup.py" 2>/dev/null || true
sleep 2

# Clear pip cache to prevent corrupted downloads
echo "🧹 Clearing pip cache..."
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate 2>/dev/null || true
    venv/bin/pip cache purge 2>/dev/null || true
    deactivate 2>/dev/null || true
else
    pip3 cache purge 2>/dev/null || true
fi

# Function to emergency fix venv
emergency_fix_venv() {
    echo "🐍 Emergency fixing virtual environment..."
    
    if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
        echo "❌ Virtual environment not found - creating new one..."
        python3 -m venv venv --system-site-packages
    fi
    
    if ! source venv/bin/activate 2>/dev/null; then
        echo "❌ Could not activate venv - recreating..."
        rm -rf venv
        python3 -m venv venv --system-site-packages
        source venv/bin/activate
    fi
    
    echo "   Upgrading pip tools..."
    venv/bin/pip install --upgrade pip setuptools wheel --no-cache-dir
    
    echo "   Removing any broken numpy installation..."
    venv/bin/pip uninstall numpy opencv-python -y 2>/dev/null || true
    
    echo "   Installing numpy from piwheels (ARM-optimized)..."
    if venv/bin/pip install numpy==1.26.4 \
        --index-url https://www.piwheels.org/simple \
        --extra-index-url https://pypi.org/simple \
        --no-cache-dir \
        --timeout 60; then
        echo "   ✅ Numpy installed from piwheels"
    else
        echo "   ⚠️  Piwheels failed, trying system numpy..."
        # Try to use system numpy if available
        if python3 -c "import numpy" 2>/dev/null; then
            echo "   ✅ Using system numpy"
        else
            echo "   ❌ Failed to get numpy - trying one more approach..."
            venv/bin/pip install --no-binary=:none: --no-build-isolation numpy==1.26.4 --timeout 30
        fi
    fi
    
    echo "   Installing remaining dependencies (excluding problematic ones)..."
    # Create temporary requirements file without numpy
    grep -v "numpy" requirements.txt > /tmp/requirements_no_numpy.txt
    
    venv/bin/pip install -r /tmp/requirements_no_numpy.txt \
        --prefer-binary \
        --only-binary=opencv-python,Pillow \
        --extra-index-url https://www.piwheels.org/simple \
        --timeout 300 || echo "   ⚠️  Some packages may have failed"
    
    rm /tmp/requirements_no_numpy.txt 2>/dev/null || true
    
    echo "   Testing installation..."
    if venv/bin/python -c "import numpy, cv2; print(f'✅ Core packages working: numpy {numpy.__version__}, opencv {cv2.__version__}')"; then
        echo "   ✅ Emergency fix successful"
    else
        echo "   ⚠️  Some issues remain - but basic functionality may work"
    fi
    
    deactivate 2>/dev/null || true
}

# Function to emergency fix system python
emergency_fix_system() {
    echo "🐍 Emergency fixing system Python..."
    
    echo "   Upgrading pip tools..."
    pip3 install --upgrade pip setuptools wheel --user --no-cache-dir
    
    echo "   Removing any broken numpy installation..."
    pip3 uninstall numpy opencv-python -y 2>/dev/null || true
    
    echo "   Installing numpy from piwheels..."
    if pip3 install numpy==1.26.4 --user \
        --index-url https://www.piwheels.org/simple \
        --extra-index-url https://pypi.org/simple \
        --no-cache-dir \
        --timeout 60; then
        echo "   ✅ Numpy installed from piwheels"
    else
        echo "   ❌ Failed to install numpy"
        return 1
    fi
    
    echo "   Installing remaining dependencies..."
    grep -v "numpy" requirements.txt > /tmp/requirements_no_numpy.txt
    
    pip3 install -r /tmp/requirements_no_numpy.txt --user \
        --prefer-binary \
        --only-binary=opencv-python,Pillow \
        --extra-index-url https://www.piwheels.org/simple \
        --timeout 300 || echo "   ⚠️  Some packages may have failed"
    
    rm /tmp/requirements_no_numpy.txt 2>/dev/null || true
    
    echo "   Testing installation..."
    if python3 -c "import numpy, cv2; print(f'✅ Core packages working: numpy {numpy.__version__}, opencv {cv2.__version__}')"; then
        echo "   ✅ Emergency fix successful"
    else
        echo "   ⚠️  Some issues remain"
        return 1
    fi
}

# Main execution
echo ""
echo "🔍 Analyzing the situation..."

# Check what's currently running
HANGING_PIDS=$(pgrep -f "pip.*install" 2>/dev/null || true)
if [ -n "$HANGING_PIDS" ]; then
    echo "⚠️  Found hanging pip processes: $HANGING_PIDS"
    echo "   Terminating them..."
    echo "$HANGING_PIDS" | xargs kill -9 2>/dev/null || true
    sleep 3
fi

echo ""
echo "🛠️  Applying emergency fix..."

if [ -d "venv" ]; then
    echo "📁 Virtual environment detected - fixing venv installation..."
    emergency_fix_venv
else
    echo "📁 No virtual environment - fixing system installation..."
    emergency_fix_system
fi

echo ""
echo "✨ Emergency fix complete!"
echo ""
echo "🧪 Testing the fix:"
echo "-------------------"
if [ -d "venv" ]; then
    echo "Virtual environment test:"
    source venv/bin/activate 2>/dev/null
    python -c "
import sys
sys.path.append('src')
try:
    import numpy
    print(f'✅ Numpy {numpy.__version__} working')
    import cv2 
    print(f'✅ OpenCV {cv2.__version__} working')
    import main
    print('✅ BathyImager main module loads')
except Exception as e:
    print(f'⚠️  Issue: {e}')
"
    deactivate 2>/dev/null || true
else
    echo "System Python test:"
    python3 -c "
import sys
sys.path.append('src')
try:
    import numpy
    print(f'✅ Numpy {numpy.__version__} working')
    import cv2
    print(f'✅ OpenCV {cv2.__version__} working') 
    import main
    print('✅ BathyImager main module loads')
except Exception as e:
    print(f'⚠️  Issue: {e}')
"
fi

echo ""
echo "🔧 Next steps:"
echo "   • The emergency fix should have broken the infinite loop"
echo "   • Run: ./update to get the improved update script"  
echo "   • Or run: sudo systemctl start bathyimager to start the service"
echo "   • Check logs: sudo journalctl -u bathyimager -f"
echo ""
echo "💡 What this fixed:"
echo "   • Killed hanging pip processes causing the infinite loop"
echo "   • Cleared corrupted pip cache"
echo "   • Installed numpy from piwheels (pre-compiled for ARM)"
echo "   • Avoided the source compilation that was hanging"