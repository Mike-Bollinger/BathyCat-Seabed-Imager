#!/bin/bash

# BathyImager WiFi Configuration Helper
# Interactive script to configure WiFi networks
# Usage: sudo ./wifi_config.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration file path
WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
WPA_CONF_BAK="/etc/wpa_supplicant/wpa_supplicant.conf.bak"

# Function to print colored output
print_header() { echo -e "${BOLD}${BLUE}=== $1 ===${NC}"; }
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

# Function to backup configuration
backup_config() {
    if [[ -f "$WPA_CONF" ]]; then
        cp "$WPA_CONF" "$WPA_CONF_BAK"
        print_success "Configuration backed up"
    fi
}

# Function to scan for WiFi networks
scan_networks() {
    print_status "Scanning for WiFi networks..."
    
    # Bring up the interface if needed
    if ! ip link show wlan0 | grep -q "state UP"; then
        ip link set wlan0 up
        sleep 2
    fi
    
    # Scan for networks
    if command -v iwlist >/dev/null 2>&1; then
        local networks=$(iwlist wlan0 scan 2>/dev/null | grep -E "ESSID|Quality|Encryption" | grep -B1 -A1 "ESSID")
        if [[ -n "$networks" ]]; then
            echo "Available networks:"
            iwlist wlan0 scan 2>/dev/null | grep "ESSID" | grep -v '""' | sed 's/.*ESSID:"\(.*\)"/  \1/' | sort -u
        else
            print_warning "No networks found or WiFi adapter not working"
        fi
    else
        print_warning "iwlist not available - install wireless-tools package"
    fi
}

# Function to get network security type
get_security_type() {
    local ssid="$1"
    
    if iwlist wlan0 scan 2>/dev/null | grep -A20 "ESSID:\"$ssid\"" | grep -q "WPA2"; then
        echo "WPA2"
    elif iwlist wlan0 scan 2>/dev/null | grep -A20 "ESSID:\"$ssid\"" | grep -q "WPA"; then
        echo "WPA"
    elif iwlist wlan0 scan 2>/dev/null | grep -A20 "ESSID:\"$ssid\"" | grep -q "WEP"; then
        echo "WEP"
    else
        echo "OPEN"
    fi
}

# Function to add a new network
add_network() {
    print_header "ADD NEW WIFI NETWORK"
    
    # Show available networks
    scan_networks
    echo ""
    
    # Get network details from user
    read -p "Enter WiFi network name (SSID): " ssid
    
    if [[ -z "$ssid" ]]; then
        print_error "SSID cannot be empty"
        return 1
    fi
    
    # Detect security type
    local security=$(get_security_type "$ssid")
    print_status "Detected security: $security"
    
    local password=""
    if [[ "$security" != "OPEN" ]]; then
        read -s -p "Enter WiFi password: " password
        echo ""
        
        if [[ -z "$password" ]]; then
            print_error "Password cannot be empty for secured networks"
            return 1
        fi
    fi
    
    # Get priority
    read -p "Enter network priority (1-10, higher = preferred): " priority
    priority=${priority:-5}
    
    # Validate priority
    if ! [[ "$priority" =~ ^[0-9]+$ ]] || [ "$priority" -lt 1 ] || [ "$priority" -gt 10 ]; then
        priority=5
        print_warning "Invalid priority, using default: 5"
    fi
    
    # Create network configuration
    local network_config=""
    
    if [[ "$security" == "OPEN" ]]; then
        network_config="network={
    ssid=\"$ssid\"
    key_mgmt=NONE
    priority=$priority
    id_str=\"added_$(date +%s)\"
}"
    else
        # Generate PSK for better security
        local psk=$(wpa_passphrase "$ssid" "$password" | grep -E "^\s*psk=" | cut -d'=' -f2)
        
        network_config="network={
    ssid=\"$ssid\"
    psk=$psk
    priority=$priority
    id_str=\"added_$(date +%s)\"
    
    # Security settings for WPA2/WPA3
    proto=RSN WPA
    key_mgmt=WPA-PSK
    pairwise=CCMP TKIP
    group=CCMP TKIP
}"
    fi
    
    # Add to configuration file
    echo "" >> "$WPA_CONF"
    echo "# Added $(date)" >> "$WPA_CONF"
    echo "$network_config" >> "$WPA_CONF"
    
    print_success "Network '$ssid' added with priority $priority"
    
    # Restart wpa_supplicant to apply changes
    print_status "Restarting WiFi service..."
    systemctl restart wpa_supplicant@wlan0
    sleep 3
    
    # Test connection
    print_status "Testing connection to '$ssid'..."
    if timeout 15 wpa_cli -i wlan0 reconfigure >/dev/null 2>&1; then
        sleep 5
        if wpa_cli -i wlan0 status | grep -q "wpa_state=COMPLETED"; then
            local connected_ssid=$(wpa_cli -i wlan0 status | grep "ssid=" | cut -d'=' -f2)
            if [[ "$connected_ssid" == "$ssid" ]]; then
                print_success "Successfully connected to '$ssid'"
            else
                print_warning "Connected to '$connected_ssid' instead of '$ssid'"
            fi
        else
            print_warning "Failed to connect to '$ssid' - check password and signal strength"
        fi
    else
        print_error "Failed to apply WiFi configuration"
    fi
}

