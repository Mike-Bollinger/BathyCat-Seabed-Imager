#!/usr/bin/env python3
"""
USB Storage Setup and Debug Tool for BathyCat Seabed Imager
==========================================================

Tool to detect, mount, and configure USB storage for BathyCat.
Specifically designed for SanDisk USB drives.

Author: Mike Bollinger
Date: August 2025
"""

import subprocess
import os
import sys
from pathlib import Path
import json

def run_command(command, description=""):
    """Run a command and return output."""
    try:
        if description:
            print(f"\n🔍 {description}")
        print(f"   $ {command}")
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"   Error: {result.stderr.strip()}")
        
        return result.stdout.strip(), result.stderr.strip(), result.returncode
        
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Command timed out")
        return "", "Timeout", 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return "", str(e), 1

def check_usb_devices():
    """Check for USB storage devices."""
    print("🔍 Checking USB Storage Devices")
    print("=" * 40)
    
    # List USB devices
    stdout, stderr, code = run_command("lsusb", "USB devices connected")
    
    # Look for storage devices
    sandisk_found = "SanDisk" in stdout or "sandisk" in stdout.lower()
    storage_keywords = ["Mass Storage", "Storage", "SanDisk", "USB", "Flash"]
    storage_devices = [line for line in stdout.split('\n') 
                      if any(keyword in line for keyword in storage_keywords)]
    
    if sandisk_found:
        print("   ✅ SanDisk device detected!")
    if storage_devices:
        print("   💾 Storage devices found:")
        for device in storage_devices:
            print(f"      {device}")
    
    return bool(storage_devices)

def check_block_devices():
    """Check block devices (actual storage devices)."""
    print("\n💾 Checking Block Devices")
    print("=" * 40)
    
    # List block devices
    stdout, stderr, code = run_command("lsblk -f", "Block devices with filesystems")
    
    # Look for USB devices
    usb_devices = []
    lines = stdout.split('\n')
    for line in lines:
        if any(fs in line.lower() for fs in ['fat32', 'exfat', 'ntfs', 'ext4', 'vfat']):
            if '/dev/sd' in line or 'usb' in line.lower():
                usb_devices.append(line.strip())
    
    if usb_devices:
        print("   📱 USB storage devices:")
        for device in usb_devices:
            print(f"      {device}")
    else:
        print("   ❌ No USB storage devices found")
    
    # Also check /dev for USB devices
    stdout, stderr, code = run_command("ls -la /dev/sd*", "USB device files")
    
    return usb_devices

def check_mount_points():
    """Check current mount points."""
    print("\n📂 Checking Mount Points")
    print("=" * 40)
    
    # Check df for mounted filesystems
    stdout, stderr, code = run_command("df -h", "Mounted filesystems")
    
    # Look for USB mounts
    usb_mounts = []
    lines = stdout.split('\n')
    for line in lines:
        if any(path in line for path in ['/media/', '/mnt/', '/dev/sd']):
            usb_mounts.append(line.strip())
    
    if usb_mounts:
        print("   📁 USB mount points:")
        for mount in usb_mounts:
            print(f"      {mount}")
    
    # Check common USB mount locations
    common_paths = [
        '/media/usb-storage',
        '/media/bathyimager',
        '/media/pi',
        '/mnt/usb',
        '/mnt/bathycat'
    ]
    
    print("   📍 Checking common USB paths:")
    for path in common_paths:
        if os.path.exists(path):
            try:
                files = os.listdir(path)
                size = len(files)
                print(f"      ✅ {path} (exists, {size} items)")
            except PermissionError:
                print(f"      ⚠️  {path} (exists, permission denied)")
        else:
            print(f"      ❌ {path} (not found)")
    
    return usb_mounts

def create_usb_mount():
    """Create and mount USB storage."""
    print("\n🔧 Setting Up USB Mount")
    print("=" * 40)
    
    # Find USB device
    stdout, stderr, code = run_command("lsblk -rno NAME,TYPE,SIZE,MOUNTPOINT", 
                                      "Finding USB device")
    
    usb_device = None
    lines = stdout.split('\n')
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] == 'part' and parts[0].startswith('sd'):
            # This might be our USB device
            device_name = parts[0]
            if len(parts) == 3 or not parts[3]:  # Not mounted
                usb_device = f"/dev/{device_name}"
                print(f"   📱 Found unmounted USB device: {usb_device}")
                break
    
    if not usb_device:
        print("   ❌ No unmounted USB device found")
        return None
    
    # Create mount point
    mount_point = "/media/usb-storage"
    stdout, stderr, code = run_command(f"sudo mkdir -p {mount_point}", 
                                      f"Creating mount point {mount_point}")
    
    # Mount the device
    stdout, stderr, code = run_command(f"sudo mount {usb_device} {mount_point}", 
                                      f"Mounting {usb_device} to {mount_point}")
    
    if code == 0:
        print(f"   ✅ Successfully mounted {usb_device} to {mount_point}")
        
        # Test write access
        test_file = f"{mount_point}/.bathycat_test"
        stdout, stderr, code = run_command(f"echo 'test' | sudo tee {test_file}", 
                                          "Testing write access")
        
        if code == 0:
            run_command(f"sudo rm {test_file}", "Cleaning up test file")
            print("   ✅ Write access confirmed")
            return mount_point
        else:
            print("   ❌ Write access failed")
    else:
        print(f"   ❌ Mount failed: {stderr}")
    
    return None

