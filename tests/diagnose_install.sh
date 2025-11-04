#!/bin/bash
#
# BathyCat Seabed Imager - Installation Diagnostics
# =================================================
# 
# Diagnoses common installation issues, especially numpy compilation problems.
#
# Usage: 
#   ./scripts/diagnose_install.sh
#
# Author: Mike Bollinger
# Date: November 2025

echo "🔍 BathyImager Installation Diagnostics"
echo "======================================="

echo ""
echo "📋 System Information:"
echo "----------------------"
echo "OS: $(uname -a)"
echo "Architecture: $(uname -m)"
echo "Python version: $(python3 --version 2>/dev/null || echo 'Python3 not found')"
echo "Pip version: $(pip3 --version 2>/dev/null || echo 'Pip3 not found')"

echo ""
echo "💾 Memory Information:"
echo "---------------------"
free -h 2>/dev/null || echo "Memory info not available"

echo ""
echo "📦 Current Python Packages:"
echo "---------------------------"
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "Virtual environment packages:"
    source venv/bin/activate 2>/dev/null && venv/bin/pip list | grep -E "(numpy|opencv|pillow)" 2>/dev/null || echo "No relevant packages found"
    deactivate 2>/dev/null || true
else
    echo "System Python packages:"
    pip3 list --user 2>/dev/null | grep -E "(numpy|opencv|pillow)" || echo "No relevant packages found"
fi

echo ""
echo "🔧 Build Dependencies:"
echo "---------------------"
echo -n "GCC: "
gcc --version 2>/dev/null | head -1 || echo "Not installed"
echo -n "Make: "
make --version 2>/dev/null | head -1 || echo "Not installed"  
echo -n "Python dev headers: "
find /usr/include -name "Python.h" 2>/dev/null | head -1 || echo "Not found"

echo ""
echo "📡 Network Connectivity:"
echo "-----------------------"
echo -n "PyPI: "
curl -s --max-time 5 https://pypi.org >/dev/null 2>&1 && echo "✅ Reachable" || echo "❌ Not reachable"
echo -n "Piwheels: "
curl -s --max-time 5 https://www.piwheels.org >/dev/null 2>&1 && echo "✅ Reachable" || echo "❌ Not reachable"

echo ""
echo "🐍 Python Environment:"
echo "---------------------"
if [ -d "venv" ]; then
    echo "Virtual environment: ✅ Present"
    if [ -f "venv/bin/activate" ]; then
        echo "Activation script: ✅ Present"
        if source venv/bin/activate 2>/dev/null; then
            echo "Activation test: ✅ Working"
            echo "Venv Python: $(which python)"
            echo "Venv Pip: $(which pip)"
            deactivate 2>/dev/null || true
        else
            echo "Activation test: ❌ Failed"
        fi
    else
        echo "Activation script: ❌ Missing"
    fi
else
    echo "Virtual environment: ❌ Not found"
fi

echo ""
echo "🔍 Common Issues Check:"
echo "----------------------"

# Check for low memory
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}' 2>/dev/null || echo "0")
if [ "$TOTAL_MEM" -lt 1000 ]; then
    echo "⚠️  Low memory detected (${TOTAL_MEM}MB). Numpy compilation may fail."
    echo "   Solution: Use pre-compiled wheels from piwheels"
fi

# Check for missing build dependencies
if ! command -v gcc >/dev/null 2>&1; then
    echo "⚠️  GCC compiler not found. Source installations will fail."
    echo "   Solution: sudo apt install build-essential"
fi

# Check for Python dev headers
if ! find /usr/include -name "Python.h" 2>/dev/null | head -1 >/dev/null; then
    echo "⚠️  Python development headers not found."
    echo "   Solution: sudo apt install python3-dev"
fi

# Check pip configuration
if [ -f ~/.pip/pip.conf ]; then
    echo "📝 Pip configuration found: ~/.pip/pip.conf"
    grep -E "(index|extra-index)" ~/.pip/pip.conf 2>/dev/null || echo "   No custom indexes configured"
else
    echo "📝 No custom pip configuration found"
fi

echo ""
echo "💡 Recommendations:"
echo "-------------------"
if [ "$(uname -m)" = "armv7l" ] || [ "$(uname -m)" = "aarch64" ]; then
    echo "• Raspberry Pi detected - use piwheels for faster installs:"
    echo "  pip install numpy --index-url https://www.piwheels.org/simple"
    echo "• Run the numpy fix script: ./scripts/fix_numpy_install.sh"
fi

if [ "$TOTAL_MEM" -lt 1000 ]; then
    echo "• Low memory system - avoid source compilation:"
    echo "  pip install --prefer-binary --only-binary=numpy,opencv-python"
fi

echo "• For hanging installations, use the enhanced update script: ./update"
echo "• Manual recovery: ./scripts/fix_numpy_install.sh --auto"

echo ""
echo "✅ Diagnostics complete!"