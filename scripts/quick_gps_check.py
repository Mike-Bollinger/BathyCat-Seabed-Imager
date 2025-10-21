#!/usr/bin/env python3
"""
Quick GPS Tagging Status Check
=============================

This script quickly checks if GPS tagging and camera auto-settings are working.
Run this on the Raspberry Pi to diagnose current status.

Usage: python3 quick_gps_check.py
"""

import sys
import os
import logging
import json
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_config():
    """Check current configuration settings."""
    print("=== CONFIGURATION CHECK ===")
    
    config_path = "../config/bathyimager_config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"✓ Configuration loaded from {config_path}")
        print(f"  GPS enabled: {config.get('gps_port', 'NOT SET')}")
        print(f"  GPS time sync: {config.get('gps_time_sync', False)}")
        print(f"  Require GPS fix: {config.get('require_gps_fix', False)}")
        print(f"  Enable metadata: {config.get('enable_metadata', False)}")
        print(f"  Camera auto exposure: {config.get('camera_auto_exposure', False)}")
        print(f"  Camera auto white balance: {config.get('camera_auto_white_balance', False)}")
        
        return config
        
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return None

def check_gps_device():
    """Check if GPS device is available."""
    print("\n=== GPS DEVICE CHECK ===")
    
    # Check for USB GPS device
    try:
        result = os.popen("lsusb | grep -i gps").read().strip()
        if result:
            print(f"✓ GPS USB device found: {result}")
        else:
            print("⚠️  No GPS USB device found in lsusb")
    except:
        pass
    
    # Check for serial ports
    serial_ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]
    found_ports = []
    
    for port in serial_ports:
        if os.path.exists(port):
            found_ports.append(port)
    
    if found_ports:
        print(f"✓ Serial ports found: {', '.join(found_ports)}")
        
        # Try to read GPS data from first port
        try:
            import serial
            ser = serial.Serial(found_ports[0], 9600, timeout=2)
            data = ser.read(200).decode('ascii', errors='ignore')
            ser.close()
            
            if '$GP' in data or '$GN' in data:
                print(f"✓ GPS NMEA data detected on {found_ports[0]}")
                print(f"  Sample: {data[:80]}...")
                return True
            else:
                print(f"⚠️  No GPS NMEA data on {found_ports[0]}")
        except Exception as e:
            print(f"⚠️  Could not read from {found_ports[0]}: {e}")
    else:
        print("❌ No serial ports found")
    
    return False

def check_camera_device():
    """Check if camera device is available."""
    print("\n=== CAMERA DEVICE CHECK ===")
    
    # Check for video devices
    video_devices = []
    for i in range(5):  # Check /dev/video0 through /dev/video4
        device = f"/dev/video{i}"
        if os.path.exists(device):
            video_devices.append(device)
    
    if video_devices:
        print(f"✓ Video devices found: {', '.join(video_devices)}")
        
        # Try to open camera with OpenCV
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            
            if cap.isOpened():
                print("✓ Camera opens successfully with OpenCV")
                
                # Check camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                auto_exposure = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
                auto_wb = cap.get(cv2.CAP_PROP_AUTO_WB)
                
                print(f"  Resolution: {width}x{height}")
                print(f"  FPS: {fps}")
                print(f"  Auto exposure: {auto_exposure}")
                print(f"  Auto white balance: {auto_wb}")
                
                cap.release()
                return True
            else:
                print("❌ Camera fails to open with OpenCV")
        except Exception as e:
            print(f"❌ Camera test failed: {e}")
    else:
        print("❌ No video devices found")
    
    return False

def check_recent_images():
    """Check for recent images and their GPS metadata."""
    print("\n=== RECENT IMAGES CHECK ===")
    
    # Look for recent images
    storage_paths = [
        "/media/usb/bathyimager",
        "../test_images",
        "/tmp/bathyimager"
    ]
    
    recent_images = []
    for base_path in storage_paths:
        if os.path.exists(base_path):
            try:
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if file.endswith(('.jpg', '.jpeg')):
                            filepath = os.path.join(root, file)
                            mtime = os.path.getmtime(filepath)
                            recent_images.append((filepath, mtime))
            except:
                pass
    
    # Sort by modification time, most recent first
    recent_images.sort(key=lambda x: x[1], reverse=True)
    
    if not recent_images:
        print("⚠️  No images found in common storage locations")
        return
    
    # Check the most recent few images
    print(f"Found {len(recent_images)} images, checking most recent 3:")
    
    for i, (filepath, mtime) in enumerate(recent_images[:3]):
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n  Image {i+1}: {os.path.basename(filepath)} ({mtime_str})")
        
        try:
            from PIL import Image
            import piexif
            
            with Image.open(filepath) as img:
                print(f"    Size: {img.size}")
                
                # Check for EXIF data
                exif_data = img.info.get('exif')
                if exif_data:
                    try:
                        exif_dict = piexif.load(exif_data)
                        gps_info = exif_dict.get('GPS', {})
                        
                        if gps_info:
                            # Try to extract coordinates
                            if 2 in gps_info and 4 in gps_info:  # GPSLatitude and GPSLongitude
                                print("    ✓ GPS coordinates found in EXIF")
                            else:
                                print("    ⚠️  GPS EXIF present but incomplete")
                        else:
                            print("    ❌ No GPS data in EXIF")
                        
                        # Check for timestamp
                        exif_main = exif_dict.get('0th', {})
                        if 306 in exif_main:  # DateTime
                            print(f"    ✓ Timestamp: {exif_main[306]}")
                    except Exception as e:
                        print(f"    ❌ EXIF parsing error: {e}")
                else:
                    print("    ❌ No EXIF data found")
                    
        except Exception as e:
            print(f"    ❌ Image read error: {e}")

def main():
    """Run quick GPS tagging status check."""
    print("BathyCat Quick GPS Tagging Status Check")
    print("=" * 45)
    
    # Check configuration
    config = check_config()
    
    # Check GPS device
    gps_ok = check_gps_device()
    
    # Check camera device  
    camera_ok = check_camera_device()
    
    # Check recent images
    check_recent_images()
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Configuration: {'✓ OK' if config else '❌ FAILED'}")
    print(f"GPS Device: {'✓ OK' if gps_ok else '❌ FAILED'}")
    print(f"Camera Device: {'✓ OK' if camera_ok else '❌ FAILED'}")
    
    if config and gps_ok and camera_ok:
        print("\n🎉 All basic components appear to be working!")
        print("If GPS metadata is still missing from images:")
        print("1. Check GPS has clear sky view for satellite acquisition")
        print("2. Run: sudo journalctl -u bathyimager | grep GPS")
        print("3. Run: ./scripts/gps_diagnostic.py for detailed testing")
    else:
        print("\n⚠️  Some components need attention - see details above")
        print("Run: ./scripts/hardware_diagnostics.sh for more detailed testing")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Script failed: {e}")
        sys.exit(1)