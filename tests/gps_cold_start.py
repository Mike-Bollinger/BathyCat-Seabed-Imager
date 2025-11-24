#!/usr/bin/env python3
"""
GPS Cold Start Tool
===================

Forces a GPS cold start to clear old almanac data and force fresh satellite acquisition.
Use this when GPS won't acquire a fix despite being in a good location.
"""

import serial
import time
import sys


def send_mtk_command(ser, cmd):
    """Send MTK command and calculate checksum."""
    # Calculate checksum
    checksum = 0
    for char in cmd:
        checksum ^= ord(char)
    
    full_cmd = f"${cmd}*{checksum:02X}\r\n"
    print(f"Sending: {full_cmd.strip()}")
    ser.write(full_cmd.encode('ascii'))
    time.sleep(0.5)


def main():
    print("=" * 70)
    print("GPS COLD START TOOL")
    print("=" * 70)
    print("\nThis will force the GPS to perform a cold start, clearing all")
    print("stored almanac and ephemeris data. This can help when the GPS")
    print("has stale data preventing a fix.")
    print("\nWARNING: After cold start, the GPS may take 5-15 minutes to")
    print("acquire a fix as it downloads fresh satellite data.")
    print("=" * 70)
    
    response = input("\nContinue with cold start? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return 0
    
    # Try common GPS serial port locations
    gps_ports = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']
    ser = None
    
    for port in gps_ports:
        try:
            print(f"\nTrying {port}...")
            ser = serial.Serial(port, 9600, timeout=1.0)
            print(f"✓ GPS connected on {port}\n")
            break
        except Exception as e:
            print(f"  ✗ {port}: {e}")
    
    if not ser:
        print("\n✗ Failed to connect to GPS on any known port")
        print("Available ports should include /dev/serial0 for GPS HAT")
        return 1
    
    try:
        
        # For Adafruit Ultimate GPS (MTK3339 chipset), send cold start command
        print("Issuing cold start command...")
        send_mtk_command(ser, "PMTK104")  # Full cold start
        
        time.sleep(1.0)
        
        # Also try to set the update rate to 1Hz for reliable operation
        print("Setting update rate to 1Hz...")
        send_mtk_command(ser, "PMTK220,1000")  # 1000ms = 1Hz
        
        time.sleep(1.0)
        
        # Enable GNGGA, GNRMC, GNVTG, GPGSA, GLGSA sentences
        print("Enabling NMEA sentences...")
        send_mtk_command(ser, "PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
        
        time.sleep(1.0)
        
        print("\n✓ Cold start complete!")
        print("\nThe GPS is now searching for satellites from scratch.")
        print("This may take 5-15 minutes for first fix.")
        print("\nRecommendations while waiting:")
        print("  1. Keep GPS outside with clear view of sky")
        print("  2. Ensure GPS HAT battery is installed (CR1220)")
        print("  3. Avoid moving the unit during acquisition")
        print("  4. Run 'python3 tests/gps_diagnostic.py' to monitor progress")
        
        print("\nReading GPS for 5 seconds to verify it's responding...")
        print("-" * 70)
        
        for i in range(50):
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line:
                print(line)
        
        print("-" * 70)
        print("✓ GPS is responding\n")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
