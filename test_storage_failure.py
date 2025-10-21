#!/usr/bin/env python3
"""
Test script to verify storage error handling when USB drive is missing.

This script simulates scenarios where the USB storage is unavailable
to verify error handling and status reporting.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from storage import StorageManager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    """Load the bathyimager configuration."""
    config_path = Path(__file__).parent / 'config' / 'bathyimager_config.json'
    with open(config_path, 'r') as f:
        return json.load(f)

def test_missing_usb_scenario():
    """Test what happens when USB storage is not available."""
    print("=" * 60)
    print("TESTING: Missing USB Drive Scenario")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Create a non-existent path to simulate missing USB
    original_path = config['storage_base_path']
    missing_path = "/nonexistent/missing_usb/bathyimager"
    
    print(f"Original USB path: {original_path}")
    print(f"Testing with missing path: {missing_path}")
    print()
    
    # Test storage initialization with missing path
    storage = StorageManager(
        base_path=missing_path,
        min_free_space_gb=config['min_free_space_gb'],
        auto_cleanup_enabled=config['auto_cleanup_enabled'],
        days_to_keep=config['days_to_keep']
    )
    
    print("1. Testing storage initialization:")
    try:
        result = storage.initialize()
        print(f"   Initialize result: {result}")
        print(f"   Storage available: {storage.is_available}")
    except Exception as e:
        print(f"   Initialize failed with exception: {e}")
    
    print("\n2. Testing storage info reporting:")
    storage_info = storage.get_storage_info()
    for key, value in storage_info.items():
        print(f"   {key}: {value}")
    
    print("\n3. Testing image save when storage unavailable:")
    test_image_data = b"fake image data for testing"
    try:
        saved_path = storage.save_image(test_image_data)
        print(f"   Save result: {saved_path}")
        if saved_path:
            print(f"   ERROR: Image was saved when storage should be unavailable!")
        else:
            print(f"   CORRECT: Image save returned None (storage unavailable)")
    except Exception as e:
        print(f"   Save failed with exception: {e}")
    
    print("\n4. Testing storage health check:")
    is_healthy = storage.is_healthy()
    print(f"   Storage healthy: {is_healthy}")

def test_read_only_scenario():
    """Test what happens when USB is mounted but read-only."""
    print("\n" + "=" * 60)
    print("TESTING: Read-Only USB Drive Scenario")
    print("=" * 60)
    
    # Create a temporary directory to simulate read-only USB
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = os.path.join(temp_dir, "bathyimager")
        os.makedirs(test_path, exist_ok=True)
        
        # Make it read-only (simulate read-only USB mount)
        os.chmod(test_path, 0o444)  # Read-only permissions
        
        print(f"Testing with read-only path: {test_path}")
        
        # Load config
        config = load_config()
        
        # Test storage with read-only path
        storage = StorageManager(
            base_path=test_path,
            min_free_space_gb=config['min_free_space_gb'],
            auto_cleanup_enabled=config['auto_cleanup_enabled'],
            days_to_keep=config['days_to_keep']
        )
        
        print("\n1. Testing storage initialization:")
        try:
            result = storage.initialize()
            print(f"   Initialize result: {result}")
            print(f"   Storage available: {storage.is_available}")
        except Exception as e:
            print(f"   Initialize failed with exception: {e}")
        
        print("\n2. Testing storage info reporting:")
        storage_info = storage.get_storage_info()
        for key, value in storage_info.items():
            print(f"   {key}: {value}")
        
        print("\n3. Testing image save with read-only storage:")
        test_image_data = b"fake image data for testing"
        try:
            saved_path = storage.save_image(test_image_data)
            print(f"   Save result: {saved_path}")
            if saved_path:
                print(f"   ERROR: Image was saved to read-only storage!")
            else:
                print(f"   CORRECT: Image save failed (read-only)")
        except Exception as e:
            print(f"   Save failed with exception: {e}")

def test_working_scenario():
    """Test normal working scenario for comparison."""
    print("\n" + "=" * 60)
    print("TESTING: Working Storage Scenario (for comparison)")
    print("=" * 60)
    
    # Create a temporary directory to simulate working USB
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = os.path.join(temp_dir, "bathyimager")
        
        print(f"Testing with working path: {test_path}")
        
        # Load config
        config = load_config()
        
        # Test storage with working path
        storage = StorageManager(
            base_path=test_path,
            min_free_space_gb=0.001,  # Very small requirement for testing
            auto_cleanup_enabled=config['auto_cleanup_enabled'],
            days_to_keep=config['days_to_keep']
        )
        
        print("\n1. Testing storage initialization:")
        try:
            result = storage.initialize()
            print(f"   Initialize result: {result}")
            print(f"   Storage available: {storage.is_available}")
        except Exception as e:
            print(f"   Initialize failed with exception: {e}")
        
        print("\n2. Testing storage info reporting:")
        storage_info = storage.get_storage_info()
        for key, value in storage_info.items():
            print(f"   {key}: {value}")
        
        print("\n3. Testing image save with working storage:")
        test_image_data = b"fake image data for testing"
        try:
            saved_path = storage.save_image(test_image_data)
            print(f"   Save result: {saved_path}")
            if saved_path and os.path.exists(saved_path):
                print(f"   SUCCESS: Image saved successfully")
                print(f"   File size: {os.path.getsize(saved_path)} bytes")
            else:
                print(f"   ERROR: Image save failed unexpectedly")
        except Exception as e:
            print(f"   Save failed with exception: {e}")

if __name__ == "__main__":
    print("BathyImager Storage Error Handling Test")
    print("Testing various storage failure scenarios...\n")
    
    # Run all tests
    test_missing_usb_scenario()
    test_read_only_scenario() 
    test_working_scenario()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("These tests verify how the storage system handles:")
    print("1. Missing/unmounted USB drives")
    print("2. Read-only USB drives") 
    print("3. Normal working storage")
    print()
    print("Key things to verify:")
    print("- Storage initialization fails gracefully")
    print("- is_available flag correctly reflects storage state")
    print("- Image saves return None when storage unavailable")
    print("- Error messages are clear and logged properly")
    print("- Status reporting shows storage state clearly")