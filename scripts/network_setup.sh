#!/bin/bash

# BathyImager Network Setup Script
# Configures dual Ethernet + WiFi connectivity for Raspberry Pi
# Usage: sudo ./network_setup.sh [--offline]

set -e

# Command line options
OFFLINE_MODE=false

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
    
    BACKUP_DIR="/etc/bathyimager-network-backup-$(date +%Y%m%d-%H%M%S)"
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
    if [[ "$OFFLINE_MODE" == "true" ]]; then
        print_warning "Skipping package installation (offline mode)"
        print_status "Required packages: dhcpcd5, wpasupplicant, wireless-tools, net-tools, iproute2"
        print_status "Install these manually when online: sudo apt update && sudo apt install -y dhcpcd5 wpasupplicant wireless-tools net-tools iproute2"
        return 0
    fi
    
    print_status "Installing required networking packages..."
    
    if ! command -v apt >/dev/null 2>&1; then
        print_error "apt package manager not found"
        exit 1
    fi
    
    # Check if we can reach package repositories
    if ! apt update >/dev/null 2>&1; then
        print_error "Cannot reach package repositories. Use --offline flag or check internet connectivity"
        exit 1
    fi
    
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
    if [[ "$OFFLINE_MODE" == "true" ]]; then
        print_warning "Skipping service enablement (offline mode)"
        print_status "Enable services manually when packages are installed:"
        print_status "  sudo systemctl enable dhcpcd"
        print_status "  sudo systemctl enable wpa_supplicant@wlan0"
        return 0
    fi
    
    print_status "Enabling network services..."
    
    # Check if dhcpcd service exists before enabling
    if systemctl list-unit-files dhcpcd.service >/dev/null 2>&1; then
        systemctl enable dhcpcd
        print_success "dhcpcd service enabled"
    else
        print_warning "dhcpcd service not found (may need to install dhcpcd5 package)"
    fi
    
    # Check if wpa_supplicant service exists before enabling
    if systemctl list-unit-files wpa_supplicant@.service >/dev/null 2>&1; then
        systemctl enable wpa_supplicant@wlan0
        print_success "wpa_supplicant@wlan0 service enabled"
    else
        print_warning "wpa_supplicant service not found (may need to install wpasupplicant package)"
    fi
    
    print_success "Network services configuration complete"
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
    if [[ "$OFFLINE_MODE" == "true" ]]; then
        print_warning "Skipping network testing (offline mode)"
        print_status "Test network manually after installing packages and restarting services"
        return 0
    fi
    
    print_status "Testing network configuration..."
    
    # Restart networking services (only if they exist)
    print_status "Restarting network services..."
    
    if systemctl is-active --quiet dhcpcd; then
        systemctl restart dhcpcd
        print_status "Restarted dhcpcd service"
    elif systemctl list-unit-files dhcpcd.service >/dev/null 2>&1; then
        systemctl restart dhcpcd
        print_status "Restarted dhcpcd service"
    else
        print_warning "dhcpcd service not available - install dhcpcd5 package first"
    fi
    
    if systemctl is-active --quiet wpa_supplicant@wlan0; then
        systemctl restart wpa_supplicant@wlan0
        print_status "Restarted wpa_supplicant@wlan0 service"
    elif systemctl list-unit-files wpa_supplicant@.service >/dev/null 2>&1; then
        systemctl restart wpa_supplicant@wlan0 || true
        print_status "Attempted to restart wpa_supplicant@wlan0 service"
    else
        print_warning "wpa_supplicant service not available - install wpasupplicant package first"
    fi
    
    # Wait for interfaces to come up
    sleep 10
    
    # Check interface status
    print_status "Checking network interfaces..."
    
    if command -v ip >/dev/null && ip link show eth0 >/dev/null 2>&1; then
        if ip link show eth0 | grep -q "state UP"; then
            print_success "Ethernet interface is UP"
        else
            print_warning "Ethernet interface is DOWN"
        fi
    else
        print_warning "Cannot check eth0 status (ip command not available or interface not found)"
    fi
    
    if command -v ip >/dev/null && ip link show wlan0 >/dev/null 2>&1; then
        if ip link show wlan0 | grep -q "state UP"; then
            print_success "WiFi interface is UP"
        else
            print_warning "WiFi interface is DOWN (may need WiFi credentials)"
        fi
    else
        print_warning "Cannot check wlan0 status (ip command not available or interface not found)"
    fi
    
    # Show routing table
    if command -v ip >/dev/null; then
        print_status "Current routing table:"
        ip route list | head -10
    else
        print_warning "ip command not available - install iproute2 package to view routing"
    fi
    
    # Test connectivity
    print_status "Testing connectivity..."
    if command -v ping >/dev/null; then
        if ping -c 2 8.8.8.8 >/dev/null 2>&1; then
            print_success "Internet connectivity confirmed"
        else
            print_warning "No internet connectivity (check network settings)"
        fi
    else
        print_warning "ping command not available - install iputils-ping package to test connectivity"
    fi
}

# Function to show usage information
show_usage() {
    cat << EOF

BathyImager Network Configuration Complete!

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
- Configuration backups are in /etc/bathyimager-network-backup-*

$(if [[ "$OFFLINE_MODE" == "true" ]]; then
    echo ""
    echo "⚠️  OFFLINE MODE - ADDITIONAL STEPS REQUIRED:"
    echo ""
    echo "1. INSTALL PACKAGES (when you get internet access):"
    echo "   sudo apt update"
    echo "   sudo apt install -y dhcpcd5 wpasupplicant wireless-tools net-tools iproute2"
    echo ""
    echo "2. ENABLE SERVICES:"
    echo "   sudo systemctl enable dhcpcd"
    echo "   sudo systemctl enable wpa_supplicant@wlan0"
    echo ""
    echo "3. THEN FOLLOW NORMAL STEPS ABOVE"
    echo ""
fi)

EOF
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --offline)
                OFFLINE_MODE=true
                shift
                ;;
            --help|-h)
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

# Function to show help
show_help() {
    cat << EOF
BathyImager Network Setup Script

USAGE:
    sudo ./network_setup.sh [OPTIONS]

OPTIONS:
    --offline          Skip package installation (for offline setup)
    --help, -h         Show this help message

DESCRIPTION:
    Configures dual Ethernet + WiFi connectivity for Raspberry Pi.
    Sets up automatic failover with Ethernet as primary and WiFi as backup.

EXAMPLES:
    sudo ./network_setup.sh                # Normal setup (requires internet)
    sudo ./network_setup.sh --offline      # Offline setup (skip packages)

EOF
}

# Main installation function
main() {
    parse_arguments "$@"
    
    if [[ "$OFFLINE_MODE" == "true" ]]; then
        print_status "BathyImager Network Setup Starting (OFFLINE MODE)..."
    else
        print_status "BathyImager Network Setup Starting..."
    fi
    
    check_root
    backup_configs
    install_packages
    configure_dhcpcd
    configure_wifi
    configure_interfaces
    enable_services
    test_configuration
    
    print_success "BathyImager Network Setup Complete!"
    show_usage
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi