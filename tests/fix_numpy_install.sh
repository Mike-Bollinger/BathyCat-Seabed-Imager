#!/bin/bash
#
# BathyCat Seabed Imager - Numpy Installation Fix
# ===============================================
# 
# Fixes common numpy installation issues on Raspberry Pi by using
# pre-compiled wheels from piwheels instead of compiling from source.
#
# Usage: 
#   ./scripts/fix_numpy_install.sh
#
# Author: Mike Bollinger  
# Date: November 2025

set -e

echo "🔧 BathyImager Numpy Installation Fix"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Not in BathyImager project directory"
    echo "   Please run this script from the project root"
    exit 1
fi

# Function to fix numpy in virtual environment
fix_venv_numpy() {
    echo "🐍 Fixing numpy in virtual environment..."
    
    if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
        echo "❌ Virtual environment not found or corrupted"
        echo "   Run: sudo ./scripts/install.sh --update to recreate"
        return 1
    fi
    
    if ! source venv/bin/activate 2>/dev/null; then
        echo "❌ Could not activate virtual environment"
        return 1
    fi
    
    echo "   Upgrading pip tools..."
    venv/bin/pip install --upgrade pip setuptools wheel --no-cache-dir
    
    echo "   Removing existing numpy (if any)..."
    venv/bin/pip uninstall numpy -y 2>/dev/null || true
    
    echo "   Installing numpy from piwheels (pre-compiled)..."
    if venv/bin/pip install numpy \
        --index-url https://www.piwheels.org/simple \
        --extra-index-url https://pypi.org/simple \
        --no-cache-dir; then
        echo "   ✅ Numpy installed successfully from piwheels"
    else
        echo "   ⚠️  Piwheels failed, trying PyPI with binary preference..."
        if venv/bin/pip install numpy --prefer-binary --no-cache-dir; then
            echo "   ✅ Numpy installed from PyPI (binary)"
        else
            echo "   ❌ Failed to install numpy"
            deactivate 2>/dev/null || true
            return 1
        fi
    fi
    
    echo "   Testing numpy installation..."
    if venv/bin/python -c "import numpy; print(f'✅ Numpy {numpy.__version__} working')"; then
        echo "   ✅ Numpy test passed"
    else
        echo "   ❌ Numpy test failed"
        deactivate 2>/dev/null || true
        return 1
    fi
    
    deactivate 2>/dev/null || true
    return 0
}

# Function to fix numpy in system Python
fix_system_numpy() {
    echo "🐍 Fixing numpy in system Python..."
    
    echo "   Upgrading pip tools..."
    pip3 install --upgrade pip setuptools wheel --user --no-cache-dir
    
    echo "   Removing existing numpy (if any)..."
    pip3 uninstall numpy -y 2>/dev/null || true
    
    echo "   Installing numpy from piwheels (pre-compiled)..."
    if pip3 install numpy --user \
        --index-url https://www.piwheels.org/simple \
        --extra-index-url https://pypi.org/simple \
        --no-cache-dir; then
        echo "   ✅ Numpy installed successfully from piwheels"
    else
        echo "   ⚠️  Piwheels failed, trying PyPI with binary preference..."
        if pip3 install numpy --user --prefer-binary --no-cache-dir; then
            echo "   ✅ Numpy installed from PyPI (binary)"
        elif pip3 install numpy --user --prefer-binary --no-cache-dir --break-system-packages; then
            echo "   ✅ Numpy installed from PyPI (with system override)"
        else
            echo "   ❌ Failed to install numpy"
            return 1
        fi
    fi
    
    echo "   Testing numpy installation..."
    if python3 -c "import numpy; print(f'✅ Numpy {numpy.__version__} working')"; then
        echo "   ✅ Numpy test passed"
    else
        echo "   ❌ Numpy test failed"
        return 1
    fi
    
    return 0
}

# Main execution
echo "📋 Numpy Installation Options:"
echo "1. 🐍 Fix numpy in virtual environment (recommended if you have venv)"
echo "2. 🐍 Fix numpy in system Python"
echo "3. 🔄 Try both (venv first, then system)"
echo ""

if [ "$1" = "--auto" ]; then
    # Auto mode - try both
    choice=3
else
    read -p "Choose option (1-3): " choice
fi

case $choice in
    1)
        fix_venv_numpy
        ;;
    2)
        fix_system_numpy
        ;;
    3)
        echo "🔄 Trying virtual environment first..."
        if fix_venv_numpy; then
            echo "✅ Virtual environment numpy fixed"
        else
            echo "⚠️  Virtual environment failed, trying system Python..."
            fix_system_numpy
        fi
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✨ Numpy fix complete!"
echo ""
echo "🧪 Next steps:"
echo "   • Test with: python3 -c \"import numpy; print('Numpy version:', numpy.__version__)\""
echo "   • Run update: ./update"
echo "   • Or install all deps: source venv/bin/activate && pip install -r requirements.txt"
echo ""
echo "💡 What this fixed:"
echo "   • Used pre-compiled wheels instead of compiling from source"
echo "   • Added piwheels repository (optimized for Raspberry Pi)"
echo "   • Avoided the 'preparing metadata' hang during compilation"