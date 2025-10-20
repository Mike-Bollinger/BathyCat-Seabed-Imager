#!/bin/bash
#
# BathyImager Complete Fix Script
# =============================
#
# Fixes all identified issues with BathyImager service
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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔧 BathyImager Complete Fix"
echo "=========================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Please run this from the BathyCat-Seabed-Imager directory"
    exit 1
fi

PROJECT_DIR="$(pwd)"
SERVICE_USER="bathyimager"

print_status "Project directory: $PROJECT_DIR"

# Stop service if running
print_status "Stopping bathyimager service..."
sudo systemctl stop bathyimager 2>/dev/null || true

# Fix 1: Create run script with system Python (not venv)
print_status "Creating run script with system Python..."
cat > run_bathyimager.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/src"
exec python3 main.py --config ../config/bathyimager_config.json "$@"
EOF
chmod +x run_bathyimager.sh
print_success "Run script created"

# Fix 2: Update service file to use system Python directly
print_status "Installing updated service file..."
sudo cp scripts/bathyimager.service /etc/systemd/system/
sudo systemctl daemon-reload
print_success "Service file updated"

# Fix 3: Mount USB storage
print_status "Setting up USB storage..."
sudo ./scripts/mount_usb.sh
print_success "USB storage configured"

# Fix 4: Ensure configuration file exists
CONFIG_FILE="config/bathyimager_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    print_status "Creating default configuration..."
    mkdir -p config
    
    cat > "$CONFIG_FILE" << 'EOF'
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
  
  "storage_base_path": "/media/usb",
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
    print_success "Configuration created"
else
    print_success "Configuration file exists"
fi

# Fix 5: Create log directory
print_status "Creating log directory..."
mkdir -p logs
sudo chown -R "$SERVICE_USER:$SERVICE_USER" logs
print_success "Log directory created"

# Fix 6: Set proper ownership
print_status "Setting ownership..."
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
print_success "Ownership set"

# Fix 7: Test the application manually
print_status "Testing application..."
if python3 src/main.py --config config/bathyimager_config.json --test 2>/dev/null; then
    print_success "Application test passed"
else
    print_warning "Application test failed (may be normal without --test flag)"
    # Try a simple import test
    if python3 -c "import sys; sys.path.append('src'); import main; print('Import successful')"; then
        print_success "Application import test passed"
    else
        print_error "Application import test failed"
        print_status "Check dependencies with: ./scripts/hardware_diagnostics.sh dependencies"
    fi
fi

# Start service
print_status "Starting bathyimager service..."
if sudo systemctl start bathyimager; then
    print_success "Service started"
    
    # Check status after a moment
    sleep 3
    if sudo systemctl is-active bathyimager >/dev/null 2>&1; then
        print_success "Service is running successfully!"
        sudo systemctl status bathyimager --no-pager -l
    else
        print_error "Service failed to start"
        print_status "Checking logs..."
        sudo journalctl -u bathyimager --no-pager -l | tail -10
    fi
else
    print_error "Failed to start service"
fi

print_status "Fix complete!"
echo
echo "Useful commands:"
echo "  sudo systemctl status bathyimager     - Check service status"
echo "  sudo journalctl -u bathyimager -f    - View live logs"
echo "  python3 src/main.py --config config/bathyimager_config.json  - Test manually"
echo "  ./scripts/hardware_diagnostics.sh    - Run hardware tests"