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
INSTALL_USER="bathyimager"
PROJECT_DIR="/home/$INSTALL_USER/BathyCat-Seabed-Imager"
CONFIG_DIR="$PROJECT_DIR/config"
LOG_DIR="/var/log/bathyimager"
SERVICE_NAME="bathyimager"
PYTHON_ENV="$PROJECT_DIR/venv"

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
    
    # Time synchronization and GPS HAT support
    # Install basic GPS and timing tools first
    print_status "Installing GPS and timing tools..."
    apt-get install -y \
        tzdata \
        pps-tools \
        gpsd \
        gpsd-clients
    
    # Handle chrony installation separately to avoid conflicts
    print_status "Installing chrony for GPS PPS support..."
    if ! install_chrony_with_conflict_resolution; then
        print_warning "Chrony installation failed - GPS PPS timing may not be optimal"
        print_warning "You can manually install chrony later with: sudo apt install chrony"
    fi
    
    # System utilities
    apt-get install -y \
        systemd \
        rsyslog \
        logrotate \
        htop \
        tree
    
    print_success "System dependencies installed"
}

# Function to install chrony with conflict resolution
install_chrony_with_conflict_resolution() {
    print_status "Resolving time synchronization conflicts..."
    
    # Check if chrony is already installed
    if command -v chronyd &> /dev/null; then
        print_success "chrony is already installed"
        return 0
    fi
    
    # Stop conflicting time services
    local services_stopped=false
    
    if systemctl is-active --quiet systemd-timesyncd 2>/dev/null; then
        print_status "Stopping systemd-timesyncd to avoid conflicts"
        if systemctl stop systemd-timesyncd 2>/dev/null && systemctl disable systemd-timesyncd 2>/dev/null; then
            services_stopped=true
            print_success "systemd-timesyncd stopped and disabled"
        else
            print_warning "Failed to stop systemd-timesyncd"
        fi
    fi
    
    if systemctl is-active --quiet ntp 2>/dev/null; then
        print_status "Stopping ntp service to avoid conflicts"
        systemctl stop ntp 2>/dev/null || true
        systemctl disable ntp 2>/dev/null || true
    fi
    
    # Try to install chrony
    print_status "Installing chrony..."
    if apt-get install -y chrony 2>/dev/null; then
        print_success "chrony installed successfully"
        return 0
    else
        print_error "Failed to install chrony due to package conflicts"
        
        # Try to resolve conflicts by removing conflicting packages
        print_status "Attempting to resolve package conflicts..."
        if apt-get remove --purge -y systemd-timesyncd 2>/dev/null; then
            print_status "Removed systemd-timesyncd, retrying chrony installation..."
            if apt-get install -y chrony 2>/dev/null; then
                print_success "chrony installed after conflict resolution"
                return 0
            fi
        fi
        
        print_error "Could not resolve chrony installation conflicts"
        print_warning "GPS PPS timing will not be available without chrony"
        return 1
    fi
}

# Function to create system user and directories
setup_directories() {
    print_status "Setting up directories and user..."
    
    # Create bathyimager user if doesn't exist
    if ! id "$INSTALL_USER" &>/dev/null; then
        useradd -m -d "/home/$INSTALL_USER" -s /bin/bash "$INSTALL_USER"
        print_status "Created user: $INSTALL_USER"
    fi
    
    # Add user to necessary groups for hardware access
    usermod -a -G dialout,gpio,i2c,spi,video,audio,input "$INSTALL_USER"
    print_status "Added $INSTALL_USER to hardware access groups"
    
    # Create SD card log directory for performance optimization
    mkdir -p "$LOG_DIR"
    print_status "Created SD card log directory: $LOG_DIR"
    
    # Set up proper video device permissions
    if [ -d /dev ]; then
        # Ensure video devices are accessible
        if ls /dev/video* >/dev/null 2>&1; then
            chmod 666 /dev/video*
            print_status "Set video device permissions"
        fi
        
        # Ensure serial/USB devices are accessible  
        if ls /dev/ttyUSB* >/dev/null 2>&1; then
            chmod 666 /dev/ttyUSB*
            print_status "Set USB serial device permissions"
        fi
        
        if ls /dev/ttyACM* >/dev/null 2>&1; then
            chmod 666 /dev/ttyACM*
            print_status "Set ACM serial device permissions"
        fi
    fi
    
    # Ensure the project is in the user's home directory
    if [[ ! -d "$PROJECT_DIR" ]]; then
        print_status "Copying project to user home directory..."
        
        # Copy current project to user home
        sudo -u "$INSTALL_USER" cp -r "$(pwd)" "/home/$INSTALL_USER/"
        
        # Ensure correct ownership
        chown -R "$INSTALL_USER:$INSTALL_USER" "$PROJECT_DIR"
    fi
    
    # Set ownership for log directory
    chown -R "$INSTALL_USER:$INSTALL_USER" "$LOG_DIR"
    
    # Create media directory with proper permissions
    mkdir -p /media/usb
    chown "$INSTALL_USER:$INSTALL_USER" /media/usb
    chmod 755 /media/usb
    
    print_success "Directories and user configured"
}

