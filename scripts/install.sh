#!/bin/bash
#
# BathyImager Seabed Imager Installation Script
# =============================================
#
# This script installs the BathyImager system on a Raspberry Pi with all
# dependencies, system services, and configuration.
#
# Usage: sudo ./install.sh [options]
#
# Options:
#   --dev      Install in development mode
#   --update   Update existing installation
#   --help     Show this help message
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation configuration
INSTALL_USER="pi"
INSTALL_DIR="/opt/bathyimager"
CONFIG_DIR="/etc/bathyimager"
LOG_DIR="/var/log/bathyimager"
SERVICE_NAME="bathyimager"
PYTHON_ENV="$INSTALL_DIR/venv"

# Flags
DEV_MODE=false
UPDATE_MODE=false
VERBOSE=false

# Function to print colored output
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

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to show help
show_help() {
    cat << EOF
BathyImager Seabed Imager Installation Script

Usage: sudo $0 [options]

Options:
    --dev       Install in development mode (editable install)
    --update    Update existing installation
    --verbose   Enable verbose output
    --help      Show this help message

This script will:
1. Update system packages
2. Install Python dependencies
3. Install BathyImager software
4. Configure system services
5. Set up directories and permissions
6. Enable and start the BathyImager imaging service

Requirements:
- Raspberry Pi OS (Bullseye or later)
- Internet connection for package downloads
- USB camera and GPS device (for operation)

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                DEV_MODE=true
                shift
                ;;
            --update)
                UPDATE_MODE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                set -x
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Function to detect Raspberry Pi
detect_raspberry_pi() {
    print_status "Detecting hardware platform..."
    
    if [[ ! -f /proc/cpuinfo ]]; then
        print_error "Cannot read /proc/cpuinfo"
        return 1
    fi
    
    if grep -q "Raspberry Pi" /proc/cpuinfo; then
        PI_MODEL=$(grep "Model" /proc/cpuinfo | cut -d: -f2 | xargs)
        print_success "Detected: $PI_MODEL"
        return 0
    else
        print_warning "Not running on Raspberry Pi - some features may not work"
        return 0
    fi
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    
    # Update package lists
    apt-get update -y
    
    # Upgrade existing packages
    apt-get upgrade -y
    
    print_success "System packages updated"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    # Core system packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        cmake \
        pkg-config \
        git \
        curl \
        wget \
        unzip
    
    # OpenCV dependencies
    apt-get install -y \
        libopencv-dev \
        python3-opencv \
        libopenblas-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev
    
    # GPIO and hardware support (skip if packages not available)
    if apt-cache show python3-rpi.gpio >/dev/null 2>&1; then
        apt-get install -y python3-rpi.gpio
        print_success "python3-rpi.gpio installed from system packages"
    else
        print_warning "python3-rpi.gpio not available from apt - will install via pip"
    fi
    
    # Try different kernel header packages for newer systems
    if apt-cache show raspberrypi-kernel-headers >/dev/null 2>&1; then
        apt-get install -y raspberrypi-kernel-headers
        print_success "raspberrypi-kernel-headers installed"
    elif apt-cache show linux-headers-rpi >/dev/null 2>&1; then
        apt-get install -y linux-headers-rpi
        print_success "linux-headers-rpi installed"
    elif apt-cache show linux-headers-$(uname -r) >/dev/null 2>&1; then
        apt-get install -y linux-headers-$(uname -r)
        print_success "linux-headers-$(uname -r) installed"
    else
        print_warning "No kernel headers package available - some GPIO functionality may be limited"
    fi
    
    apt-get install -y i2c-tools
    
    # Serial/USB support
    apt-get install -y \
        minicom \
        setserial \
        usbutils
    
    # System utilities
    apt-get install -y \
        systemd \
        rsyslog \
        logrotate \
        htop \
        tree
    
    print_success "System dependencies installed"
}

# Function to create system user and directories
setup_directories() {
    print_status "Setting up directories and user..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Create configuration directory
    mkdir -p "$CONFIG_DIR"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Create user if doesn't exist
    if ! id "$INSTALL_USER" &>/dev/null; then
        useradd -r -d "$INSTALL_DIR" -s /bin/bash "$INSTALL_USER"
        print_status "Created user: $INSTALL_USER"
    fi
    
    # Add user to necessary groups
    usermod -a -G dialout,gpio,i2c,spi "$INSTALL_USER"
    
    # Set ownership
    chown -R "$INSTALL_USER:$INSTALL_USER" "$INSTALL_DIR"
    chown -R "$INSTALL_USER:$INSTALL_USER" "$LOG_DIR"
    
    print_success "Directories and user configured"
}

# Function to create Python virtual environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment
    sudo -u "$INSTALL_USER" python3 -m venv "$PYTHON_ENV"
    
    # Upgrade pip
    sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install --upgrade pip setuptools wheel
    
    print_success "Python virtual environment created"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Core dependencies
    sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install \
        opencv-python \
        numpy \
        pillow \
        piexif \
        pynmea2 \
        pyserial \
        psutil
    
    # Try to install RPi.GPIO (may need different approach on newer OS)
    if ! sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install RPi.GPIO; then
        print_warning "RPi.GPIO installation failed - trying alternative gpiozero"
        sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install gpiozero
    fi
    
    # Development dependencies (if dev mode)
    if [[ "$DEV_MODE" == true ]]; then
        sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install \
            pytest \
            pytest-cov \
            black \
            flake8 \
            mypy \
            pre-commit
    fi
    
    print_success "Python dependencies installed"
}

# Function to install BathyImager software
install_bathyimager() {
    print_status "Installing BathyImager software..."
    
    # Copy source code
    if [[ "$DEV_MODE" == true ]]; then
        # Development mode - create symlink
        if [[ -d "$(pwd)/src" ]]; then
            ln -sfn "$(pwd)/src" "$INSTALL_DIR/src"
            chown -h "$INSTALL_USER:$INSTALL_USER" "$INSTALL_DIR/src"
        else
            print_error "Source directory not found. Run from BathyImager project root."
            exit 1
        fi
    else
        # Production mode - copy files
        if [[ -d "src" ]]; then
            cp -r src "$INSTALL_DIR/"
            chown -R "$INSTALL_USER:$INSTALL_USER" "$INSTALL_DIR"
        else
            print_error "Source directory not found. Run from BathyImager project root."
            exit 1
        fi
    fi
    
    # Make main script executable
    chmod +x "$INSTALL_DIR/src/main.py"
    
    print_success "BathyImager software installed"
}

# Function to install configuration
install_configuration() {
    print_status "Installing configuration..."
    
    # Copy configuration file
    if [[ -f "config/bathyimager_config.json" ]]; then
        cp "config/bathyimager_config.json" "$CONFIG_DIR/config.json"
        
        # Update paths in config for production
        if [[ "$DEV_MODE" == false ]]; then
            sed -i 's|"/var/log/bathyimager/bathyimager.log"|"/var/log/bathyimager/bathyimager.log"|g' "$CONFIG_DIR/config.json"
            sed -i 's|"/media/usb-storage/bathyimager"|"/media/usb-storage/bathyimager"|g' "$CONFIG_DIR/config.json"
        fi
        
        chown "$INSTALL_USER:$INSTALL_USER" "$CONFIG_DIR/config.json"
        chmod 644 "$CONFIG_DIR/config.json"
    else
        print_warning "Configuration file not found, creating default..."
        create_default_config
    fi
    
    print_success "Configuration installed"
}

# Function to create default configuration
create_default_config() {
    cat > "$CONFIG_DIR/config.json" << EOF
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
  
  "storage_base_path": "/media/usb-storage/bathyimager",
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
  "log_file_path": "/var/log/bathyimager/bathyimager.log",
  "log_max_size_mb": 100,
  "log_backup_count": 5,
  
  "auto_start": true,
  "watchdog_enabled": true,
  "status_report_interval": 30
}
EOF
    chown "$INSTALL_USER:$INSTALL_USER" "$CONFIG_DIR/config.json"
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=BathyImager Seabed Imager
Documentation=https://github.com/Mike-Bollinger/BathyImager-Seabed-Imager
After=network.target multi-user.target
Wants=network.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$PYTHON_ENV/bin/python -m main --config $CONFIG_DIR/config.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bathyimager

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$LOG_DIR /media
DeviceAllow=/dev/video* rw
DeviceAllow=/dev/ttyUSB* rw
DeviceAllow=/dev/ttyACM* rw

# Resource limits
MemoryLimit=512M
CPUQuota=50%

# Watchdog
WatchdogSec=60

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    print_success "Systemd service created"
}

# Function to configure log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/bathyimager" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $INSTALL_USER $INSTALL_USER
    postrotate
        systemctl reload-or-restart $SERVICE_NAME
    endscript
}
EOF
    
    print_success "Log rotation configured"
}

# Function to configure USB storage auto-mount
setup_usb_automount() {
    print_status "Setting up USB storage auto-mount..."
    
    # Create mount point
    mkdir -p /media/usb-storage
    
    # Add to fstab for auto-mount (optional)
    if ! grep -q "usb-storage" /etc/fstab; then
        echo "# BathyImager USB Storage" >> /etc/fstab
        echo "# LABEL=BATHYIMAGER /media/usb-storage auto defaults,user,noauto 0 0" >> /etc/fstab
    fi
    
    # Create udev rule for auto-mount
    cat > "/etc/udev/rules.d/99-bathyimager-storage.rules" << EOF
# BathyImager USB Storage Auto-mount
SUBSYSTEM=="block", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", \
ACTION=="add", KERNEL=="sd[a-z][0-9]", \
RUN+="/bin/mkdir -p /media/usb-storage", \
RUN+="/bin/mount -o defaults,uid=$INSTALL_USER,gid=$INSTALL_USER %N /media/usb-storage"

SUBSYSTEM=="block", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", \
ACTION=="remove", KERNEL=="sd[a-z][0-9]", \
RUN+="/bin/umount /media/usb-storage"
EOF
    
    # Reload udev rules
    udevadm control --reload-rules
    
    print_success "USB auto-mount configured"
}

# Function to run tests
run_tests() {
    print_status "Running system tests..."
    
    # Test Python environment
    if ! sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/python" -c "import sys; sys.path.append('$INSTALL_DIR/src'); import main; print('BathyImager import successful')"; then
        print_error "Python import test failed"
        return 1
    fi
    
    # Test configuration
    if ! sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/python" -c "import sys; sys.path.append('$INSTALL_DIR/src'); from main import BathyImagerService; print('Configuration test passed')"; then
        print_warning "Configuration test failed - check hardware connections"
    fi
    
    print_success "System tests completed"
}

# Function to enable and start service
enable_service() {
    print_status "Enabling and starting BathyImager imaging service..."
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    # Start service
    systemctl start "$SERVICE_NAME"
    
    # Check status
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "BathyImager imaging service is running"
    else
        print_warning "BathyImager imaging service failed to start - check logs with: journalctl -u $SERVICE_NAME"
    fi
}

# Function to show installation summary
show_summary() {
    print_success "BathyImager installation completed!"
    
    echo
    echo "Installation Summary:"
    echo "===================="
    echo "Install Directory: $INSTALL_DIR"
    echo "Configuration:     $CONFIG_DIR/config.json"
    echo "Log Directory:     $LOG_DIR"
    echo "Service Name:      $SERVICE_NAME"
    echo "Python Environment: $PYTHON_ENV"
    echo
    echo "Useful Commands:"
    echo "==============="
    echo "Check service status:    systemctl status $SERVICE_NAME"
    echo "View logs:              journalctl -u $SERVICE_NAME -f"
    echo "Restart service:        sudo systemctl restart $SERVICE_NAME"
    echo "Stop service:           sudo systemctl stop $SERVICE_NAME"
    echo "Edit configuration:     sudo nano $CONFIG_DIR/config.json"
    echo
    echo "Next Steps:"
    echo "==========="
    echo "1. Connect USB camera and GPS device"
    echo "2. Insert USB storage device"
    echo "3. Check service logs for any errors"
    echo "4. Test image capture functionality"
    echo
    
    if [[ "$DEV_MODE" == true ]]; then
        print_warning "Development mode enabled - changes to source code will take effect immediately"
    fi
}

# Main installation function
main() {
    echo "BathyImager Seabed Imager Installation Script"
    echo "=============================================="
    echo
    
    parse_args "$@"
    check_root
    
    if [[ "$UPDATE_MODE" == true ]]; then
        print_status "Running in update mode"
        # Stop service during update
        systemctl stop "$SERVICE_NAME" || true
    fi
    
    detect_raspberry_pi
    update_system
    install_system_dependencies
    setup_directories
    setup_python_environment
    install_python_dependencies
    install_bathyimager
    install_configuration
    create_systemd_service
    setup_log_rotation
    setup_usb_automount
    
    if [[ "$UPDATE_MODE" == false ]]; then
        run_tests
    fi
    
    enable_service
    show_summary
    
    print_success "Installation complete!"
}

# Run main function with all arguments
main "$@"