# Function to list configured networks
list_networks() {
    print_header "CONFIGURED WIFI NETWORKS"
    
    if [[ ! -f "$WPA_CONF" ]]; then
        print_error "No configuration file found"
        return 1
    fi
    
    echo "Networks in configuration:"
    grep -E "ssid=|priority=" "$WPA_CONF" | paste - - | while IFS=$'\t' read -r ssid_line priority_line; do
        local ssid=$(echo "$ssid_line" | sed 's/.*ssid="\?\([^"]*\)"\?.*/\1/')
        local priority=$(echo "$priority_line" | sed 's/.*priority=\([0-9]*\).*/\1/')
        priority=${priority:-"auto"}
        echo "  $ssid (priority: $priority)"
    done
    
    echo ""
    print_status "Current connection status:"
    if command -v wpa_cli >/dev/null 2>&1; then
        local status=$(wpa_cli -i wlan0 status 2>/dev/null)
        if echo "$status" | grep -q "wpa_state=COMPLETED"; then
            local current_ssid=$(echo "$status" | grep "ssid=" | cut -d'=' -f2)
            local ip_addr=$(ip addr show wlan0 | grep -o "inet [0-9./]*" | cut -d' ' -f2)
            print_success "Connected to: $current_ssid ($ip_addr)"
        else
            print_warning "Not connected to any network"
        fi
    fi
}

