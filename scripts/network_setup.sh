#!/bin/bash

# BathyCat Network Setup Script
# Configures dual Ethernet + WiFi connectivity for Raspberry Pi
# Usage: sudo ./network_setup.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")/config"

# Function to print colored output
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to backup existing configuration
backup_configs() {
    print_status "Backing up existing network configurations..."
    
    BACKUP_DIR="/etc/bathycat-network-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup existing configurations
    if [[ -f /etc/dhcpcd.conf ]]; then
        cp /etc/dhcpcd.conf "$BACKUP_DIR/dhcpcd.conf.bak"
        print_success "Backed up dhcpcd.conf"
    fi
    
    if [[ -f /etc/wpa_supplicant/wpa_supplicant.conf ]]; then
        cp /etc/wpa_supplicant/wpa_supplicant.conf "$BACKUP_DIR/wpa_supplicant.conf.bak"
        print_success "Backed up wpa_supplicant.conf"
    fi
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to install required packages
install_packages() {
    print_status "Installing required networking packages..."
    
    apt update
    
    # Install networking tools
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
    
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            print_status "Installing $package..."
            apt install -y "$package"
        else
            print_status "$package is already installed"
        fi
    done
    
    print_success "All networking packages installed"
}

# Function to configure dhcpcd
configure_dhcpcd() {
    print_status "Configuring dhcpcd for dual network support..."
    
    # Check if our config exists
    if [[ ! -f "$CONFIG_DIR/dhcpcd.conf" ]]; then
        print_error "dhcpcd.conf not found in $CONFIG_DIR"
        exit 1
    fi
    
    # Copy our configuration
    cp "$CONFIG_DIR/dhcpcd.conf" /etc/dhcpcd.conf
    chown root:root /etc/dhcpcd.conf
    chmod 644 /etc/dhcpcd.conf
    
    print_success "dhcpcd configuration updated"
}

# Function to configure WiFi
configure_wifi() {
    print_status "Setting up WiFi configuration..."
    
    # Check if our config exists
    if [[ ! -f "$CONFIG_DIR/wpa_supplicant.conf" ]]; then
        print_error "wpa_supplicant.conf not found in $CONFIG_DIR"
        exit 1
    fi
    
    # Ensure directory exists
    mkdir -p /etc/wpa_supplicant
    
    # Copy template (user will need to edit)
    if [[ ! -f /etc/wpa_supplicant/wpa_supplicant.conf ]]; then
        cp "$CONFIG_DIR/wpa_supplicant.conf" /etc/wpa_supplicant/wpa_supplicant.conf
    else
        print_warning "WiFi configuration already exists. Template saved as wpa_supplicant.conf.template"
        cp "$CONFIG_DIR/wpa_supplicant.conf" /etc/wpa_supplicant/wpa_supplicant.conf.template
    fi
    
    chown root:root /etc/wpa_supplicant/wpa_supplicant.conf*
    chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf*
    
    print_success "WiFi configuration template installed"
    print_warning "You must edit /etc/wpa_supplicant/wpa_supplicant.conf with your WiFi credentials"
}

# Function to enable and start services
enable_services() {
    print_status "Enabling network services..."
    
    # Enable dhcpcd
    systemctl enable dhcpcd
    
    # Enable wpa_supplicant
    systemctl enable wpa_supplicant@wlan0
    
    print_success "Network services enabled"
}

# Function to configure interface priorities
configure_interfaces() {
    print_status "Configuring network interface priorities..."
    
    # The priorities are set in dhcpcd.conf:
    # - eth0 (Ethernet): metric 100 (highest priority)
    # - wlan0 (WiFi): metric 300 (lower priority)
    
    print_success "Interface priorities configured via dhcpcd.conf"
}

# Function to test network configuration
test_configuration() {
    print_status "Testing network configuration..."
    
    # Restart networking services
    print_status "Restarting network services..."
    systemctl restart dhcpcd
    systemctl restart wpa_supplicant@wlan0 || true
    
    # Wait for interfaces to come up
    sleep 10
    
    # Check interface status
    print_status "Checking network interfaces..."
    
    if ip link show eth0 | grep -q "state UP"; then
        print_success "Ethernet interface is UP"
    else
        print_warning "Ethernet interface is DOWN"
    fi
    
    if ip link show wlan0 | grep -q "state UP"; then
        print_success "WiFi interface is UP"
    else
        print_warning "WiFi interface is DOWN (may need WiFi credentials)"
    fi
    
    # Show routing table
    print_status "Current routing table:"
    ip route list | head -10
    
    # Test connectivity
    print_status "Testing connectivity..."
    if ping -c 2 8.8.8.8 >/dev/null 2>&1; then
        print_success "Internet connectivity confirmed"
    else
        print_warning "No internet connectivity (check network settings)"
    fi
}

# Function to show usage information
show_usage() {
    cat << EOF

BathyCat Network Configuration Complete!

NEXT STEPS:
1. Edit WiFi credentials:
   sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
   
2. Restart networking:
   sudo systemctl restart dhcpcd
   sudo systemctl restart wpa_supplicant@wlan0
   
3. Check status:
   ./network_status.sh
   
4. Test connections:
   ./network_test.sh

CONFIGURATION:
- Ethernet (eth0): Primary connection, metric 100
- WiFi (wlan0): Secondary connection, metric 300
- Both interfaces can be active simultaneously
- Traffic routes through Ethernet when available, WiFi as fallback

FILES MODIFIED:
- /etc/dhcpcd.conf
- /etc/wpa_supplicant/wpa_supplicant.conf

BACKUP LOCATION:
- Configuration backups are in /etc/bathycat-network-backup-*

EOF
}

# Main installation function
main() {
    print_status "BathyCat Network Setup Starting..."
    
    check_root
    backup_configs
    install_packages
    configure_dhcpcd
    configure_wifi
    configure_interfaces
    enable_services
    test_configuration
    
    print_success "BathyCat Network Setup Complete!"
    show_usage
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi