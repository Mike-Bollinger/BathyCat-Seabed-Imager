#!/bin/bash

# BathyImager Internet Sharing Setup Script
# Use this when your computer is sharing internet through Ethernet
# 
# Usage: sudo ./setup_shared_internet.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

print_status "Setting up internet connection sharing via Ethernet..."

# Configure IP address for Pi
print_status "Configuring IP address for eth0..."
ip addr add 192.168.137.200/24 dev eth0 2>/dev/null || true
ip link set eth0 up

# Add default route via computer (192.168.137.1)
print_status "Adding default route via computer (192.168.137.1)..."
ip route del default 2>/dev/null || true
ip route add default via 192.168.137.1 dev eth0 2>/dev/null || true

# Set DNS
print_status "Configuring DNS servers..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# Test connectivity
print_status "Testing internet connectivity..."
if ping -c 3 -W 5 google.com >/dev/null 2>&1; then
    print_success "Internet connectivity confirmed!"
    
    print_status "Installing required networking packages..."
    apt update
    
    packages=(
        "dhcpcd5"
        "wpasupplicant" 
        "wireless-tools"
        "net-tools"
        "iproute2"
        "dnsutils"
        "iputils-ping"
    )
    
    for package in "${packages[@]}"; do
        print_status "Installing $package..."
        apt install -y "$package"
    done
    
    print_success "All packages installed!"
    
    # Enable services
    print_status "Enabling network services..."
    systemctl enable dhcpcd
    systemctl enable wpa_supplicant@wlan0
    
    print_success "Services enabled!"
    
    print_status "Cleaning up temporary network configuration..."
    # Remove temporary config - dhcpcd will take over
    ip route del default via 192.168.137.1 dev eth0 2>/dev/null || true
    ip addr del 192.168.137.200/24 dev eth0 2>/dev/null || true
    
    print_success "Setup complete! You can now run:"
    print_status "  sudo ./scripts/network_setup.sh"
    print_status "  sudo ./scripts/wifi_config.sh"
    
else
    print_error "Cannot reach internet. Please check:"
    print_error "1. Computer internet sharing is enabled"
    print_error "2. Ethernet cable is connected"
    print_error "3. Computer Ethernet adapter is set to 192.168.137.1"
    print_error "4. Computer is sharing internet through the Ethernet adapter"
    
    print_status "Current network configuration:"
    print_status "IP: $(ip addr show eth0 | grep 'inet ' | awk '{print $2}' || echo 'None')"
    print_status "Gateway: $(ip route | grep default | awk '{print $3}' || echo 'None')"
    print_status "DNS: $(cat /etc/resolv.conf | grep nameserver | head -1 | awk '{print $2}' || echo 'None')"
    
    exit 1
fi