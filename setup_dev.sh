#!/bin/bash
#
# BathyImager Development Setup Script
# ====================================
#
# Quick setup for development environment in home directory
#

set -e

# Colors for output
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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🚀 BathyImager Development Setup"
echo "================================"

# Check if we're in the project directory
if [ ! -f "src/bathycat_imager.py" ]; then
    print_error "Please run this script from the BathyCat-Seabed-Imager directory"
    exit 1
fi

PROJECT_DIR="$(pwd)"
print_status "Setting up development environment in: $PROJECT_DIR"

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install core dependencies
pip install \
    opencv-python \
    numpy \
    pillow \
    piexif \
    pynmea2 \
    pyserial \
    psutil

# Try to install RPi.GPIO (may fail on non-Pi systems)
if ! pip install RPi.GPIO; then
    print_warning "RPi.GPIO installation failed - installing gpiozero as alternative"
    pip install gpiozero
fi

# Install development dependencies
pip install \
    pytest \
    pytest-cov \
    black \
    flake8 \
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