def setup_bathycat_directories(mount_point):
    """Set up BathyCat directory structure on USB."""
    print(f"\n📁 Setting Up BathyCat Directories on {mount_point}")
    print("=" * 40)
    
    bathycat_path = f"{mount_point}/bathycat"
    directories = [
        "images",
        "metadata", 
        "previews",
        "logs",
        "exports"
    ]
    
    # Create main BathyCat directory
    stdout, stderr, code = run_command(f"sudo mkdir -p {bathycat_path}", 
                                      f"Creating main directory {bathycat_path}")
    
    if code != 0:
        print(f"   ❌ Failed to create main directory: {stderr}")
        return False
    
    # Create subdirectories
    for directory in directories:
        dir_path = f"{bathycat_path}/{directory}"
        stdout, stderr, code = run_command(f"sudo mkdir -p {dir_path}", 
                                          f"Creating {dir_path}")
        if code == 0:
            print(f"   ✅ Created {directory}/")
        else:
            print(f"   ❌ Failed to create {directory}/: {stderr}")
    
    # Set permissions for the user
    username = os.getenv('USER', 'bathyimager')
    stdout, stderr, code = run_command(f"sudo chown -R {username}:{username} {bathycat_path}", 
                                      f"Setting ownership to {username}")
    
    if code == 0:
        print(f"   ✅ Set ownership to {username}")
    else:
        print(f"   ⚠️  Ownership setting failed: {stderr}")
    
    # Set permissions
    stdout, stderr, code = run_command(f"sudo chmod -R 755 {bathycat_path}", 
                                      "Setting directory permissions")
    
    return True

def test_bathycat_storage():
    """Test BathyCat storage configuration."""
    print("\n🧪 Testing BathyCat Storage Configuration")
    print("=" * 40)
    
    # Test with BathyCat config
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from config import Config
        from storage_manager import StorageManager
        
        print("   ✅ BathyCat modules imported successfully")
        
        # Test different storage paths
        test_paths = [
            "/media/usb-storage/bathycat",
            "/media/bathyimager/bathycat", 
            "/mnt/usb/bathycat"
        ]
        
        for path in test_paths:
            print(f"\n   📍 Testing path: {path}")
            
            if os.path.exists(path):
                print(f"      ✅ Path exists")
                
                # Test BathyCat StorageManager
                try:
                    config = Config()
                    config.config_data['storage_base_path'] = path
                    storage = StorageManager(config)
                    
                    # Test initialization (this will be async, so we'll just test creation)
                    print(f"      ✅ StorageManager created successfully")
                    print(f"      📊 Base path: {storage.base_path}")
                    
                    # Check if directories can be created
                    if os.access(path, os.W_OK):
                        print(f"      ✅ Write access confirmed")
                    else:
                        print(f"      ❌ No write access")
                        
                except Exception as e:
                    print(f"      ❌ StorageManager error: {e}")
            else:
                print(f"      ❌ Path does not exist")
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Make sure you're running from the BathyCat directory")
    except Exception as e:
        print(f"   ❌ Test error: {e}")

def main():
    """Main USB storage setup routine."""
    print("🚀 BathyCat USB Storage Setup Tool")
    print("=" * 50)
    
    print("This tool will help set up USB storage for BathyCat.")
    
    # Step 1: Check USB devices
    usb_found = check_usb_devices()
    
    # Step 2: Check block devices
    block_devices = check_block_devices()
    
    # Step 3: Check mount points
    mount_points = check_mount_points()
    
    # Step 4: Try to mount USB if not already mounted
    mount_point = None
    if not any('/media/' in mount or '/mnt/' in mount for mount in mount_points):
        print("\n💡 No USB storage appears to be mounted. Attempting to mount...")
        mount_point = create_usb_mount()
    else:
        print("\n✅ USB storage appears to be already mounted")
        for mount in mount_points:
            if '/media/' in mount or '/mnt/' in mount:
                mount_point = mount.split()[-1]  # Get mount point
                break
    
    # Step 5: Setup BathyCat directories
    if mount_point:
        setup_success = setup_bathycat_directories(mount_point)
        if setup_success:
            print(f"\n✅ BathyCat USB storage setup complete!")
            print(f"   Storage path: {mount_point}/bathycat")
            
            # Step 6: Test BathyCat integration
            test_bathycat_storage()
        else:
            print(f"\n❌ Failed to set up BathyCat directories")
    
    # Summary
    print(f"\n📋 Setup Summary:")
    print(f"   USB Device: {'✅ Found' if usb_found else '❌ Not found'}")
    print(f"   Block Device: {'✅ Found' if block_devices else '❌ Not found'}")
    print(f"   Mount Point: {'✅ ' + mount_point if mount_point else '❌ Not mounted'}")
    
    if mount_point:
        print(f"\n🎯 Next Steps:")
        print(f"   1. Update BathyCat config: storage_base_path = '{mount_point}/bathycat'")
        print(f"   2. Test with: python3 tests/test_camera_capture.py --usb-only")
        print(f"   3. Run main app: python3 src/bathycat_imager.py")
    else:
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Check USB connection")
        print(f"   2. Try: sudo fdisk -l")
        print(f"   3. Manual mount: sudo mount /dev/sdb1 /media/usb-storage")

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("⚠️  Some operations require root privileges.")
        print("   For full functionality, run: sudo python3 tests/test_usb_storage.py")
        print("   Continuing with limited functionality...")
        print()
    
    main()
