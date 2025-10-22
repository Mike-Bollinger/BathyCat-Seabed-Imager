#!/bin/bash

# BathyImager Network Test Script  
# Tests network connectivity scenarios for dual Ethernet + WiFi setup
# Usage: ./network_test.sh [--interface eth0|wlan0] [--continuous]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default settings
TEST_INTERFACE=""
CONTINUOUS_MODE=false
TEST_COUNT=5
TIMEOUT=5

# Function to print colored output
print_header() { echo -e "${BOLD}${BLUE}=== $1 ===${NC}"; }
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to show usage
show_usage() {
    cat << EOF
BathyImager Network Test Script

USAGE:
    ./network_test.sh [OPTIONS]

OPTIONS:
    --interface IFACE    Test specific interface (eth0, wlan0)
    --continuous        Run continuous monitoring
    --count N           Number of ping tests (default: 5)
    --timeout N         Timeout per test (default: 5s)
    --help              Show this help

EXAMPLES:
    ./network_test.sh                          # Test all interfaces
    ./network_test.sh --interface eth0         # Test only Ethernet
    ./network_test.sh --continuous             # Continuous monitoring
    ./network_test.sh --count 10 --timeout 3  # Custom test parameters

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interface)
                TEST_INTERFACE="$2"
                shift 2
                ;;
            --continuous)
                CONTINUOUS_MODE=true
                shift
                ;;
            --count)
                TEST_COUNT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to test ping via specific interface
test_ping_interface() {
    local interface=$1
    local target=$2
    local description=$3
    local count=${4:-3}
    
    if ! ip link show "$interface" >/dev/null 2>&1; then
        print_error "$interface: Interface not found"
        return 1
    fi
    
    if ! ip link show "$interface" | grep -q "state UP"; then
        print_warning "$interface: Interface is DOWN"
        return 1
    fi
    
    local ip_addr=$(ip addr show "$interface" | grep -o "inet [0-9./]*" | head -1 | cut -d' ' -f2 | cut -d'/' -f1)
    if [[ -z "$ip_addr" ]]; then
        print_warning "$interface: No IP address assigned"
        return 1
    fi
    
    print_status "Testing $description via $interface ($ip_addr)..."
    
    # Use ping with source interface
    if ping -I "$interface" -c "$count" -W "$TIMEOUT" "$target" >/dev/null 2>&1; then
        # Get detailed stats
        local stats=$(ping -I "$interface" -c "$count" -W "$TIMEOUT" "$target" 2>&1 | tail -1)
        print_success "$description via $interface: Success - $stats"
        return 0
    else
        print_error "$description via $interface: Failed"
        return 1
    fi
}

# Function to test routing preferences
test_routing_priority() {
    print_header "ROUTING PRIORITY TEST"
    
    print_status "Current routing table:"
    ip route show | grep "default" | while read -r route; do
        echo "  $route"
    done
    echo ""
    
    # Test which interface is actually used for internet traffic
    print_status "Testing actual route taken..."
    
    if command -v traceroute >/dev/null 2>&1; then
        print_status "Traceroute to 8.8.8.8 (first 3 hops):"
        timeout 10 traceroute -n -m 3 8.8.8.8 2>/dev/null | head -5 | tail -3 | while read -r line; do
            echo "  $line"
        done
    fi
    
    # Check which interface has the lowest metric
    local eth_metric=$(ip route show | grep "default.*eth0" | grep -o "metric [0-9]*" | cut -d' ' -f2)
    local wifi_metric=$(ip route show | grep "default.*wlan0" | grep -o "metric [0-9]*" | cut -d' ' -f2)
    
    echo ""
    echo "Interface priorities (lower metric = higher priority):"
    [[ -n "$eth_metric" ]] && echo "  eth0: metric $eth_metric"
    [[ -n "$wifi_metric" ]] && echo "  wlan0: metric $wifi_metric"
    
    if [[ -n "$eth_metric" ]] && [[ -n "$wifi_metric" ]]; then
        if (( eth_metric < wifi_metric )); then
            print_success "Ethernet correctly has higher priority than WiFi"
        else
            print_warning "WiFi has higher priority than Ethernet"
        fi
    fi
}

# Function to test bandwidth
test_bandwidth() {
    local interface=$1
    
    if ! command -v iperf3 >/dev/null 2>&1; then
        print_warning "iperf3 not available - install with: sudo apt install iperf3"
        return 1
    fi
    
    print_status "Testing bandwidth via $interface..."
    print_status "Note: This requires an iperf3 server for accurate testing"
    
    # Simple download test using curl if available
    if command -v curl >/dev/null 2>&1; then
        local ip_addr=$(ip addr show "$interface" | grep -o "inet [0-9./]*" | head -1 | cut -d' ' -f2 | cut -d'/' -f1)
        if [[ -n "$ip_addr" ]]; then
            print_status "Testing download speed via $interface..."
            # Test with a small file from a reliable source
            timeout 10 curl -s --interface "$ip_addr" -o /dev/null -w "Speed: %{speed_download} bytes/sec\n" \
                "http://speedtest.ftp.otenet.gr/files/test100k.db" 2>/dev/null || \
                print_warning "Bandwidth test failed for $interface"
        fi
    fi
}

