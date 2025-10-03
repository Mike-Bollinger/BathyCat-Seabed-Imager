#!/bin/bash
#
# BathyCat Safe Install Script - H264 USB Camera Edition
# ======================================================
#
# This version is designed to avoid system bricking and specifically
# handles the H264 USB camera compatibility issues we discovered.
#

set -e  # Exit on any error

# Colors for output
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

# Detect user
if [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
else
    USER=$(whoami)
    if [ "$USER" = "root" ]; then
        USER="pi"  # Default fallback
    fi
fi

print_status "Installing BathyCat for user: $USER"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run with sudo"
    exit 1
fi

# Function to safely update system
safe_system_update() {
    print_status "Updating package lists..."
    apt-get update
    
    # Only upgrade if user confirms (to avoid breaking changes)
    read -p "Do you want to upgrade all packages? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Upgrading packages..."
        apt-get upgrade -y
    else
        print_warning "Skipping package upgrade"
    fi
}

# Install only essential packages (no risky ones)
install_safe_dependencies() {
    print_status "Installing essential dependencies..."
    
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        wget \
        unzip \
        v4l-utils \
        fswebcam \
        htop \
        screen \
        rsync
    
    print_success "Essential dependencies installed"
}

# Install Python packages in virtual environment (safer)
install_python_packages() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment as the user (not root)
    sudo -u $USER python3 -m venv /home/$USER/bathycat-venv
    
    # Install packages in virtual environment
    sudo -u $USER /home/$USER/bathycat-venv/bin/pip install --upgrade pip
    sudo -u $USER /home/$USER/bathycat-venv/bin/pip install \
        opencv-python \
        numpy \
        pynmea2 \
        pyserial \
        asyncio-mqtt \
        pillow
    
    print_success "Python packages installed in virtual environment"
}

# Create directories with proper permissions
create_directories() {
    print_status "Creating directories..."
    
    mkdir -p $INSTALL_DIR
    mkdir -p $CONFIG_DIR
    mkdir -p /var/log/bathycat
    
    # Set proper ownership
    chown -R $USER:$USER $INSTALL_DIR
    chown -R $USER:$USER $CONFIG_DIR
    chown -R $USER:$USER /var/log/bathycat
    
    print_success "Directories created"
}

# Copy BathyCat files
install_bathycat_files() {
    print_status "Installing BathyCat files..."
    
    # Assume we're running from the BathyCat directory
    if [ -d "src" ]; then
        cp -r src/* $INSTALL_DIR/
        cp config/bathycat_config.json $CONFIG_DIR/
        
        # Apply camera fixes immediately
        if [ -d "debug" ]; then
            cp debug/fswebcam_integration.py $INSTALL_DIR/
            cp debug/camera_diagnostics.py $INSTALL_DIR/
            cp debug/fix_camera_permissions.sh $INSTALL_DIR/
            chmod +x $INSTALL_DIR/fix_camera_permissions.sh
        fi
        
        chown -R $USER:$USER $INSTALL_DIR
        chown -R $USER:$USER $CONFIG_DIR
        
        print_success "BathyCat files installed"
    else
        print_error "BathyCat source files not found. Please run from BathyCat directory."
        exit 1
    fi
}

# Configure USB storage (safer approach)
configure_usb_storage() {
    print_status "Configuring USB storage..."
    
    # Create mount point
    mkdir -p /media/usb-storage
    
    # Add to fstab only if not already there
    if ! grep -q "/media/usb-storage" /etc/fstab; then
        echo "# BathyCat USB Storage" >> /etc/fstab
        echo "LABEL=BATHYCAT-DATA /media/usb-storage exfat defaults,uid=1000,gid=1000,umask=000,nofail 0 0" >> /etc/fstab
        print_warning "USB storage configured. Please label your USB drive as 'BATHYCAT-DATA'"
    fi
    
    print_success "USB storage configuration added"
}

# Configure USB GPS (safer - no boot partition changes)
configure_usb_gps() {
    print_status "Configuring USB GPS..."
    
    # Add user to dialout group for USB access
    usermod -a -G dialout $USER
    
    # Create udev rule for consistent GPS device naming
    cat > /etc/udev/rules.d/99-bathycat-gps.rules << EOF
# BathyCat USB GPS
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="gps-usb"
SUBSYSTEM=="tty", ATTRS{product}=="*GPS*", SYMLINK+="gps-usb"
EOF
    
    print_success "USB GPS configured"
}

# Configure camera (with H264 fixes)
configure_camera() {
    print_status "Configuring camera with H264 fixes..."
    
    # Add user to video group
    usermod -a -G video $USER
    
    # Set camera permissions
    if [ -e /dev/video0 ]; then
        chmod 666 /dev/video0
    fi
    
    # Create camera fix script that runs on boot
    cat > /etc/systemd/system/bathycat-camera-fix.service << EOF
[Unit]
Description=BathyCat Camera Permissions Fix
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'chmod 666 /dev/video* 2>/dev/null || true'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable bathycat-camera-fix.service
    
    print_success "Camera configuration applied"
}

# Create systemd service (using virtual environment)
create_service() {
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=BathyCat Seabed Imager
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=/home/$USER/bathycat-venv/bin/python $INSTALL_DIR/bathycat_imager.py --config $CONFIG_DIR/bathycat_config.json
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    print_success "Systemd service created"
}

# Apply camera fixes immediately
apply_camera_fixes() {
    print_status "Applying H264 camera fixes..."
    
    # Run our camera permission fix
    if [ -f "$INSTALL_DIR/fix_camera_permissions.sh" ]; then
        sudo -u $USER bash $INSTALL_DIR/fix_camera_permissions.sh
    fi
    
    print_success "Camera fixes applied"
}

# Main installation function
main() {
    print_status "Starting BathyCat Safe Installation..."
    
    safe_system_update
    install_safe_dependencies
    install_python_packages
    create_directories
    install_bathycat_files
    configure_usb_storage
    configure_usb_gps
    configure_camera
    create_service
    apply_camera_fixes
    
    print_success "BathyCat installation completed successfully!"
    print_status "Next steps:"
    echo "1. Reboot the system: sudo reboot"
    echo "2. Connect USB devices (GPS, camera, storage)"
    echo "3. Label USB drive as 'BATHYCAT-DATA' and format as exFAT"
    echo "4. Start service: sudo systemctl start $SERVICE_NAME"
    echo "5. Check status: sudo systemctl status $SERVICE_NAME"
    echo "6. View logs: journalctl -u $SERVICE_NAME -f"
}

# Run main function
main "$@"