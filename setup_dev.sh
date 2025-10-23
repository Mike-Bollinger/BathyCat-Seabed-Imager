#!/bin/bash#!/bin/bash

##

# Development Environment Setup for BathyCat Seabed Imager# BathyImager Development Setup Script

# ========================================================# ====================================

# #

# Simple wrapper script that calls the device permissions setup# Quick setup for development environment in home directory

# and provides development environment configuration#

#

# Author: Mike Bollingerset -e

# Date: October 2025

# Colors for output

set -e  # Exit on any errorRED='\033[0;31m'

GREEN='\033[0;32m'

echo "🛠️  BathyImager Development Environment Setup"YELLOW='\033[1;33m'

echo "============================================="BLUE='\033[0;34m'

NC='\033[0m'

# Check if we're running as root (needed for device permissions)

if [ "$EUID" -ne 0 ]; thenprint_status() {

    echo "❌ This script needs to be run as root for device permissions"    echo -e "${BLUE}[INFO]${NC} $1"

    echo "   Please run: sudo ./setup_dev.sh"}

    exit 1

fiprint_success() {

    echo -e "${GREEN}[SUCCESS]${NC} $1"

# Run the device permissions setup}

echo "🔧 Setting up device permissions..."

if [ -f "scripts/setup_device_permissions.sh" ]; thenprint_warning() {

    bash scripts/setup_device_permissions.sh    echo -e "${YELLOW}[WARNING]${NC} $1"

    echo "✅ Device permissions configured"}

else

    echo "❌ Device permissions script not found"print_error() {

    echo "   Looking for: scripts/setup_device_permissions.sh"    echo -e "${RED}[ERROR]${NC} $1"

    exit 1}

fi

echo "🚀 BathyImager Development Setup"

# Create directories if they don't existecho "================================"

echo "📁 Creating necessary directories..."

mkdir -p /var/log/bathyimager# Check if we're in the project directory

chown bathyimager:bathyimager /var/log/bathyimager 2>/dev/null || echo "   Note: bathyimager user not found"if [ ! -f "src/bathycat_imager.py" ]; then

mkdir -p /media/usb    print_error "Please run this script from the BathyCat-Seabed-Imager directory"

echo "✅ Directories created"    exit 1

fi

# Set up udev rules for consistent device naming

echo "⚙️  Setting up udev rules..."PROJECT_DIR="$(pwd)"

UDEV_RULES_FILE="/etc/udev/rules.d/99-bathyimager.rules"print_status "Setting up development environment in: $PROJECT_DIR"



cat > "$UDEV_RULES_FILE" << 'EOF'# Create Python virtual environment if it doesn't exist

# BathyImager udev rules for consistent device permissionsif [ ! -d "venv" ]; then

# USB cameras    print_status "Creating Python virtual environment..."

SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"    python3 -m venv venv

# GPS devices (USB serial)    print_success "Virtual environment created"

SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", GROUP="dialout", MODE="0664"else

SUBSYSTEM=="tty", ATTRS{serial}=="*GPS*", GROUP="dialout", MODE="0664"    print_status "Virtual environment already exists"

# All USB serial devices for GPS fallbackfi

KERNEL=="ttyUSB*", GROUP="dialout", MODE="0664"

KERNEL=="ttyACM*", GROUP="dialout", MODE="0664"# Activate virtual environment and install dependencies

# GPIO accessprint_status "Installing Python dependencies..."

SUBSYSTEM=="gpio", GROUP="gpio", MODE="0664"source venv/bin/activate

KERNEL=="gpiomem", GROUP="gpio", MODE="0664"pip install --upgrade pip setuptools wheel

EOF

# Install core dependencies

echo "✅ udev rules installed"pip install \

    opencv-python \

# Reload udev rules    numpy \

echo "🔄 Reloading udev rules..."    pillow \

udevadm control --reload-rules    piexif \

udevadm trigger    pynmea2 \

echo "✅ udev rules reloaded"    pyserial \

    psutil

echo ""

echo "✨ Development environment setup complete!"# Try to install RPi.GPIO (may fail on non-Pi systems)

echo ""if ! pip install RPi.GPIO; then

echo "📋 Next steps:"    print_warning "RPi.GPIO installation failed - installing gpiozero as alternative"

echo "   1. Reboot to ensure all permissions take effect"    pip install gpiozero

echo "   2. Connect your camera and GPS devices"fi

echo "   3. Run hardware diagnostics: ./scripts/hardware_diagnostics.sh all"

echo "   4. Test the system: python3 src/main.py --config config/bathyimager_config.json"# Install development dependencies

echo ""pip install \

echo "🔍 Troubleshooting:"    pytest \

echo "   • Check device detection: ls -la /dev/video* /dev/ttyUSB*"    pytest-cov \

echo "   • Verify permissions: ./scripts/hardware_diagnostics.sh permissions"    black \

echo "   • View logs: tail -f /var/log/bathyimager/bathyimager.log"    flake8 \
    mypy

print_success "Dependencies installed"

# Create run script for easy execution
cat > run_bathyimager.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/src"
exec ../venv/bin/python main.py --config ../config/bathyimager_config.json "$@"
EOF

chmod +x run_bathyimager.sh
print_success "Run script created: ./run_bathyimager.sh"

# Create configuration file if it doesn't exist
if [ ! -f "config/bathyimager_config.json" ]; then
    print_status "Creating default configuration..."
    mkdir -p config
    
    cat > config/bathyimager_config.json << 'EOF'
{
  "capture_fps": 4.0,
  "require_gps_fix": false,
  "gps_fix_timeout": 300.0,
  
  "camera_device_id": 0,
  "camera_width": 1920,
  "camera_height": 1080,
  "camera_fps": 30,
  "camera_format": "MJPG",
  "camera_auto_exposure": true,
  "camera_auto_white_balance": true,
  "camera_contrast": 50,
  "camera_saturation": 60,
  "camera_exposure": -6,
  "camera_white_balance": 4000,
  
  "gps_port": "/dev/ttyUSB0",
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true,
  
  "image_format": "JPEG",
  "jpeg_quality": 85,
  "enable_metadata": true,
  "enable_preview": false,
  "preview_width": 320,
  
  "storage_base_path": "./captured_images",
  "min_free_space_gb": 5.0,
  "auto_cleanup_enabled": true,
  "cleanup_threshold_gb": 10.0,
  "days_to_keep": 30,
  
  "led_power_pin": 18,
  "led_gps_pin": 23,
  "led_camera_pin": 24,
  "led_error_pin": 25,
  
  "log_level": "INFO",
  "log_to_file": true,
  "log_file_path": "./logs/bathyimager.log",
  "log_max_size_mb": 100,
  "log_backup_count": 5,
  
  "auto_start": true,
  "watchdog_enabled": true,
  "status_report_interval": 30
}
EOF
    
    print_success "Configuration created: config/bathyimager_config.json"
else
    print_status "Configuration file already exists"
fi

# Create directories for development
mkdir -p logs
mkdir -p captured_images

print_success "Development setup complete!"

echo
echo "Development Environment Ready:"
echo "============================="
echo "Project Directory: $PROJECT_DIR"
echo "Python Environment: $PROJECT_DIR/venv"
echo "Configuration: $PROJECT_DIR/config/bathyimager_config.json"
echo "Run Script: $PROJECT_DIR/run_bathyimager.sh"
echo
echo "Development Commands:"
echo "===================="
echo "Activate Python env:  source venv/bin/activate"
echo "Run application:      ./run_bathyimager.sh"
echo "Run in src directory: cd src && python main.py --config ../config/bathyimager_config.json"
echo "Run tests:           source venv/bin/activate && python -m pytest tests/"
echo "Update from git:     git pull"
echo
echo "For system service installation, run: sudo ./scripts/install.sh"