# Function to test DNS resolution
test_dns() {
    local interface=$1
    
    print_status "Testing DNS resolution via $interface..."
    
    local ip_addr=$(ip addr show "$interface" | grep -o "inet [0-9./]*" | head -1 | cut -d' ' -f2 | cut -d'/' -f1)
    if [[ -z "$ip_addr" ]]; then
        print_warning "$interface: No IP address for DNS test"
        return 1
    fi
    
    # Test DNS resolution
    if command -v nslookup >/dev/null 2>&1; then
        local result=$(timeout 5 nslookup google.com 2>/dev/null | grep -A1 "Non-authoritative answer")
        if [[ -n "$result" ]]; then
            print_success "DNS resolution via $interface: Working"
        else
            print_error "DNS resolution via $interface: Failed"
        fi
    fi
}

# Function to test interface failover
test_failover() {
    print_header "FAILOVER SIMULATION TEST"
    
    # Check both interfaces are available
    local eth_up=false
    local wifi_up=false
    
    if ip link show eth0 2>/dev/null | grep -q "state UP" && ip addr show eth0 | grep -q "inet "; then
        eth_up=true
    fi
    
    if ip link show wlan0 2>/dev/null | grep -q "state UP" && ip addr show wlan0 | grep -q "inet "; then
        wifi_up=true
    fi
    
    if [[ "$eth_up" = true ]] && [[ "$wifi_up" = true ]]; then
        print_status "Both interfaces are up - testing failover behavior"
        
        print_status "Current primary route:"
        ip route show | grep "default" | head -1
        
        print_warning "To test failover manually:"
        echo "  1. Disconnect Ethernet cable"
        echo "  2. Run: ./network_test.sh --interface wlan0"
        echo "  3. Reconnect Ethernet"
        echo "  4. Run: ./network_test.sh"
        
    else
        print_warning "Failover test requires both Ethernet and WiFi to be connected"
        echo "  Ethernet: $([ "$eth_up" = true ] && echo "UP" || echo "DOWN")"
        echo "  WiFi:     $([ "$wifi_up" = true ] && echo "UP" || echo "DOWN")"
    fi
}

# Function to run comprehensive tests
run_comprehensive_test() {
    local interface=$1
    
    print_header "TESTING INTERFACE: $interface"
    
    # Basic connectivity tests
    print_status "Basic connectivity tests:"
    test_ping_interface "$interface" "8.8.8.8" "Google DNS" 3
    test_ping_interface "$interface" "1.1.1.1" "Cloudflare DNS" 3
    test_ping_interface "$interface" "google.com" "Google.com" 3
    
    echo ""
    
    # DNS test
    test_dns "$interface"
    
    echo ""
    
    # Bandwidth test (optional)
    if [[ "$CONTINUOUS_MODE" = false ]]; then
        test_bandwidth "$interface"
    fi
    
    echo ""
}

# Function to monitor connectivity continuously  
monitor_continuous() {
    print_header "CONTINUOUS NETWORK MONITORING"
    print_status "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        echo -n "[$timestamp] "
        
        # Test primary connection
        if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
            local route=$(ip route get 8.8.8.8 2>/dev/null | head -1)
            local interface=$(echo "$route" | grep -o "dev [a-z0-9]*" | cut -d' ' -f2)
            print_success "Internet OK via $interface"
        else
            print_error "Internet FAILED"
        fi
        
        sleep 5
    done
}

# Main test function
main() {
    parse_args "$@"
    
    echo -e "${BOLD}${BLUE}BathyImager Network Test Suite${NC}"
    echo -e "${BLUE}Started: $(date)${NC}"
    echo ""
    
    # Continuous monitoring mode
    if [[ "$CONTINUOUS_MODE" = true ]]; then
        monitor_continuous
        return
    fi
    
    # Test specific interface
    if [[ -n "$TEST_INTERFACE" ]]; then
        run_comprehensive_test "$TEST_INTERFACE"
        return
    fi
    
    # Test all interfaces
    for interface in eth0 wlan0; do
        if ip link show "$interface" >/dev/null 2>&1; then
            run_comprehensive_test "$interface"
        else
            print_warning "Interface $interface not found"
        fi
    done
    
    # Routing priority test
    test_routing_priority
    echo ""
    
    # Failover test
    test_failover
    echo ""
    
    # Summary
    print_header "TEST SUMMARY"
    
    local eth_ok=false
    local wifi_ok=false
    
    # Quick connectivity check
    if ip link show eth0 2>/dev/null | grep -q "state UP" && ping -I eth0 -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        eth_ok=true
    fi
    
    if ip link show wlan0 2>/dev/null | grep -q "state UP" && ping -I wlan0 -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        wifi_ok=true
    fi
    
    echo "Interface Status:"
    echo "  Ethernet: $([ "$eth_ok" = true ] && echo "✅ Working" || echo "❌ Failed")"
    echo "  WiFi:     $([ "$wifi_ok" = true ] && echo "✅ Working" || echo "❌ Failed")"
    
    if [[ "$eth_ok" = true ]] && [[ "$wifi_ok" = true ]]; then
        print_success "Dual connectivity is working properly"
    elif [[ "$eth_ok" = true ]]; then
        print_warning "Only Ethernet is working"
    elif [[ "$wifi_ok" = true ]]; then
        print_warning "Only WiFi is working"
    else
        print_error "No working network connections"
    fi
    
    echo ""
    print_status "Use --continuous for real-time monitoring"
    print_status "Use --interface <name> to test specific interface"
}

# Trap Ctrl+C for clean exit
trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi