#!/bin/bash
"""
BathyCat Seabed Imager - Installation Script
===========================================

Automated installation script for Raspberry Pi OS.
This script will install all dependencies and configure the system.

Author: BathyCat Systems
Date: August 2025
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/bathycat"
CONFIG_DIR="/etc/bathycat"
LOG_DIR="/var/log/bathycat"
SERVICE_NAME="bathycat-imager"

# Detect the actual user (not root, but the user who called sudo)
if [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
else
    # Fallback: find the first non-root user with a home directory
    USER=$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd | head -1)
fi

print_status "Detected user: $USER"

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
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check OS compatibility
check_os() {
    print_status "Checking OS compatibility..."
    
    if [ ! -f /etc/os-release ]; then
        print_error "Cannot determine OS version"
        exit 1
    fi
    
    . /etc/os-release
    
    if [[ "$ID" != "raspbian" && "$ID" != "debian" ]]; then
        print_warning "This script is designed for Raspberry Pi OS, but may work on other Debian-based systems"
    fi
    
    print_success "OS check completed"
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    
    apt-get update
    apt-get upgrade -y
    
    print_success "System packages updated"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    # Essential packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        cmake \
        pkg-config \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libgtk-3-dev \
        libatlas-base-dev \
        gfortran \
        python3-numpy \
        python3-opencv \
        gpsd \
        gpsd-clients \
        pps-tools \
        chrony \
        rsync \
        htop \
        screen
    
    print_success "System dependencies installed"
}

# Function to configure GPS/PPS
configure_gps() {
    print_status "Configuring GPS and PPS..."
    
    # Enable UART and disable Bluetooth on UART
    if ! grep -q "enable_uart=1" /boot/config.txt; then
        echo "enable_uart=1" >> /boot/config.txt
    fi
    
    if ! grep -q "dtoverlay=disable-bt" /boot/config.txt; then
        echo "dtoverlay=disable-bt" >> /boot/config.txt
    fi
    
    # Configure serial port
    systemctl disable hciuart 2>/dev/null || true
    
    # Configure GPSD
    cat > /etc/default/gpsd << EOF
# Default settings for the gpsd init script and the hotplug wrapper.

# Start the gpsd daemon automatically at boot time
START_DAEMON="true"

# Use USB hotplugging to add new USB devices automatically to the daemon
USBAUTO="false"

# Devices gpsd should collect to at boot time.
DEVICES="/dev/serial0"

# Other options you want to pass to gpsd
GPSD_OPTIONS="-n -s 9600"
EOF
    
    # Enable and start GPSD
    systemctl enable gpsd
    
    print_success "GPS configuration completed"
}

# Function to configure camera
configure_camera() {
    print_status "Configuring camera settings..."
    
    # Enable camera in raspi-config equivalent
    if ! grep -q "start_x=1" /boot/config.txt; then
        echo "start_x=1" >> /boot/config.txt
    fi
    
    if ! grep -q "gpu_mem=128" /boot/config.txt; then
        echo "gpu_mem=128" >> /boot/config.txt
    fi
    
    # Add user to video group
    usermod -a -G video $USER
    
    print_success "Camera configuration completed"
}

# Function to setup storage
setup_storage() {
    print_status "Setting up storage configuration..."
    
    # Create mount point for USB storage
    mkdir -p /media/usb-storage
    
    # Add fstab entry (commented out - requires manual UUID setup)
    if ! grep -q "/media/usb-storage" /etc/fstab; then
        echo "# BathyCat USB Storage (uncomment and set correct UUID)" >> /etc/fstab
        echo "# UUID=your-usb-uuid /media/usb-storage ext4 defaults,noatime 0 2" >> /etc/fstab
    fi
    
    # Create BathyCat storage directory structure
    mkdir -p /media/usb-storage/bathycat/{images,metadata,previews,logs,exports}
    chown -R $USER:$USER /media/usb-storage/bathycat
    
    print_success "Storage setup completed"
}

# Function to create Python virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    # Create installation directory
    mkdir -p $INSTALL_DIR
    
    # Create virtual environment
    python3 -m venv $INSTALL_DIR/venv
    
    # Activate and upgrade pip
    source $INSTALL_DIR/venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    print_success "Virtual environment created"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    source $INSTALL_DIR/venv/bin/activate
    
    # Install required packages
    pip install \
        opencv-python \
        numpy \
        pillow \
        pyserial \
        pynmea2 \
        psutil \
        piexif \
        asyncio-mqtt \
        aiofiles
    
    print_success "Python dependencies installed"
}

# Function to copy application files
copy_application() {
    print_status "Copying application files..."
    
    # Copy source code
    cp -r src/ $INSTALL_DIR/
    cp -r config/ $INSTALL_DIR/
    
    # Set permissions
    chmod +x $INSTALL_DIR/src/bathycat_imager.py
    chown -R $USER:$USER $INSTALL_DIR
    
    print_success "Application files copied"
}

# Function to create configuration
create_configuration() {
    print_status "Creating system configuration..."
    
    # Create config directory
    mkdir -p $CONFIG_DIR
    
    # Copy configuration file
    cp config/bathycat_config.json $CONFIG_DIR/config.json
    
    # Create log directory
    mkdir -p $LOG_DIR
    chown $USER:$USER $LOG_DIR
    
    print_success "Configuration created"
}

# Function to create systemd service
create_service() {
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=BathyCat Seabed Imager
After=network.target gpsd.service
Wants=gpsd.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/src/bathycat_imager.py --config $CONFIG_DIR/config.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Performance optimizations
Nice=-10
IOSchedulingClass=2
IOSchedulingPriority=4

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    print_success "Systemd service created and enabled"
}

# Function to create startup script
create_startup_script() {
    print_status "Creating startup script..."
    
    cat > $INSTALL_DIR/start_capture.sh << 'EOF'
#!/bin/bash
# BathyCat Seabed Imager Startup Script

INSTALL_DIR="/opt/bathycat"
CONFIG_DIR="/etc/bathycat"

echo "Starting BathyCat Seabed Imager..."
echo "Installation: $INSTALL_DIR"
echo "Configuration: $CONFIG_DIR"

# Activate virtual environment
source $INSTALL_DIR/venv/bin/activate

# Start the application
python3 $INSTALL_DIR/src/bathycat_imager.py --config $CONFIG_DIR/config.json --verbose

EOF
    
    chmod +x $INSTALL_DIR/start_capture.sh
    
    print_success "Startup script created"
}

# Function to create useful utilities
create_utilities() {
    print_status "Creating utility scripts..."
    
    # Status check script
    cat > $INSTALL_DIR/status.sh << 'EOF'
#!/bin/bash
# BathyCat Status Check Script

echo "=== BathyCat Seabed Imager Status ==="
echo

# Service status
echo "Service Status:"
systemctl status bathycat-imager --no-pager -l

echo
echo "Storage Status:"
df -h /media/usb-storage 2>/dev/null || echo "USB storage not mounted"

echo
echo "GPS Status:"
gpspipe -r -n 5 2>/dev/null || echo "GPS not available"

echo
echo "Camera Status:"
lsusb | grep -i camera || echo "No USB cameras detected"

echo
echo "Recent Logs:"
journalctl -u bathycat-imager --no-pager -n 10

EOF
    
    # Manual start script
    cat > $INSTALL_DIR/manual_start.sh << 'EOF'
#!/bin/bash
# Manual start script for testing

cd /opt/bathycat
source venv/bin/activate
python3 src/bathycat_imager.py --config /etc/bathycat/config.json --verbose

EOF
    
    # Stop script
    cat > $INSTALL_DIR/stop.sh << 'EOF'
#!/bin/bash
# Stop BathyCat service

echo "Stopping BathyCat Seabed Imager..."
sudo systemctl stop bathycat-imager
echo "Service stopped"

EOF
    
    # Make scripts executable
    chmod +x $INSTALL_DIR/*.sh
    
    print_success "Utility scripts created"
}

# Function to perform post-installation setup
post_install_setup() {
    print_status "Performing post-installation setup..."
    
    # Create desktop shortcut
    if [ -d "/home/$USER/Desktop" ]; then
        cat > /home/$USER/Desktop/BathyCat.desktop << EOF
[Desktop Entry]
Name=BathyCat Status
Comment=Check BathyCat Seabed Imager Status
Exec=lxterminal -e $INSTALL_DIR/status.sh
Icon=applications-system
Terminal=true
Type=Application
Categories=System;
EOF
        chmod +x /home/$USER/Desktop/BathyCat.desktop
        chown $USER:$USER /home/$USER/Desktop/BathyCat.desktop
    fi
    
    # Add useful aliases to .bashrc
    if ! grep -q "BathyCat aliases" /home/$USER/.bashrc; then
        cat >> /home/$USER/.bashrc << EOF

# BathyCat aliases
alias bathycat-status='$INSTALL_DIR/status.sh'
alias bathycat-start='sudo systemctl start bathycat-imager'
alias bathycat-stop='sudo systemctl stop bathycat-imager'
alias bathycat-restart='sudo systemctl restart bathycat-imager'
alias bathycat-logs='journalctl -u bathycat-imager -f'
alias bathycat-config='sudo nano $CONFIG_DIR/config.json'

EOF
    fi
    
    print_success "Post-installation setup completed"
}

# Function to run system tests
run_tests() {
    print_status "Running system tests..."
    
    # Test camera
    echo "Testing camera..."
    if lsusb | grep -qi camera; then
        print_success "Camera detected via USB"
    else
        print_warning "No USB camera detected - please connect camera"
    fi
    
    # Test GPS
    echo "Testing GPS..."
    if [ -e /dev/serial0 ]; then
        print_success "GPS serial port available"
    else
        print_warning "GPS serial port not found - check configuration"
    fi
    
    # Test storage
    echo "Testing storage..."
    if [ -d /media/usb-storage ]; then
        print_success "Storage mount point exists"
    else
        print_warning "Storage mount point missing"
    fi
    
    # Test Python environment
    echo "Testing Python environment..."
    if source $INSTALL_DIR/venv/bin/activate && python3 -c "import cv2, serial, numpy"; then
        print_success "Python dependencies available"
    else
        print_error "Python dependency test failed"
    fi
    
    print_success "System tests completed"
}

# Main installation function
main() {
    echo "========================================"
    echo "BathyCat Seabed Imager Installation"
    echo "========================================"
    echo
    
    check_root
    check_os
    
    print_status "Starting installation process..."
    
    update_system
    install_system_dependencies
    configure_gps
    configure_camera
    setup_storage
    create_venv
    install_python_dependencies
    copy_application
    create_configuration
    create_service
    create_startup_script
    create_utilities
    post_install_setup
    run_tests
    
    echo
    print_success "Installation completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Reboot the system: sudo reboot"
    echo "2. Connect your USB flash drive and update /etc/fstab with correct UUID"
    echo "3. Connect USB camera and GPS HAT"
    echo "4. Test the system: $INSTALL_DIR/status.sh"
    echo "5. Start the service: sudo systemctl start bathycat-imager"
    echo
    echo "Configuration file: $CONFIG_DIR/config.json"
    echo "Logs: journalctl -u bathycat-imager -f"
    echo "Status: $INSTALL_DIR/status.sh"
    echo
}

# Run main function
main "$@"
