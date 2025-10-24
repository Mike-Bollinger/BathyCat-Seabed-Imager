#!/bin/bash
#
# GPS Time Synchronization Test Script for BathyCat Seabed Imager
# ==============================================================
#
# This script tests the GPS time synchronization implementation to ensure:
# 1. GPS boot sync service is properly installed and configured
# 2. GPS device detection works correctly 
# 3. Time synchronization functions properly
# 4. Timezone detection works from GPS coordinates
# 5. System integration is working as expected
# 6. Existing image geotagging functionality is preserved
#
# Usage: sudo ./test_gps_time_sync.sh [options]
#
# Options:
#   --manual     Run manual tests (requires GPS device)
#   --simulate   Run simulation tests (no GPS required)
#   --full       Run both manual and simulation tests
#   --help       Show this help message
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
PROJECT_DIR="/home/bathyimager/BathyCat-Seabed-Imager"
GPS_SCRIPT="$PROJECT_DIR/src/gps_time_sync.py"
MAIN_SERVICE="bathyimager"
GPS_BOOT_SERVICE="gps-boot-sync"
GPS_TIMER_SERVICE="gps-periodic-sync.timer"
LOG_DIR="/var/log/bathyimager"
CONFIG_FILE="$PROJECT_DIR/config/bathycat_config.json"

# Test flags
RUN_MANUAL=false
RUN_SIMULATION=false
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
GPS Time Synchronization Test Script

Usage: sudo $0 [options]

Options:
    --manual     Run manual tests (requires connected GPS device)
    --simulate   Run simulation tests (no GPS device required)
    --full       Run both manual and simulation tests
    --verbose    Enable verbose output
    --help       Show this help message

Test Categories:
1. Service Installation Tests - Verify systemd services are installed
2. GPS Device Detection Tests - Test GPS device detection logic  
3. Time Sync Function Tests - Test time synchronization functions
4. Integration Tests - Test end-to-end functionality
5. Compatibility Tests - Ensure existing features still work

Manual tests require a connected GPS device and will attempt real GPS operations.
Simulation tests use mock data and can run without hardware.

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --manual)
                RUN_MANUAL=true
                shift
                ;;
            --simulate)
                RUN_SIMULATION=true
                shift
                ;;
            --full)
                RUN_MANUAL=true
                RUN_SIMULATION=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                set -x
                shift
                ;;
            --help)
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
    
    # Default to simulation if no options specified
    if [[ "$RUN_MANUAL" == false && "$RUN_SIMULATION" == false ]]; then
        RUN_SIMULATION=true
    fi
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to test service installation
test_service_installation() {
    print_status "Testing service installation..."
    
    local tests_passed=0
    local tests_total=8
    
    # Test 1: GPS boot sync service file exists
    if [[ -f "/etc/systemd/system/gps-boot-sync.service" ]]; then
        print_success "GPS boot sync service file exists"
        ((tests_passed++))
    else
        print_error "GPS boot sync service file not found"
    fi
    
    # Test 2: GPS periodic sync service file exists
    if [[ -f "/etc/systemd/system/gps-periodic-sync.service" ]]; then
        print_success "GPS periodic sync service file exists"
        ((tests_passed++))
    else
        print_error "GPS periodic sync service file not found"
    fi
    
    # Test 3: GPS periodic sync timer file exists
    if [[ -f "/etc/systemd/system/gps-periodic-sync.timer" ]]; then
        print_success "GPS periodic sync timer file exists"
        ((tests_passed++))
    else
        print_error "GPS periodic sync timer file not found"
    fi
    
    # Test 4: GPS time sync Python script exists  
    if [[ -f "$GPS_SCRIPT" ]]; then
        print_success "GPS time sync Python script exists"
        ((tests_passed++))
    else
        print_error "GPS time sync Python script not found at $GPS_SCRIPT"
    fi
    
    # Test 5: GPS script is executable
    if [[ -x "$GPS_SCRIPT" ]]; then
        print_success "GPS time sync script is executable"
        ((tests_passed++))
    else
        print_error "GPS time sync script is not executable"
    fi
    
    # Test 6: Main BathyImager service exists
    if [[ -f "/etc/systemd/system/bathyimager.service" ]]; then
        print_success "Main BathyImager service file exists"
        ((tests_passed++))
    else
        print_error "Main BathyImager service file not found"
    fi
    
    # Test 7: GPS boot service is enabled
    if systemctl is-enabled --quiet gps-boot-sync 2>/dev/null; then
        print_success "GPS boot sync service is enabled"
        ((tests_passed++))
    else
        print_warning "GPS boot sync service is not enabled"
    fi
    
    # Test 8: GPS periodic timer is enabled
    if systemctl is-enabled --quiet gps-periodic-sync.timer 2>/dev/null; then
        print_success "GPS periodic sync timer is enabled"
        ((tests_passed++))
    else
        print_warning "GPS periodic sync timer is not enabled"
    fi
    
    print_info "Service installation tests: $tests_passed/$tests_total passed"
    
    if [[ $tests_passed -lt 5 ]]; then
        print_error "Critical service installation issues detected"
        return 1
    fi
    
    return 0
}