# Function to create Python virtual environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    # Remove existing venv if it exists (for update mode)
    if [[ "$UPDATE_MODE" == true && -d "$PYTHON_ENV" ]]; then
        print_status "Removing existing virtual environment..."
        sudo rm -rf "$PYTHON_ENV"
    fi
    
    # Ensure python3-venv is available
    if ! python3 -m venv --help &>/dev/null; then
        print_status "Installing python3-venv package..."
        apt-get update
        apt-get install -y python3-venv
    fi
    
    # Create virtual environment with system site packages for better compatibility
    print_status "Creating virtual environment..."
    if ! sudo -u "$INSTALL_USER" python3 -m venv "$PYTHON_ENV" --system-site-packages; then
        print_error "Failed to create virtual environment"
        print_status "Trying without system-site-packages..."
        sudo -u "$INSTALL_USER" python3 -m venv "$PYTHON_ENV"
    fi
    
    # Upgrade pip with retry and timeout
    print_status "Upgrading pip in virtual environment..."
    if ! timeout 300 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install --upgrade pip setuptools wheel --no-cache-dir; then
        print_warning "Pip upgrade failed or timed out - continuing anyway"
    fi
    
    print_success "Python virtual environment created"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Use requirements.txt if it exists, otherwise install core dependencies manually
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        print_status "Installing from requirements.txt..."
        print_status "Note: Using pre-compiled wheels to avoid compilation issues..."
        
        # Upgrade pip tools first
        sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install --upgrade pip setuptools wheel --no-cache-dir >/dev/null 2>&1 || true
        
        # Try enhanced installation with piwheels and binary preference
        if timeout 600 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install -r "$PROJECT_DIR/requirements.txt" \
            --no-cache-dir \
            --prefer-binary \
            --only-binary=numpy,opencv-python,Pillow \
            --extra-index-url https://www.piwheels.org/simple; then
            print_success "Requirements installed successfully (using pre-compiled wheels)"
        elif print_warning "Primary method failed - trying piwheels numpy first..." && \
             timeout 300 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install numpy \
                 --no-cache-dir \
                 --index-url https://www.piwheels.org/simple \
                 --extra-index-url https://pypi.org/simple && \
             timeout 600 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install -r "$PROJECT_DIR/requirements.txt" \
                 --no-cache-dir --prefer-binary; then
            print_success "Requirements installed (numpy from piwheels)"
        else
            print_warning "Requirements.txt installation failed - trying individual packages"
            install_core_dependencies_manual
        fi
    else
        install_core_dependencies_manual
    fi
}

# Function to install core dependencies manually (fallback)
install_core_dependencies_manual() {
    print_status "Installing core dependencies manually..."
    
    # Install numpy first from piwheels to avoid compilation issues
    print_status "Installing numpy (using piwheels for ARM optimization)..."
    if ! timeout 300 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install numpy \
         --index-url https://www.piwheels.org/simple \
         --extra-index-url https://pypi.org/simple \
         --no-cache-dir; then
        print_warning "Piwheels numpy failed - trying standard PyPI with binary preference"
        if ! timeout 300 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install numpy --prefer-binary --no-cache-dir; then
            print_warning "Failed to install numpy - this may cause issues"
        fi
    fi
    
    # Core dependencies with timeout and error handling (excluding numpy since we already installed it)
    for package in opencv-python pillow piexif pynmea2 pyserial psutil; do
        print_status "Installing $package..."
        if ! timeout 180 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install "$package" --prefer-binary --no-cache-dir; then
            print_warning "Failed to install $package - continuing with next package"
        fi
    done
    
    # Try to install RPi.GPIO (may need different approach on newer OS)
    print_status "Installing GPIO libraries..."
    if ! timeout 120 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install RPi.GPIO --no-cache-dir; then
        print_warning "RPi.GPIO installation failed - trying alternative gpiozero"
        timeout 120 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install gpiozero --no-cache-dir || print_warning "GPIO library installation failed"
    fi
    
    # Development dependencies (if dev mode)
    if [[ "$DEV_MODE" == true ]]; then
        print_status "Installing development dependencies..."
        for dev_package in pytest pytest-cov black flake8 mypy pre-commit; do
            if ! timeout 120 sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/pip" install "$dev_package" --no-cache-dir; then
                print_warning "Failed to install $dev_package"
            fi
        done
    fi
    
    print_success "Python dependencies installed"
}