# Function to remove a network
remove_network() {
    print_header "REMOVE WIFI NETWORK"
    
    list_networks
    echo ""
    
    read -p "Enter SSID to remove: " ssid_to_remove
    
    if [[ -z "$ssid_to_remove" ]]; then
        print_error "SSID cannot be empty"
        return 1
    fi
    
    # Check if network exists
    if ! grep -q "ssid=\"$ssid_to_remove\"" "$WPA_CONF"; then
        print_error "Network '$ssid_to_remove' not found in configuration"
        return 1
    fi
    
    # Create temporary file without the network
    local temp_file=$(mktemp)
    local in_network=false
    local brace_count=0
    local removed=false
    
    while IFS= read -r line; do
        if [[ "$line" =~ ssid=\"$ssid_to_remove\" ]]; then
            in_network=true
            # Find the opening brace of this network block
            local temp_line_num=$(grep -n "ssid=\"$ssid_to_remove\"" "$WPA_CONF" | cut -d':' -f1)
            # Find the preceding "network={" line
            continue
        fi
        
        if [[ "$in_network" == true ]]; then
            if [[ "$line" =~ ^[[:space:]]*network[[:space:]]*=\{ ]]; then
                brace_count=1
                continue
            elif [[ "$line" == *"{"* ]]; then
                ((brace_count++))
                continue
            elif [[ "$line" == *"}"* ]]; then
                ((brace_count--))
                if [[ "$brace_count" -eq 0 ]]; then
                    in_network=false
                    removed=true
                    continue
                fi
                continue
            else
                continue
            fi
        fi
        
        echo "$line" >> "$temp_file"
    done < "$WPA_CONF"
    
    if [[ "$removed" == true ]]; then
        mv "$temp_file" "$WPA_CONF"
        print_success "Network '$ssid_to_remove' removed"
        
        # Restart wpa_supplicant
        print_status "Restarting WiFi service..."
        systemctl restart wpa_supplicant@wlan0
    else
        rm "$temp_file"
        print_error "Failed to remove network '$ssid_to_remove'"
    fi
}

# Function to test current connection
test_connection() {
    print_header "WIFI CONNECTION TEST"
    
    # Check interface status
    if ! ip link show wlan0 | grep -q "state UP"; then
        print_error "WiFi interface is down"
        return 1
    fi
    
    # Check wpa_supplicant status
    if ! systemctl is-active wpa_supplicant@wlan0 >/dev/null 2>&1; then
        print_warning "wpa_supplicant service is not running"
        print_status "Starting wpa_supplicant..."
        systemctl start wpa_supplicant@wlan0
        sleep 3
    fi
    
    # Get connection status
    local status=$(wpa_cli -i wlan0 status 2>/dev/null)
    if echo "$status" | grep -q "wpa_state=COMPLETED"; then
        local ssid=$(echo "$status" | grep "ssid=" | cut -d'=' -f2)
        local bssid=$(echo "$status" | grep "bssid=" | cut -d'=' -f2)
        local freq=$(echo "$status" | grep "freq=" | cut -d'=' -f2)
        
        print_success "Connected to: $ssid"
        echo "  BSSID: $bssid"
        echo "  Frequency: ${freq}MHz"
        
        # Signal strength
        if command -v iwconfig >/dev/null 2>&1; then
            local signal=$(iwconfig wlan0 2>/dev/null | grep -o "Signal level=[0-9-]* dBm" | cut -d'=' -f2)
            if [[ -n "$signal" ]]; then
                echo "  Signal: $signal"
            fi
        fi
        
        # IP address
        local ip_addr=$(ip addr show wlan0 | grep -o "inet [0-9./]*" | cut -d' ' -f2)
        if [[ -n "$ip_addr" ]]; then
            echo "  IP Address: $ip_addr"
        fi
        
        # Test internet connectivity
        print_status "Testing internet connectivity..."
        if ping -c 3 -W 3 8.8.8.8 >/dev/null 2>&1; then
            print_success "Internet connectivity working"
        else
            print_error "No internet connectivity"
        fi
        
    else
        local state=$(echo "$status" | grep "wpa_state=" | cut -d'=' -f2)
        print_error "Not connected - state: $state"
        
        # Show scan results
        print_status "Available networks:"
        wpa_cli -i wlan0 scan >/dev/null 2>&1
        sleep 2
        wpa_cli -i wlan0 scan_results 2>/dev/null | tail -n +2 | while read -r line; do
            local network_ssid=$(echo "$line" | awk '{print $5}')
            local signal=$(echo "$line" | awk '{print $3}')
            if [[ -n "$network_ssid" && "$network_ssid" != "" ]]; then
                echo "  $network_ssid ($signal dBm)"
            fi
        done
    fi
}

# Function to show configuration file
show_config() {
    print_header "CURRENT WIFI CONFIGURATION"
    
    if [[ -f "$WPA_CONF" ]]; then
        print_status "Configuration file: $WPA_CONF"
        echo ""
        cat "$WPA_CONF"
    else
        print_error "No configuration file found"
    fi
}

# Function to show main menu
show_menu() {
    cat << EOF

${BOLD}${BLUE}BathyImager WiFi Configuration Menu${NC}

1) Scan for networks
2) Add new network
3) List configured networks  
4) Remove network
5) Test current connection
6) Show configuration file
7) Restart WiFi service
0) Exit

EOF
}

# Function to restart WiFi service
restart_service() {
    print_status "Restarting WiFi services..."
    
    systemctl restart wpa_supplicant@wlan0
    systemctl restart dhcpcd
    
    sleep 5
    
    print_success "WiFi services restarted"
    test_connection
}

# Main menu loop
main_menu() {
    while true; do
        show_menu
        read -p "Select option [0-7]: " choice
        
        case $choice in
            1)
                scan_networks
                read -p "Press Enter to continue..."
                ;;
            2)
                add_network
                read -p "Press Enter to continue..."
                ;;
            3)
                list_networks
                read -p "Press Enter to continue..."
                ;;
            4)
                remove_network
                read -p "Press Enter to continue..."
                ;;
            5)
                test_connection
                read -p "Press Enter to continue..."
                ;;
            6)
                show_config
                read -p "Press Enter to continue..."
                ;;
            7)
                restart_service
                read -p "Press Enter to continue..."
                ;;
            0)
                print_success "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        clear
    done
}

# Main function
main() {
    check_root
    backup_config
    
    clear
    print_header "BathyImager WiFi Configuration Helper"
    print_status "WiFi configuration file: $WPA_CONF"
    
    # Quick status check
    if systemctl is-active wpa_supplicant@wlan0 >/dev/null 2>&1; then
        print_success "WiFi service is running"
    else
        print_warning "WiFi service is not running"
    fi
    
    main_menu
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi