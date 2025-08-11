#!/usr/bin/env python3
"""
GPS Debug Tool for BathyCat Seabed Imager
=========================================

Simple tool to debug GPS connectivity and data reception.
Works even without GPS fix (indoors).

Author: Mike Bollinger
Date: August 2025
"""

import sys
import time
import subprocess
import glob
from pathlib import Path

def check_usb_devices():
    """Check for USB devices that might be GPS."""
    print("🔍 Checking USB devices...")
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')
        
        print(f"Found {len(lines)} USB devices:")
        gps_keywords = ['GPS', 'GlobalSat', 'u-blox', 'PA1010D', 'Adafruit', 'NMEA']
        
        for line in lines:
            is_gps = any(keyword.lower() in line.lower() for keyword in gps_keywords)
            marker = "🛰️ " if is_gps else "   "
            print(f"{marker}{line}")
            
        return any(any(keyword.lower() in line.lower() for keyword in gps_keywords) for line in lines)
        
    except Exception as e:
        print(f"Error checking USB devices: {e}")
        return False

def check_serial_devices():
    """Check for serial devices that might be GPS."""
    print("\n🔌 Checking serial devices...")
    
    # Common GPS serial device patterns
    patterns = ['/dev/ttyACM*', '/dev/ttyUSB*', '/dev/serial/by-id/*GPS*', '/dev/serial/by-id/*gps*']
    
    devices = []
    for pattern in patterns:
        devices.extend(glob.glob(pattern))
    
    if devices:
        print(f"Found {len(devices)} potential GPS devices:")
        for device in devices:
            print(f"   📡 {device}")
    else:
        print("❌ No serial devices found")
        print("   Check: Is GPS connected? Are drivers loaded?")
    
    return devices

def test_serial_device(device, duration=5):
    """Test reading from a serial device."""
    print(f"\n🧪 Testing {device} for GPS data...")
    
    try:
        # Use timeout command to read for a few seconds
        result = subprocess.run(['timeout', str(duration), 'cat', device], 
                              capture_output=True, text=True, timeout=duration+2)
        
        output = result.stdout
        
        if not output:
            print(f"   ❌ No data received from {device}")
            return False
            
        # Look for NMEA sentences
        lines = output.split('\n')
        nmea_lines = [line for line in lines if line.startswith('$')]
        
        if nmea_lines:
            print(f"   ✅ GPS NMEA data detected! ({len(nmea_lines)} sentences)")
            print("   📊 Sample data:")
            for line in nmea_lines[:3]:  # Show first 3 lines
                print(f"      {line[:80]}...")
            
            # Analyze sentence types
            sentence_types = {}
            for line in nmea_lines:
                if len(line) > 6:
                    sentence_type = line[:6]  # e.g., $GPGGA, $GPRMC
                    sentence_types[sentence_type] = sentence_types.get(sentence_type, 0) + 1
            
            print("   📋 Sentence types found:")
            for stype, count in sentence_types.items():
                print(f"      {stype}: {count} messages")
            
            return True
        else:
            print(f"   ❌ Data received, but no NMEA sentences found")
            print(f"   📝 Raw data sample: {output[:100]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout reading from {device}")
        return False
    except Exception as e:
        print(f"   ❌ Error reading from {device}: {e}")
        return False

def test_gps_controller():
    """Test the BathyCat GPS controller."""
    print(f"\n🧩 Testing BathyCat GPS Controller...")
    
    try:
        # Add src directory to path
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        
        from config import Config
        from gps_controller import GPSController
        
        config = Config()
        print(f"   📄 Config GPS port: {config.gps_port}")
        
        gps = GPSController(config)
        print("   ✅ GPS controller created successfully")
        
        # Get initial stats
        stats = gps.get_gps_stats()
        print(f"   📊 Initial stats: {stats}")
        
        # Test position string (should work even without fix)
        pos_str = gps.get_position_string()
        print(f"   📍 Position string: {pos_str}")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Try: pip3 install pynmea2 pyserial --break-system-packages")
        return False
    except Exception as e:
        print(f"   ❌ GPS controller error: {e}")
        return False

def main():
    """Main GPS debug routine."""
    print("🛰️  BathyCat GPS Debug Tool")
    print("=" * 40)
    
    print("This tool will help diagnose GPS connectivity issues.")
    print("It works even indoors without GPS satellite fix.\n")
    
    # Step 1: Check USB devices
    usb_gps_found = check_usb_devices()
    
    # Step 2: Check serial devices  
    serial_devices = check_serial_devices()
    
    # Step 3: Test each serial device
    gps_working = False
    for device in serial_devices:
        if test_serial_device(device):
            gps_working = True
            break
    
    # Step 4: Test GPS controller
    controller_working = test_gps_controller()
    
    # Summary
    print(f"\n📋 GPS Debug Summary:")
    print(f"   USB GPS Device: {'✅ Found' if usb_gps_found else '❌ Not found'}")
    print(f"   Serial Devices: {'✅ Found' if serial_devices else '❌ Not found'}")
    print(f"   GPS Data Flow: {'✅ Working' if gps_working else '❌ No data'}")
    print(f"   GPS Controller: {'✅ Working' if controller_working else '❌ Error'}")
    
    if not any([usb_gps_found, serial_devices, gps_working, controller_working]):
        print(f"\n🔧 Troubleshooting suggestions:")
        print(f"   1. Check USB connection - is GPS plugged in?")
        print(f"   2. Check device permissions: sudo usermod -a -G dialout $USER")
        print(f"   3. Install GPS tools: sudo apt install gpsd-clients")
        print(f"   4. Test with: gpspipe -r -n 5")
        print(f"   5. Check dmesg for USB device recognition: dmesg | tail")
    
    elif gps_working and controller_working:
        print(f"\n✅ GPS system appears to be working correctly!")
        print(f"   The GPS should work with BathyCat even indoors (no satellite fix needed)")
    
    else:
        print(f"\n⚠️  GPS hardware detected but controller has issues")
        print(f"   Check Python dependencies and configuration")

if __name__ == '__main__':
    main()
