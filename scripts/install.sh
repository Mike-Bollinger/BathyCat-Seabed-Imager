#!/bin/bash
#
# BathyCat Complete Installation Script
# ====================================
# 
# Installs and configures the complete BathyCat system

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
INSTALL_DIR="/opt/bathycat"
CONFIG_DIR="/etc/bathycat"
SERVICE_NAME="bathycat-imager"

# Detect actual user (the one who invoked sudo)
if [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
else
    USER="pi"  # Fallback to pi if SUDO_USER not set
fi

# Validate user exists
if ! id "$USER" &>/dev/null; then
    print_error "User '$USER' does not exist on this system"
    print_error "Available users: $(cut -d: -f1 /etc/passwd | grep -v '^_' | head -10 | tr '\n' ' ')"
    exit 1
fi

print_status "Using user: $USER"

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    apt-get update
    print_success "Package lists updated"
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Note: Updated package names for Debian Trixie compatibility (2025)
    # - libatlas-base-dev → libopenblas-dev (BLAS/LAPACK libraries)
    # - exfat-utils → exfatprogs (exFAT filesystem utilities)
    
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        cmake \
        pkg-config \
        libjpeg-dev \
        libtiff5-dev \
        libpng-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libgtk-3-dev \
        libopenblas-dev \
        gfortran \
        python3-numpy \
        fswebcam \
        v4l-utils \
        usbutils \
        exfat-fuse \
        exfatprogs \
        git \
        wget \
        unzip
    
    print_success "System dependencies installed"
}

# Create installation directories
create_directories() {
    print_status "Creating installation directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "/var/log/bathycat"
    
    chown -R "$USER:$USER" "$INSTALL_DIR"
    chown -R "$USER:$USER" "$CONFIG_DIR"
    chown -R "$USER:$USER" "/var/log/bathycat"
    
    print_success "Directories created"
}

# Copy application files
copy_application() {
    print_status "Installing BathyCat application..."
    
    if [ -d "src" ]; then
        cp -r src/* "$INSTALL_DIR/"
        cp config/bathycat_config.json "$CONFIG_DIR/config.json"
        cp scripts/setup_usb_storage_robust.sh "$INSTALL_DIR/setup_usb_storage.sh"
        
        # Make scripts executable
        chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
        
        chown -R "$USER:$USER" "$INSTALL_DIR"
        chown -R "$USER:$USER" "$CONFIG_DIR"
        
        print_success "Application files installed"
    else
        print_error "Source files not found. Run from BathyCat project directory."
        exit 1
    fi
}

# Create Python virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    sudo -u "$USER" python3 -m venv "$INSTALL_DIR/venv"
    
    # Activate and install packages
    sudo -u "$USER" bash -c "
        source '$INSTALL_DIR/venv/bin/activate'
        pip install --upgrade pip
        pip install opencv-python numpy pillow pyserial pynmea2 psutil piexif
    "
    
    print_success "Python environment created"
}

# Configure camera permissions
configure_camera() {
    print_status "Configuring camera permissions..."
    
    # Add user to video group
    usermod -a -G video "$USER"
    
    # Create udev rule for camera permissions
    cat > /etc/udev/rules.d/99-bathycat-camera.rules << EOF
# BathyCat Camera Permissions
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
KERNEL=="video[0-9]*", GROUP="video", MODE="0664"
EOF
    
    udevadm control --reload-rules
    
    print_success "Camera configured"
}

# Configure GPS
configure_gps() {
    print_status "Configuring USB GPS..."
    
    # Add user to dialout group for USB serial access
    usermod -a -G dialout "$USER"
    
    # Create udev rule for GPS device
    cat > /etc/udev/rules.d/99-bathycat-gps.rules << EOF
# BathyCat USB GPS
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="gps-usb"
SUBSYSTEM=="tty", ATTRS{product}=="*GPS*", SYMLINK+="gps-usb"
EOF
    
    udevadm control --reload-rules
    
    print_success "GPS configured"
}

# Create systemd service
create_service() {
    print_status "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=BathyCat Seabed Imager
Documentation=https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager
After=network.target multi-user.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStartPre=/bin/sleep 10
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/bathycat_imager.py --config $CONFIG_DIR/config.json --verbose
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=always
RestartSec=30
TimeoutStartSec=60
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bathycat-imager

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security (relaxed for hardware access)
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    print_success "Service created and enabled"
}

# Create utility scripts
create_utilities() {
    print_status "Creating utility scripts..."
    
    # Status script
    cat > "$INSTALL_DIR/status.sh" << 'EOF'
#!/bin/bash
echo "=== BathyCat System Status ==="
echo ""
echo "Service Status:"
systemctl status bathycat-imager --no-pager || true
echo ""
echo "USB Storage:"
df -h /media/usb-storage 2>/dev/null || echo "Not mounted"
echo ""
echo "USB Devices:"
lsusb | grep -E "(camera|GPS|storage)" || lsusb | head -5
echo ""
echo "Recent Logs:"
journalctl -u bathycat-imager --no-pager -n 5 || true
EOF
    
    chmod +x "$INSTALL_DIR/status.sh"
    
    print_success "Utility scripts created"
}

# Run tests
run_tests() {
    print_status "Running system tests..."
    
    # Test Python environment
    if sudo -u "$USER" "$INSTALL_DIR/venv/bin/python3" -c "import cv2, serial, numpy; print('✅ Python dependencies OK')"; then
        print_success "Python environment test passed"
    else
        print_warning "Python environment test failed"
    fi
    
    # Test camera
    if lsusb | grep -i camera >/dev/null; then
        print_success "USB camera detected"
    else
        print_warning "No USB camera detected"
    fi
    
    # Test GPS
    if ls /dev/ttyUSB* /dev/ttyACM* >/dev/null 2>&1; then
        print_success "USB serial devices found (likely GPS)"
    else
        print_warning "No USB serial devices found"
    fi
}

# Main installation
main() {
    echo "🚀 BathyCat Seabed Imager Installation"
    echo "====================================="
    echo ""
    
    check_root
    update_system
    install_dependencies
    create_directories
    copy_application
    create_venv
    configure_camera
    configure_gps
    create_service
    create_utilities
    run_tests
    
    echo ""
    print_success "Installation completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "1. Reboot the system: sudo reboot"
    echo "2. Connect USB devices (camera, GPS, storage)"
    echo "3. Set up USB storage: sudo $INSTALL_DIR/setup_usb_storage.sh"
    echo "4. Start the service: sudo systemctl start $SERVICE_NAME"
    echo "5. Check status: $INSTALL_DIR/status.sh"
    echo "6. View logs: journalctl -u $SERVICE_NAME -f"
    echo ""
}

# Check if we're in the right directory
if [ ! -f "src/bathycat_imager.py" ]; then
    print_error "Please run this script from the BathyCat project directory"
    exit 1
fi

# Run main installation
main "$@"