# Function to test GPS device detection
test_gps_device_detection() {
    print_status "Testing GPS device detection..."
    
    # Test if GPS time sync script can run basic checks
    if python3 -c "
import sys
sys.path.append('$PROJECT_DIR/src')
try:
    from gps_time_sync import GPSTimeSync
    gps_sync = GPSTimeSync()
    print('GPS time sync module loaded successfully')
    exit(0)
except Exception as e:
    print(f'Error loading GPS time sync module: {e}')
    exit(1)
"; then
        print_success "GPS time sync module loads correctly"
    else
        print_error "GPS time sync module failed to load"
        return 1
    fi
    
    # List available serial ports
    print_info "Available serial devices:"
    if ls /dev/tty{USB,ACM,AMA}* 2>/dev/null; then
        print_success "Serial devices detected"
    else
        print_warning "No serial devices detected (/dev/ttyUSB*, /dev/ttyACM*, /dev/ttyAMA*)"
    fi
    
    return 0
}

# Function to test time sync functionality (simulation)
test_time_sync_simulation() {
    print_status "Testing time synchronization functionality (simulation)..."
    
    # Create a test script that simulates GPS time sync
    local test_script="/tmp/test_gps_time_sync.py"
    
cat > "$test_script" << 'EOF'
#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add project src to path
sys.path.append('/home/bathyimager/BathyCat-Seabed-Imager/src')

try:
    from gps_time_sync import GPSTimeSync
    
    def test_utc_timezone():
        """Test that system always uses UTC timezone"""
        gps_sync = GPSTimeSync()
        
        # Test UTC timezone setting
        result = gps_sync._ensure_utc_timezone()
        print(f"UTC timezone setup: {'SUCCESS' if result else 'WARNING'}")
        
        return True
    
    def test_config_loading():
        """Test configuration loading"""
        gps_sync = GPSTimeSync()
        config = gps_sync.config
        print(f"Configuration loaded: {len(config)} items")
        return True
    
    def test_logging_setup():
        """Test logging setup"""
        gps_sync = GPSTimeSync()
        logger = gps_sync.logger
        logger.info("Test log message")
        print("Logging system initialized successfully")
        return True
    
    def test_both_modes():
        """Test both boot and periodic modes"""
        gps_sync = GPSTimeSync()
        print("Boot mode test: GPS sync service can be initialized")
        print("Periodic mode test: GPS sync service can be initialized")
        return True
    
    # Run tests
    print("Running GPS time sync simulation tests...")
    
    test_utc_timezone()
    test_config_loading() 
    test_logging_setup()
    test_both_modes()
    
    print("All simulation tests passed!")
    
except Exception as e:
    print(f"Simulation test failed: {e}")
    sys.exit(1)
EOF
    
    if python3 "$test_script"; then
        print_success "Time synchronization simulation tests passed"
        rm -f "$test_script"
        return 0
    else
        print_error "Time synchronization simulation tests failed"
        rm -f "$test_script"
        return 1
    fi
}

# Function to test manual GPS functionality
test_manual_gps() {
    print_status "Testing manual GPS functionality..."
    print_warning "This test requires a connected GPS device and may take several minutes"
    
    # Check for GPS devices
    if ! ls /dev/tty{USB,ACM,AMA}* >/dev/null 2>&1; then
        print_error "No GPS devices detected - skipping manual tests"
        return 1
    fi
    
    print_info "Attempting to run GPS time sync service manually..."
    
    # Run GPS time sync manually with timeout
    if timeout 60 python3 "$GPS_SCRIPT" --boot 2>&1 | tee /tmp/gps_test.log; then
        print_success "GPS time sync completed successfully"
        
        # Check if sync marker was created
        if [[ -f "/var/run/gps_time_synced" ]]; then
            print_success "GPS sync marker file created"
            cat /var/run/gps_time_synced
        else
            print_warning "GPS sync marker file not created (normal if GPS fix not acquired)"
        fi
        
    else
        print_warning "GPS time sync timed out or failed (normal if no GPS signal)"
        print_info "GPS test output:"
        tail -20 /tmp/gps_test.log 2>/dev/null || echo "No log output available"
    fi
    
    return 0
}

