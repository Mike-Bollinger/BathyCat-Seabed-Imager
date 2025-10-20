#!/bin/bash
#
# BathyImager Dependency Installer
# ===============================
#
# Installs missing Python dependencies for BathyImager
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔧 BathyImager Dependency Installer"
echo "==================================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Please run this from the BathyCat-Seabed-Imager directory"
    exit 1
fi

# Check for virtual environment
if [ -d "venv" ]; then
    print_status "Activating virtual environment..."
    source venv/bin/activate
    USING_VENV=true
else
    print_status "No virtual environment found - using system Python"
    USING_VENV=false
fi

# Update pip first
print_status "Updating pip..."
if [ "$USING_VENV" = true ]; then
    pip install --upgrade pip
else
    python3 -m pip install --upgrade pip --user
fi

# Install missing packages
print_status "Installing missing Python packages..."

packages=(
    "pyserial"
    "pynmea2" 
    "Pillow"
    "piexif"
    "opencv-python"
    "numpy"
    "psutil"
)

for package in "${packages[@]}"; do
    print_status "Installing $package..."
    if [ "$USING_VENV" = true ]; then
        pip install "$package"
    else
        python3 -m pip install "$package" --user --break-system-packages 2>/dev/null || \
        python3 -m pip install "$package" --user
    fi
    print_success "$package installed"
done

# Try to install RPi.GPIO (may fail on non-Pi systems)
print_status "Installing Raspberry Pi packages..."
if [ "$USING_VENV" = true ]; then
    pip install RPi.GPIO || pip install gpiozero
else
    python3 -m pip install RPi.GPIO --user --break-system-packages 2>/dev/null || \
    python3 -m pip install gpiozero --user --break-system-packages 2>/dev/null || \
    echo "GPIO packages installation failed (normal on non-Pi systems)"
fi

# Test imports
print_status "Testing package imports..."
python3 << 'EOF'
import sys
success = True

packages = [
    'serial', 'pynmea2', 'PIL', 'piexif', 'cv2', 'numpy', 'psutil'
]

for pkg in packages:
    try:
        __import__(pkg)
        print(f"  ✓ {pkg}")
    except ImportError as e:
        print(f"  ✗ {pkg}: {e}")
        success = False

# Test GPIO
try:
    import RPi.GPIO
    print("  ✓ RPi.GPIO")
except ImportError:
    try:
        import gpiozero
        print("  ✓ gpiozero (RPi.GPIO alternative)")
    except ImportError:
        print("  ✗ No GPIO library (install RPi.GPIO or gpiozero)")

if success:
    print("\n✅ All core dependencies available!")
else:
    print("\n❌ Some dependencies missing")
    sys.exit(1)
EOF

if [ "$USING_VENV" = true ]; then
    deactivate
fi

print_success "Dependency installation complete!"
echo
echo "Next steps:"
echo "1. Test hardware: ./scripts/hardware_diagnostics.sh"
echo "2. Test application: ./run_bathyimager.sh"
echo "3. Check service: sudo systemctl status bathyimager"