# Function to install BathyImager software
install_bathyimager() {
    print_status "Setting up BathyImager software..."
    
    # Ensure we're working from the correct directory
    if [[ "$(pwd)" != *"BathyCat-Seabed-Imager"* ]]; then
        print_error "Please run this script from the BathyCat-Seabed-Imager directory"
        exit 1
    fi
    
    # Make sure the project files are in the user's home directory
    if [[ "$PROJECT_DIR" != "$(pwd)" ]]; then
        print_status "Copying project files to user directory..."
        sudo -u "$INSTALL_USER" mkdir -p "/home/$INSTALL_USER"
        sudo -u "$INSTALL_USER" cp -r "$(pwd)" "/home/$INSTALL_USER/"
        chown -R "$INSTALL_USER:$INSTALL_USER" "$PROJECT_DIR"
    fi
    
    # Make main script executable
    chmod +x "$PROJECT_DIR/src/main.py"
    
    # Create a simple run script
    cat > "$PROJECT_DIR/run_bathyimager.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR/src"
exec "$PYTHON_ENV/bin/python" main.py --config "$CONFIG_DIR/bathyimager_config.json" "\$@"
EOF
    
    chmod +x "$PROJECT_DIR/run_bathyimager.sh"
    chown "$INSTALL_USER:$INSTALL_USER" "$PROJECT_DIR/run_bathyimager.sh"
    
    print_success "BathyImager software configured"
}

# Function to install configuration
install_configuration() {
    print_status "Setting up configuration..."
    
    # Use configuration file from project directory
    if [[ -f "config/bathyimager_config.json" ]]; then
        # Configuration stays in project directory
        print_status "Using configuration from project directory: $CONFIG_DIR/bathyimager_config.json"
        
        # Ensure proper ownership
        chown "$INSTALL_USER:$INSTALL_USER" "$CONFIG_DIR/bathyimager_config.json"
        chmod 644 "$CONFIG_DIR/bathyimager_config.json"
    else
        print_warning "Configuration file not found, creating default..."
        create_default_config
    fi
    
    print_success "Configuration ready"
}

# Function to create default configuration
create_default_config() {
    cat > "$CONFIG_DIR/bathyimager_config.json" << EOF
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
  
  "gps_port": "/dev/ttyAMA0",
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true,
  
  "pps_enabled": true,
  "pps_gpio_pin": 4,
  "pps_device": "/dev/pps0",
  
  "image_format": "JPEG",
  "jpeg_quality": 85,
  "enable_metadata": true,
  "enable_preview": false,
  "preview_width": 320,
  
  "storage_base_path": "/media/usb/bathyimager",
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
    chown "$INSTALL_USER:$INSTALL_USER" "$CONFIG_DIR/bathyimager_config.json"
}

# Function to create systemd service
create_systemd_service() {
    print_status "Installing systemd services..."
    
    # Copy the main BathyImager service file
    if [ -f "$PROJECT_DIR/scripts/bathyimager.service" ]; then
        cp "$PROJECT_DIR/scripts/bathyimager.service" "/etc/systemd/system/$SERVICE_NAME.service"
        print_success "BathyImager service file installed"
    else
        print_error "Service file not found at $PROJECT_DIR/scripts/bathyimager.service"
        return 1
    fi
    
    # Install GPS time sync helper script
    if [ -f "$PROJECT_DIR/scripts/gps_set_time.sh" ]; then
        chmod +x "$PROJECT_DIR/scripts/gps_set_time.sh"
        print_success "GPS time sync helper script installed"
    else
        print_warning "GPS time sync helper script not found"
    fi
    
    # Reload systemd
    systemctl daemon-reload
    
    print_success "Systemd services installed"
}

