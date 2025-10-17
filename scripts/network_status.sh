#!/bin/bash

# BathyImager Network Status Script
# Shows current network configuration and connectivity status
# Usage: ./network_status.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() { echo -e "${BOLD}${BLUE}=== $1 ===${NC}"; }
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check interface status
check_interface() {
    local interface=$1
    local name=$2
    
    if ip link show "$interface" >/dev/null 2>&1; then
        local state=$(ip link show "$interface" | grep -o "state [A-Z]*" | cut -d' ' -f2)
        local ip_addr=$(ip addr show "$interface" | grep -o "inet [0-9./]*" | cut -d' ' -f2)
        
        echo -n "  $name ($interface): "
        
        if [[ "$state" == "UP" ]]; then
            if [[ -n "$ip_addr" ]]; then
                print_success "UP - IP: $ip_addr"
            else
                print_warning "UP - No IP address"
            fi
        else
            print_error "DOWN"
        fi
    else
        print_error "$name ($interface): Interface not found"
    fi
}

# Function to check WiFi connection
check_wifi_connection() {
    if command -v wpa_cli >/dev/null 2>&1; then
        local status=$(wpa_cli -i wlan0 status 2>/dev/null)
        if echo "$status" | grep -q "wpa_state=COMPLETED"; then
            local ssid=$(echo "$status" | grep "ssid=" | cut -d'=' -f2)
            local freq=$(echo "$status" | grep "freq=" | cut -d'=' -f2)
            print_success "Connected to: $ssid (${freq}MHz)"
            
            # Signal strength
            if command -v iwconfig >/dev/null 2>&1; then
                local signal=$(iwconfig wlan0 2>/dev/null | grep -o "Signal level=[0-9-]* dBm" | cut -d'=' -f2)
                if [[ -n "$signal" ]]; then
                    echo "    Signal strength: $signal"
                fi
            fi
        else
            local state=$(echo "$status" | grep "wpa_state=" | cut -d'=' -f2)
            print_warning "WiFi state: $state"
        fi
    else
        print_warning "wpa_cli not available"
    fi
}

# Function to test connectivity
test_connectivity() {
    local target=$1
    local name=$2
    
    if ping -c 2 -W 3 "$target" >/dev/null 2>&1; then
        print_success "$name: Reachable"
    else
        print_error "$name: Unreachable"
    fi
}

# Function to show routing table
show_routing() {
    print_header "ROUTING TABLE"
    
    echo "Default routes (priority order):"
    ip route show | grep "default" | while read -r route; do
        local interface=$(echo "$route" | grep -o "dev [a-z0-9]*" | cut -d' ' -f2)
        local gateway=$(echo "$route" | grep -o "via [0-9.]*" | cut -d' ' -f2)
        local metric=$(echo "$route" | grep -o "metric [0-9]*" | cut -d' ' -f2)
        echo "  -> $interface via $gateway (metric: ${metric:-auto})"
    done
    
    echo ""
    echo "All routes:"
    ip route show | head -10
}

# Function to show DNS configuration
show_dns() {
    print_header "DNS CONFIGURATION"
    
    if [[ -f /etc/resolv.conf ]]; then
        echo "DNS servers:"
        grep "nameserver" /etc/resolv.conf | while read -r line; do
            echo "  $line"
        done
        
        echo ""
        echo "Search domains:"
        grep -E "^(search|domain)" /etc/resolv.conf | head -5
    else
        print_warning "No /etc/resolv.conf found"
    fi
}

# Function to show service status
show_services() {
    print_header "NETWORK SERVICES"
    
    # Check dhcpcd
    if systemctl is-active dhcpcd >/dev/null 2>&1; then
        print_success "dhcpcd: Active"
    else
        print_error "dhcpcd: Inactive"
    fi
    
    # Check wpa_supplicant
    if systemctl is-active wpa_supplicant@wlan0 >/dev/null 2>&1; then
        print_success "wpa_supplicant@wlan0: Active"
    else
        print_warning "wpa_supplicant@wlan0: Inactive"
    fi
    
    # Check NetworkManager (if present)
    if systemctl is-active NetworkManager >/dev/null 2>&1; then
        print_warning "NetworkManager: Active (may conflict with dhcpcd)"
    fi
}

# Function to show interface statistics
show_interface_stats() {
    print_header "INTERFACE STATISTICS"
    
    for interface in eth0 wlan0; do
        if ip link show "$interface" >/dev/null 2>&1; then
            echo "$interface statistics:"
            # RX/TX packets and bytes
            local rx_packets=$(cat "/sys/class/net/$interface/statistics/rx_packets" 2>/dev/null || echo "N/A")
            local tx_packets=$(cat "/sys/class/net/$interface/statistics/tx_packets" 2>/dev/null || echo "N/A")
            local rx_bytes=$(cat "/sys/class/net/$interface/statistics/rx_bytes" 2>/dev/null || echo "N/A")
            local tx_bytes=$(cat "/sys/class/net/$interface/statistics/tx_bytes" 2>/dev/null || echo "N/A")
            
            echo "  RX: $rx_packets packets, $rx_bytes bytes"
            echo "  TX: $tx_packets packets, $tx_bytes bytes"
            echo ""
        fi
    done
}

# Function to show quick diagnostics
show_diagnostics() {
    print_header "QUICK DIAGNOSTICS"
    
    # Check for common issues
    if ! systemctl is-active dhcpcd >/dev/null 2>&1; then
        print_error "dhcpcd service is not running"
        echo "  Fix: sudo systemctl start dhcpcd"
    fi
    
    if ip route show | grep -q "default.*metric 100"; then
        print_success "Ethernet has priority routing configured"
    else
        print_warning "Ethernet priority routing may not be configured"
    fi
    
    if ip route show | grep -q "default.*wlan0"; then
        if ip route show | grep -q "default.*eth0"; then
            print_success "Both Ethernet and WiFi have routing configured"
        else
            print_warning "Only WiFi routing configured"
        fi
    fi
    
    # Check for conflicting services
    if systemctl is-active NetworkManager >/dev/null 2>&1; then
        print_warning "NetworkManager is active - may conflict with dhcpcd"
        echo "  Consider: sudo systemctl disable NetworkManager"
    fi
}

# Function to show summary
show_summary() {
    print_header "CONNECTION SUMMARY"
    
    local eth_up=false
    local wifi_up=false
    local internet=false
    
    # Check Ethernet
    if ip link show eth0 2>/dev/null | grep -q "state UP" && ip addr show eth0 | grep -q "inet "; then
        eth_up=true
    fi
    
    # Check WiFi  
    if ip link show wlan0 2>/dev/null | grep -q "state UP" && ip addr show wlan0 | grep -q "inet "; then
        wifi_up=true
    fi
    
    # Check internet
    if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        internet=true
    fi
    
    echo "Status Summary:"
    echo "  Ethernet: $([ "$eth_up" = true ] && echo "✅ Connected" || echo "❌ Not connected")"
    echo "  WiFi:     $([ "$wifi_up" = true ] && echo "✅ Connected" || echo "❌ Not connected")"
    echo "  Internet: $([ "$internet" = true ] && echo "✅ Available" || echo "❌ Not available")"
    
    # Recommendations
    echo ""
    echo "Recommendations:"
    if [ "$eth_up" = true ] && [ "$wifi_up" = true ]; then
        print_success "Dual connectivity active - traffic will prefer Ethernet"
    elif [ "$eth_up" = true ]; then
        echo "  Only Ethernet connected - WiFi backup available if configured"
    elif [ "$wifi_up" = true ]; then
        echo "  Only WiFi connected - consider connecting Ethernet for primary connection"
    else
        print_error "No network connections active"
    fi
}

# Main function
main() {
    clear
    echo -e "${BOLD}${BLUE}BathyImager Network Status Report${NC}"
    echo -e "${BLUE}Generated: $(date)${NC}"
    echo ""
    
    # Network interfaces
    print_header "NETWORK INTERFACES"
    check_interface "eth0" "Ethernet"
    check_interface "wlan0" "WiFi"
    echo ""
    
    # WiFi specific info
    print_header "WIFI CONNECTION"
    check_wifi_connection
    echo ""
    
    # Services
    show_services
    echo ""
    
    # Routing
    show_routing
    echo ""
    
    # DNS
    show_dns
    echo ""
    
    # Connectivity tests
    print_header "CONNECTIVITY TESTS"
    test_connectivity "8.8.8.8" "Google DNS"
    test_connectivity "1.1.1.1" "Cloudflare DNS"
    test_connectivity "google.com" "Google.com"
    echo ""
    
    # Interface statistics
    show_interface_stats
    
    # Diagnostics
    show_diagnostics
    echo ""
    
    # Summary
    show_summary
    
    echo ""
    echo -e "${BLUE}For detailed logs: journalctl -u dhcpcd -u wpa_supplicant@wlan0${NC}"
    echo -e "${BLUE}For live monitoring: watch -n 2 ./network_status.sh${NC}"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi