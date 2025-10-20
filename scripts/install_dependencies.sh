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

# Install system packages first (preferred method)
print_status "Installing system packages via apt..."
apt_packages=(
    "python3-serial"      # pyserial
    "python3-pil"         # Pillow
    "python3-opencv"      # opencv-python
    "python3-numpy"       # numpy  
    "python3-psutil"      # psutil
    "python3-rpi.gpio"    # RPi.GPIO
    "python3-gpiozero"    # gpiozero
    "python3-pip"         # pip
    "python3-setuptools"  # setuptools
    "python3-wheel"       # wheel
)

# Update package list
sudo apt update

for package in "${apt_packages[@]}"; do
    print_status "Installing $package..."
    if sudo apt install -y "$package"; then
        print_success "$package installed via apt"
    else
        print_warning "$package not available via apt"
    fi
done

# Install packages not available via apt using pip with --break-system-packages
print_status "Installing remaining packages via pip..."

pip_packages=(
    "pynmea2"
    "piexif"
)

for package in "${pip_packages[@]}"; do
    print_status "Installing $package via pip..."
    if [ "$USING_VENV" = true ]; then
        pip install "$package"
    else
        python3 -m pip install "$package" --break-system-packages
    fi
    print_success "$package installed"
done

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