# Function to setup device permissions and udev rules
setup_device_permissions() {
    print_status "Setting up device permissions and udev rules..."
    
    # Install udev rules file
    if [ -f "$PROJECT_DIR/scripts/99-bathyimager.rules" ]; then
        cp "$PROJECT_DIR/scripts/99-bathyimager.rules" "/etc/udev/rules.d/"
        print_success "Udev rules installed"
    else
        print_warning "Udev rules file not found - creating basic rules"
        cat > "/etc/udev/rules.d/99-bathyimager.rules" << EOF
# Basic udev rules for BathyImager hardware access
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
SUBSYSTEM=="tty", KERNEL=="ttyUSB*", GROUP="dialout", MODE="0664"
SUBSYSTEM=="tty", KERNEL=="ttyACM*", GROUP="dialout", MODE="0664"
KERNEL=="gpiomem", GROUP="gpio", MODE="0664"
EOF
    fi
    
    # Make device permission script executable
    if [ -f "$PROJECT_DIR/scripts/setup_device_permissions.sh" ]; then
        chmod +x "$PROJECT_DIR/scripts/setup_device_permissions.sh"
        print_success "Device permission script made executable"
    fi
    
    # Add user to required groups if not already a member
    print_status "Adding user to hardware access groups..."
    usermod -a -G video,dialout,gpio,i2c,spi "$INSTALL_USER" || true
    
    # Reload udev rules
    udevadm control --reload-rules && udevadm trigger
    
    # Set current device permissions
    print_status "Setting current device permissions..."
    if [ -f "$PROJECT_DIR/scripts/setup_device_permissions.sh" ]; then
        "$PROJECT_DIR/scripts/setup_device_permissions.sh"
    else
        # Fallback manual permission setting
        chmod 666 /dev/video* 2>/dev/null || true
        chmod 666 /dev/ttyUSB* 2>/dev/null || true
        chmod 666 /dev/ttyACM* 2>/dev/null || true
        chmod 666 /dev/gpiomem 2>/dev/null || true
        chgrp video /dev/video* 2>/dev/null || true
        chgrp dialout /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true
        chgrp gpio /dev/gpiomem 2>/dev/null || true
    fi
    
    print_success "Device permissions configured"
}

# Function to resolve time synchronization conflicts
resolve_time_sync_conflicts() {
    print_status "Resolving time synchronization conflicts for GPS HAT..."
    
    # Check current time sync services
    SYSTEMD_TIMESYNCD_ACTIVE=false
    CHRONY_INSTALLED=false
    
    if systemctl is-active --quiet systemd-timesyncd 2>/dev/null; then
        SYSTEMD_TIMESYNCD_ACTIVE=true
        print_status "systemd-timesyncd is currently active"
    fi
    
    if command -v chronyd &> /dev/null; then
        CHRONY_INSTALLED=true
        print_status "chrony is already installed"
    fi
    
    # Stop systemd-timesyncd if active to prevent conflicts
    if $SYSTEMD_TIMESYNCD_ACTIVE; then
        print_status "Stopping systemd-timesyncd to prevent conflicts with chrony"
        systemctl stop systemd-timesyncd || true
        systemctl disable systemd-timesyncd || true
        print_success "systemd-timesyncd stopped and disabled"
    fi
    
    # Install chrony if not present
    if ! $CHRONY_INSTALLED; then
        print_status "Installing chrony for GPS PPS support..."
        apt-get install -y chrony
        print_success "chrony installed"
    else
        print_success "chrony already installed"
    fi
}

# Function to configure GPS HAT hardware
configure_gps_hat() {
    print_status "Configuring Adafruit Ultimate GPS HAT..."
    
    # Resolve time sync conflicts first
    resolve_time_sync_conflicts
    
    # Check if /boot/firmware/config.txt exists (newer Pi OS) or /boot/config.txt (older)
    if [ -f "/boot/firmware/config.txt" ]; then
        CONFIG_FILE="/boot/firmware/config.txt"
    elif [ -f "/boot/config.txt" ]; then
        CONFIG_FILE="/boot/config.txt"
    else
        print_warning "Boot config file not found - GPS HAT configuration may fail"
        return 1
    fi
    
    print_status "Using boot config: $CONFIG_FILE"
    
    # Backup original config
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Enable UART for GPS communication
    if ! grep -q "enable_uart=1" "$CONFIG_FILE"; then
        echo "enable_uart=1" >> "$CONFIG_FILE"
        print_success "UART enabled for GPS HAT communication"
    else
        print_success "UART already enabled"
    fi
    
    # Enable PPS GPIO overlay for GPIO 4 (GPS HAT standard)
    if ! grep -q "dtoverlay=pps-gpio,gpiopin=4" "$CONFIG_FILE"; then
        echo "dtoverlay=pps-gpio,gpiopin=4" >> "$CONFIG_FILE"
        print_success "PPS GPIO overlay enabled on GPIO 4"
    else
        print_success "PPS GPIO overlay already enabled"
    fi
    
    # Configure PPS module loading at boot
    if ! grep -q "pps-gpio" /etc/modules; then
        echo "pps-gpio" >> /etc/modules
        print_success "PPS-GPIO module configured for boot loading"
    else
        print_success "PPS-GPIO module already configured"
    fi
    
    # Set up GPIO UART permissions for GPS HAT
    if [ -f "/dev/ttyAMA0" ]; then
        chmod 666 /dev/ttyAMA0 2>/dev/null || true
        chgrp dialout /dev/ttyAMA0 2>/dev/null || true
        print_success "GPS HAT UART permissions configured"
    else
        print_warning "GPS HAT UART /dev/ttyAMA0 not found - may appear after reboot"
    fi
    
    # Configure Chrony for GPS HAT time synchronization
    configure_chrony_for_gps_hat
    
    # Apply timing optimizations for precise image capture
    configure_timing_optimizations
    
    print_success "GPS HAT hardware configuration complete"
    print_warning "REBOOT REQUIRED for GPS HAT changes to take effect"
}

# Function to configure chrony for GPS HAT
configure_chrony_for_gps_hat() {
    print_status "Configuring chrony for GPS HAT time synchronization..."
    
    # Check if chrony is installed
    if ! command -v chronyd &> /dev/null; then
        print_warning "chrony not installed - skipping GPS time synchronization setup"
        return 1
    fi
    
    local chrony_conf="/etc/chrony/chrony.conf"
    
    if [ ! -f "$chrony_conf" ]; then
        print_warning "chrony configuration file not found at $chrony_conf"
        return 1
    fi
    
    # Backup original chrony config
    if [ ! -f "${chrony_conf}.backup.original" ]; then
        cp "$chrony_conf" "${chrony_conf}.backup.original"
        print_status "Created backup of original chrony configuration"
    fi
    
    # Create timestamped backup
    cp "$chrony_conf" "${chrony_conf}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Remove any existing GPS HAT configuration
    sed -i '/# GPS HAT Time Sources for BathyCat/,/^$/d' "$chrony_conf"
    
    # Add GPS HAT time sources to Chrony configuration
    cat >> "$chrony_conf" << 'EOF'

# GPS HAT Time Sources for BathyCat
# NMEA time reference from GPS UART
refclock SHM 0 offset 0.5 delay 0.2 refid NMEA

# PPS time reference from GPIO 4 
refclock PPS /dev/pps0 trust lock NMEA refid PPS

# Allow NTP server access (for network time distribution)
allow 192.168.0.0/16
allow 10.0.0.0/8
allow 172.16.0.0/12

# Comment out pool servers when GPS is primary time source
# pool 2.debian.pool.ntp.org iburst
EOF
    
    print_success "Chrony configured for GPS HAT time sources"
    
    # Enable chrony service
    if systemctl enable chrony 2>/dev/null; then
        print_success "chrony service enabled"
    else
        print_warning "Failed to enable chrony service"
    fi
    
    # Start chrony service
    if systemctl start chrony 2>/dev/null; then
        print_success "chrony service started"
    else
        print_warning "Failed to start chrony service - will start after reboot"
    fi
    
    # Verify no conflicting time services are running
    local conflicts_found=false
    
    if systemctl is-active --quiet systemd-timesyncd 2>/dev/null; then
        print_warning "systemd-timesyncd is still active - this may conflict with chrony"
        conflicts_found=true
    fi
    
    if systemctl is-active --quiet ntp 2>/dev/null; then
        print_warning "ntp service is still active - this may conflict with chrony"
        conflicts_found=true
    fi
    
    if ! $conflicts_found; then
        print_success "No conflicting time services detected"
    fi
    
    return 0
}