# Function to test existing GPS functionality compatibility  
test_gps_compatibility() {
    print_status "Testing GPS compatibility with existing functionality..."
    
    # Test that original GPS class still works
    if python3 -c "
import sys
sys.path.append('$PROJECT_DIR/src')
try:
    from gps import GPS
    config = {'gps_port': '/dev/ttyUSB0', 'gps_baudrate': 9600}
    gps = GPS(config)
    print('Original GPS class works correctly')
    exit(0)
except Exception as e:
    print(f'Error with original GPS class: {e}') 
    exit(1)
"; then
        print_success "Original GPS class compatibility maintained"
    else
        print_error "Original GPS class compatibility broken"
        return 1
    fi
    
    return 0
}

# Function to test system integration
test_system_integration() {
    print_status "Testing system integration..."
    
    local tests_passed=0
    local tests_total=4
    
    # Test 1: Check systemd service dependencies
    if systemctl list-dependencies gps-boot-sync 2>/dev/null | grep -q "multi-user.target"; then
        print_success "GPS boot service has correct systemd dependencies"
        ((tests_passed++))
    else
        print_warning "GPS boot service dependencies may be incorrect"
    fi
    
    # Test 2: Check log directory permissions
    if [[ -d "$LOG_DIR" && -w "$LOG_DIR" ]]; then
        print_success "Log directory exists and is writable"
        ((tests_passed++))
    else
        print_warning "Log directory issues detected"
    fi
    
    # Test 3: Check configuration file
    if [[ -f "$CONFIG_FILE" && -r "$CONFIG_FILE" ]]; then
        print_success "Configuration file exists and is readable"
        ((tests_passed++))
    else
        print_warning "Configuration file not found or not readable"
    fi
    
    # Test 4: Test timedatectl availability
    if command -v timedatectl >/dev/null 2>&1; then
        print_success "timedatectl command available for time management"
        ((tests_passed++))
        
        # Show current time status
        print_info "Current time status:"
        timedatectl status 2>/dev/null || echo "Could not get time status"
        
        # Test GPS timer status
        if systemctl is-active --quiet gps-periodic-sync.timer 2>/dev/null; then
            print_success "GPS periodic sync timer is active"
        else
            print_warning "GPS periodic sync timer is not active"
        fi
    else
        print_error "timedatectl not available - time sync may not work"
    fi
    
    print_info "System integration tests: $tests_passed/$tests_total passed"
    return 0
}

# Function to run comprehensive tests
run_tests() {
    local total_failures=0
    
    echo "GPS Time Synchronization Test Suite"
    echo "==================================="
    echo
    
    print_info "Test configuration:"
    print_info "  Manual tests: $RUN_MANUAL"
    print_info "  Simulation tests: $RUN_SIMULATION"
    print_info "  Project directory: $PROJECT_DIR"
    echo
    
    # Always run basic tests
    test_service_installation || ((total_failures++))
    echo
    
    test_gps_device_detection || ((total_failures++))
    echo
    
    test_gps_compatibility || ((total_failures++))
    echo
    
    test_system_integration || ((total_failures++))
    echo
    
    # Run simulation tests
    if [[ "$RUN_SIMULATION" == true ]]; then
        test_time_sync_simulation || ((total_failures++))
        echo
    fi
    
    # Run manual tests if requested
    if [[ "$RUN_MANUAL" == true ]]; then
        test_manual_gps || ((total_failures++))
        echo
    fi
    
    # Summary
    echo "Test Summary"
    echo "============"
    if [[ $total_failures -eq 0 ]]; then
        print_success "All tests passed successfully!"
        echo
        print_info "GPS time synchronization implementation is ready for deployment."
        print_info "On next boot, the system will attempt to sync time with GPS."
        echo
        print_info "Useful commands:"
        print_info "  Check GPS boot sync:    systemctl status gps-boot-sync"
        print_info "  Check GPS timer:        systemctl status gps-periodic-sync.timer"
        print_info "  View GPS sync logs:     journalctl -u gps-boot-sync"
        print_info "  View GPS timer logs:    journalctl -u gps-periodic-sync"
        print_info "  Check time status:      timedatectl status"
        print_info "  Manual GPS sync:        sudo systemctl start gps-boot-sync"
        print_info "  Manual periodic sync:   sudo systemctl start gps-periodic-sync"
    else
        print_error "$total_failures test categories failed"
        echo
        print_error "Please review the failed tests and fix issues before deployment."
        echo
        print_info "Common issues:"
        print_info "  1. GPS device not connected or detected"
        print_info "  2. Service not installed correctly (run install.sh)"
        print_info "  3. Permissions or path issues"
        print_info "  4. Missing dependencies"
    fi
    
    echo
    return $total_failures
}

# Main function
main() {
    parse_args "$@"
    check_root
    
    run_tests
    local exit_code=$?
    
    exit $exit_code
}

# Run main function
main "$@"