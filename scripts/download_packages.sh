#!/bin/bash

# BathyImager System Package Downloader
# Run this on a Linux system with internet to download required packages
#
# Usage: ./download_packages.sh [output_directory]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Output directory
OUTPUT_DIR="${1:-system-packages}"

print_status "BathyImager Package Downloader"
print_status "Downloading system packages to: $OUTPUT_DIR"

# Check if apt is available
if ! command -v apt >/dev/null 2>&1; then
    print_error "This script requires apt package manager (Debian/Ubuntu)"
    print_error "For other distributions, manually download equivalent packages"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Update package lists
print_status "Updating package lists..."
apt update

# List of required packages
packages=(
    "dhcpcd5"           # DHCP client daemon
    "wpasupplicant"     # WiFi authentication  
    "wireless-tools"    # WiFi utilities
    "net-tools"         # Network utilities (ifconfig, route, etc.)
    "iproute2"          # Modern network utilities (ip command)
    "dnsutils"          # DNS utilities (nslookup, dig)
    "iputils-ping"      # Ping utility
    "traceroute"        # Network tracing
    "netcat-openbsd"    # Network debugging
    "iftop"             # Network monitoring
    "iperf3"            # Network performance testing
)

print_status "Downloading packages..."

for package in "${packages[@]}"; do
    print_status "Downloading $package..."
    if apt download "$package" 2>/dev/null; then
        print_success "Downloaded $package"
    else
        print_warning "Failed to download $package (may not be available)"
    fi
done

# Download dependencies
print_status "Downloading dependencies..."
for package in "${packages[@]}"; do
    print_status "Downloading dependencies for $package..."
    apt-cache depends "$package" | grep "Depends:" | cut -d: -f2 | tr -d ' ' | while read dep; do
        if [[ "$dep" != *"|"* ]] && [[ "$dep" != "<"* ]] && [[ "$dep" != ">"* ]]; then
            apt download "$dep" 2>/dev/null || true
        fi
    done
done

# Create installation script
print_status "Creating installation script..."
cat > install_packages.sh << 'EOF'
#!/bin/bash

# BathyImager Package Installer
# Install downloaded system packages on Raspberry Pi

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

print_status "Installing BathyImager system packages..."

# Install packages
if ls *.deb >/dev/null 2>&1; then
    print_status "Installing .deb packages..."
    dpkg -i *.deb || true
    
    print_status "Fixing any broken dependencies..."
    apt --fix-broken install -y
    
    print_success "Package installation complete!"
    
    print_status "Enabling services..."
    systemctl enable dhcpcd || true
    systemctl enable wpa_supplicant@wlan0 || true
    
    print_success "Services enabled!"
    print_status "You can now run the network setup: ./network_setup.sh"
else
    print_error "No .deb packages found in current directory"
    exit 1
fi
EOF

chmod +x install_packages.sh

# Create transfer instructions
cat > TRANSFER_INSTRUCTIONS.md << 'EOF'
# Package Transfer Instructions

## What This Contains
This directory contains pre-downloaded Debian packages needed for BathyImager networking.

## Transfer to Raspberry Pi

### Method 1: USB Drive
1. Copy this entire directory to a USB drive
2. Insert USB into Raspberry Pi
3. Mount and copy:
   ```bash
   sudo mkdir -p /media/usb
   sudo mount /dev/sda1 /media/usb
   cp -r /media/usb/system-packages ~/
   cd ~/system-packages
   sudo ./install_packages.sh
   ```

### Method 2: SCP Transfer
```bash
scp -r system-packages pi@<pi-ip>:~/
ssh pi@<pi-ip>
cd ~/system-packages
sudo ./install_packages.sh
```

### Method 3: SD Card
1. Copy to SD card boot partition before first boot
2. After Pi boots:
   ```bash
   sudo mv /boot/system-packages ~/
   cd ~/system-packages  
   sudo ./install_packages.sh
   ```

## After Installation
Run the BathyImager network setup:
```bash
cd /opt/bathyimager
sudo ./scripts/network_setup.sh
```
EOF

# Summary
print_success "Package download complete!"
print_status "Downloaded $(ls *.deb | wc -l) packages"
print_status "Total size: $(du -sh . | cut -f1)"

echo ""
print_status "NEXT STEPS:"
print_status "1. Copy this directory to your Raspberry Pi"
print_status "2. Run: sudo ./install_packages.sh"
print_status "3. Run: sudo ./scripts/network_setup.sh"
echo ""
print_status "See TRANSFER_INSTRUCTIONS.md for detailed transfer methods"