# Function to configure timing optimizations for precise image capture
configure_timing_optimizations() {
    print_status "Configuring timing optimizations for precise image capture..."
    
    # 1. Configure CPU Governor for Performance
    print_status "Setting CPU governor to performance mode..."
    
    # Set immediate CPU governor to performance
    if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
        echo "performance" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true
        for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            [ -f "$cpu" ] && echo "performance" > "$cpu" 2>/dev/null || true
        done
        print_success "CPU governor set to performance mode"
    else
        print_warning "CPU frequency scaling not available"
    fi
    
    # Make CPU governor setting persistent
    cat > "/etc/systemd/system/cpufreq-performance.service" << 'EOF'
[Unit]
Description=Set CPU Governor to Performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do [ -f "$cpu" ] && echo "performance" > "$cpu"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable cpufreq-performance.service 2>/dev/null || true
    print_success "CPU performance governor service configured"
    
    # 2. Configure Kernel Boot Parameters for Timing Precision
    print_status "Configuring kernel boot parameters for timing precision..."
    
    # Determine boot config file location
    local CMDLINE_FILE=""
    if [ -f "/boot/firmware/cmdline.txt" ]; then
        CMDLINE_FILE="/boot/firmware/cmdline.txt"
    elif [ -f "/boot/cmdline.txt" ]; then
        CMDLINE_FILE="/boot/cmdline.txt"
    else
        print_warning "cmdline.txt not found - skipping kernel parameter optimization"
        return 1
    fi
    
    print_status "Using cmdline file: $CMDLINE_FILE"
    
    # Backup original cmdline
    cp "$CMDLINE_FILE" "$CMDLINE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Read current cmdline
    local current_cmdline=$(cat "$CMDLINE_FILE")
    local new_params=""
    
    # Add timing optimization parameters if not already present
    if ! echo "$current_cmdline" | grep -q "isolcpus="; then
        new_params="$new_params isolcpus=3"
        print_status "Adding CPU isolation parameter"
    fi
    
    if ! echo "$current_cmdline" | grep -q "rcu_nocbs="; then
        new_params="$new_params rcu_nocbs=3"
        print_status "Adding RCU callback offload parameter"
    fi
    
    if ! echo "$current_cmdline" | grep -q "nohz_full="; then
        new_params="$new_params nohz_full=3"
        print_status "Adding tickless CPU parameter"
    fi
    
    if ! echo "$current_cmdline" | grep -q "preempt="; then
        new_params="$new_params preempt=none"
        print_status "Adding preemption control parameter"
    fi
    
    if ! echo "$current_cmdline" | grep -q "processor.max_cstate="; then
        new_params="$new_params processor.max_cstate=1"
        print_status "Adding CPU C-state limit parameter"
    fi
    
    if ! echo "$current_cmdline" | grep -q "intel_idle.max_cstate="; then
        new_params="$new_params intel_idle.max_cstate=0"
        print_status "Adding Intel idle state parameter"
    fi
    
    # Add new parameters if any were needed
    if [ -n "$new_params" ]; then
        echo "$current_cmdline$new_params" > "$CMDLINE_FILE"
        print_success "Kernel timing optimization parameters added"
    else
        print_success "Kernel timing parameters already configured"
    fi
    
    # 3. Configure Real-time Process Priorities
    print_status "Configuring real-time process priorities..."
    
    # Create limits configuration for real-time scheduling
    cat > "/etc/security/limits.d/99-bathyimager-realtime.conf" << EOF
# Real-time scheduling limits for BathyImager timing precision
$INSTALL_USER    soft    rtprio    99
$INSTALL_USER    hard    rtprio    99
$INSTALL_USER    soft    nice      -20
$INSTALL_USER    hard    nice      -20
$INSTALL_USER    soft    memlock   unlimited
$INSTALL_USER    hard    memlock   unlimited
EOF
    
    print_success "Real-time process limits configured"
    
    # 4. Configure IRQ Affinity for GPS PPS
    print_status "Configuring IRQ affinity optimization..."
    
    # Create IRQ affinity service for GPS PPS timing
    cat > "/etc/systemd/system/irq-affinity-gps.service" << 'EOF'
[Unit]
Description=Optimize IRQ Affinity for GPS PPS Timing
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c '
# Move all IRQs away from CPU 3 (isolated for timing-critical tasks)
for irq in /proc/irq/*/smp_affinity; do
    [ -f "$irq" ] && echo "7" > "$irq" 2>/dev/null || true
done

# Set GPIO interrupt (PPS) to high priority if available
if [ -d "/proc/irq" ]; then
    for irq_dir in /proc/irq/*/; do
        if [ -f "${irq_dir}gpiochip0" ] || [ -f "${irq_dir}gpio" ]; then
            echo "1" > "${irq_dir}smp_affinity" 2>/dev/null || true
        fi
    done
fi
'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable irq-affinity-gps.service 2>/dev/null || true
    print_success "IRQ affinity optimization service configured"
    
    # 5. Configure GPIO Performance Settings
    print_status "Configuring GPIO performance settings..."
    
    # Set GPIO driver for better PPS timing
    if [ -f "/boot/firmware/config.txt" ]; then
        local GPIO_CONFIG="/boot/firmware/config.txt"
    elif [ -f "/boot/config.txt" ]; then
        local GPIO_CONFIG="/boot/config.txt"
    else
        print_warning "Boot config not found for GPIO optimization"
        return 1
    fi
    
    # Add GPIO performance optimizations if not present
    if ! grep -q "# GPIO Performance Optimizations for BathyCat" "$GPIO_CONFIG"; then
        cat >> "$GPIO_CONFIG" << 'EOF'

# GPIO Performance Optimizations for BathyCat
# Reduce GPIO interrupt latency for PPS timing
gpio=4=ip,pu  # GPS PPS input with pullup
EOF
        print_success "GPIO performance optimizations added to boot config"
    else
        print_success "GPIO performance optimizations already configured"
    fi
    
    print_success "Timing optimizations configuration complete"
    print_warning "REBOOT REQUIRED for timing optimizations to take effect"
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
    mkdir -p /media/usb
    
    # Add to fstab for auto-mount (optional)
    if ! grep -q "usb.*bathyimager" /etc/fstab; then
        echo "# BathyImager USB Storage" >> /etc/fstab
        echo "# LABEL=BATHYIMAGER /media/usb auto defaults,user,noauto 0 0" >> /etc/fstab
    fi
    
    # Create udev rule for auto-mount
    cat > "/etc/udev/rules.d/99-bathyimager-storage.rules" << EOF
# BathyImager USB Storage Auto-mount
SUBSYSTEM=="block", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", \
ACTION=="add", KERNEL=="sd[a-z][0-9]", \
RUN+="/bin/mkdir -p /media/usb", \
RUN+="/bin/mount -o defaults,uid=$INSTALL_USER,gid=$INSTALL_USER %N /media/usb"

SUBSYSTEM=="block", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", \
ACTION=="remove", KERNEL=="sd[a-z][0-9]", \
RUN+="/bin/umount /media/usb"
EOF
    
    # Reload udev rules
    udevadm control --reload-rules
    
    print_success "USB auto-mount configured"
}

# Function to run tests
run_tests() {
    print_status "Running system tests..."
    
    # Test Python environment
    if ! sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/python" -c "import sys; sys.path.append('$PROJECT_DIR/src'); import main; print('BathyImager import successful')"; then
        print_error "Python import test failed"
        return 1
    fi
    
    # Test camera access
    print_status "Testing camera access..."
    if ! sudo -u "$INSTALL_USER" "$PYTHON_ENV/bin/python" -c "
import cv2
try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            print('Camera test successful')
        else:
            print('Camera capture failed')
            exit(1)
    else:
        print('Camera open failed')
        exit(1)
except Exception as e:
    print(f'Camera test error: {e}')
    exit(1)
"; then
        print_warning "Camera test failed - check camera connection and permissions"
    else
        print_success "Camera test passed"
    fi
    
    # Test GPS device access
    print_status "Testing GPS device access..."
    if [ -e "/dev/ttyUSB0" ]; then
        if sudo -u "$INSTALL_USER" timeout 5 python3 -c "
import serial
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    ser.close()
    print('GPS device accessible')
except Exception as e:
    print(f'GPS test error: {e}')
    exit(1)
" 2>/dev/null; then
            print_success "GPS device test passed"
        else
            print_warning "GPS device test failed - check GPS connection"
        fi
    else
        print_warning "GPS device /dev/ttyUSB0 not found"
    fi
    
    # Test run script
    if ! sudo -u "$INSTALL_USER" "$PROJECT_DIR/run_bathyimager.sh" --help >/dev/null 2>&1; then
        print_warning "Run script test failed - check hardware connections"
    fi
    
    print_success "System tests completed"
}

# Function to enable and start services
enable_service() {
    print_status "Enabling and starting BathyImager services..."
    
    # Note: GPS time sync is now integrated into the main GPS class
    # No separate services needed - GPS syncs time automatically on first fix
    print_success "GPS time sync integrated into main GPS service"
    
    # Enable main BathyImager service
    systemctl enable "$SERVICE_NAME"
    
    # Start main service
    systemctl start "$SERVICE_NAME"
    
    # Check status
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "BathyImager imaging service is running"
    else
        print_warning "BathyImager imaging service failed to start - check logs with: journalctl -u $SERVICE_NAME"
    fi
    
    # Show GPS boot sync service status
    if [ -f "/etc/systemd/system/gps-boot-sync.service" ]; then
        if systemctl is-enabled --quiet gps-boot-sync; then
            print_success "GPS boot sync service is enabled (will run on next boot)"
        else
            print_warning "GPS boot sync service is not enabled"
        fi
    fi
}

# Function to show installation summary
show_summary() {
    print_success "BathyImager installation completed!"
    
    echo
    echo "Installation Summary:"
    echo "===================="
    echo "Project Directory: $PROJECT_DIR"
    echo "Configuration:     $CONFIG_DIR/bathyimager_config.json"
    echo "Log Directory:     $LOG_DIR"
    echo "Service Name:      $SERVICE_NAME"
    echo "Python Environment: $PYTHON_ENV"
    echo "Run Script:        $PROJECT_DIR/run_bathyimager.sh"
    echo
    echo "Useful Commands:"
    echo "==============="
    echo "Check service status:    systemctl status $SERVICE_NAME"
    echo "View logs:              journalctl -u $SERVICE_NAME -f"
    echo "Check time status:      timedatectl status"
    echo "Restart service:        sudo systemctl restart $SERVICE_NAME"
    echo "Stop service:           sudo systemctl stop $SERVICE_NAME"
    echo "Edit configuration:     nano $CONFIG_DIR/bathyimager_config.json"
    echo "Run manually:           sudo -u $INSTALL_USER $PROJECT_DIR/run_bathyimager.sh"
    echo "Update code:            cd $PROJECT_DIR && git pull"
    echo
    echo "Development Commands:"
    echo "===================="
    echo "Switch to service user: sudo -u $INSTALL_USER -i"
    echo "Project directory:      cd $PROJECT_DIR"
    echo "Activate Python env:    source $PROJECT_DIR/venv/bin/activate"
    echo "Run development mode:   cd $PROJECT_DIR/src && python main.py --config ../config/bathyimager_config.json"
    echo
    echo "System Services:"
    echo "==============="
    echo "Main service status:     systemctl status $SERVICE_NAME"
    echo "GPS sync service:        systemctl status gps-boot-sync"
    echo "View main logs:          journalctl -u $SERVICE_NAME -f"
    echo "View GPS sync logs:      journalctl -u gps-boot-sync -f"
    echo "Restart main service:    sudo systemctl restart $SERVICE_NAME"
    echo "Stop main service:       sudo systemctl stop $SERVICE_NAME"
    echo "Check time sync status:  timedatectl status"
    echo
    echo "Time Synchronization Status:"
    echo "============================"
    echo "  systemd-timesyncd: $(systemctl is-active systemd-timesyncd 2>/dev/null || echo 'inactive')"
    echo "  chrony: $(systemctl is-active chrony 2>/dev/null || echo 'not installed')"
    echo "  GPS PPS device: $(ls /dev/pps* 2>/dev/null || echo 'not available (needs reboot + GPS fix)')"
    echo
    echo "Next Steps:"
    echo "==========="
    echo "1. Connect USB camera and GPS HAT (if not already connected)"
    echo "2. Insert USB storage device"
    echo "3. REBOOT to enable GPS HAT PPS support"
    echo "4. Check service logs for any errors (journalctl -u bathyimager -f)"
    echo "5. Verify GPS PPS timing: sudo ppstest /dev/pps0 (after GPS fix)"
    echo "6. Check chrony GPS sources: sudo chronyc sources -v"
    echo "7. Test image capture functionality"
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
    setup_device_permissions
    configure_gps_hat
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