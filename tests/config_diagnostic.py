#!/usr/bin/env python3
"""
Configuration Diagnostic Script
==============================

This script checks what configuration is actually being loaded by the BathyCat system
and verifies GPS port settings.
"""

import sys
import os
import json
import logging

# Add src directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def main():
    """Run configuration diagnostics."""
    print("BathyCat Configuration Diagnostic")
    print("=" * 40)
    
    # Test 1: Check JSON config file loading
    print("\n1. Testing JSON Config File Loading:")
    
    config_paths = [
        '/etc/bathycat/config.json',
        '/usr/local/etc/bathycat/config.json',
        './config/bathycat_config.json',
        '../config/bathycat_config.json'
    ]
    
    config_found = False
    config_data = None
    actual_config_path = None
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            print(f"  ✓ Found config file: {config_path}")
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                config_found = True
                actual_config_path = config_path
                break
            except Exception as e:
                print(f"  ✗ Error loading {config_path}: {e}")
        else:
            print(f"  - Config file not found: {config_path}")
    
    if not config_found:
        print("  ✗ No valid config file found!")
        return
    
    # Test 2: Check GPS configuration
    print(f"\n2. GPS Configuration from {actual_config_path}:")
    gps_port = config_data.get('gps_port', 'NOT SET')
    gps_baudrate = config_data.get('gps_baudrate', 'NOT SET')
    gps_timeout = config_data.get('gps_timeout', 'NOT SET')
    
    print(f"  GPS Port: {gps_port}")
    print(f"  GPS Baudrate: {gps_baudrate}")
    print(f"  GPS Timeout: {gps_timeout}")
    
    if gps_port == "/dev/ttyAMA0":
        print("  ✓ GPS port correctly set to GPIO UART (/dev/ttyAMA0)")
    elif gps_port == "/dev/ttyUSB0":
        print("  ✗ GPS port still set to USB (/dev/ttyUSB0) - should be /dev/ttyAMA0")
    else:
        print(f"  ? GPS port set to unexpected value: {gps_port}")
    
    # Test 3: Check device availability
    print(f"\n3. Device Availability Check:")
    devices_to_check = ["/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/serial0"]
    
    for device in devices_to_check:
        if os.path.exists(device):
            print(f"  ✓ {device} exists")
        else:
            print(f"  ✗ {device} does not exist")
    
    # Test 4: Test GPS module import and initialization
    print(f"\n4. GPS Module Import Test:")
    try:
        from gps import GPS
        print("  ✓ GPS module imported successfully")
        
        # Test GPS initialization with current config
        print("  Testing GPS initialization with current config...")
        try:
            gps = GPS(config_data)
            print(f"  ✓ GPS object created successfully with port: {gps.port}")
        except Exception as e:
            print(f"  ✗ GPS initialization failed: {e}")
            
    except ImportError as e:
        print(f"  ✗ Failed to import GPS module: {e}")
    
    # Test 5: Show all GPS-related config keys
    print(f"\n5. All GPS-Related Configuration Keys:")
    gps_keys = [key for key in config_data.keys() if 'gps' in key.lower()]
    for key in gps_keys:
        print(f"  {key}: {config_data[key]}")
    
    print(f"\n6. Summary:")
    print(f"  Config file: {actual_config_path}")
    print(f"  GPS port in config: {gps_port}")
    print(f"  Expected GPS port: /dev/ttyAMA0")
    if gps_port == "/dev/ttyAMA0":
        print("  ✓ Configuration appears correct")
    else:
        print("  ✗ Configuration needs updating")


if __name__ == '__main__':
    main()