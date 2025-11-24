#!/usr/bin/env python3
"""
Find GPS Port
=============

Scan for available serial ports that might be the GPS.
"""

import os
import glob

print("=" * 70)
print("GPS PORT FINDER")
print("=" * 70)

# Check for common GPS serial ports
common_ports = [
    '/dev/serial0',      # Pi 3/4 primary UART (Bluetooth disabled)
    '/dev/serial1',      # Pi 3/4 mini UART
    '/dev/ttyAMA0',      # Pi hardware UART (older models or BT disabled)
    '/dev/ttyS0',        # Alternative name
    '/dev/ttyUSB0',      # USB GPS
    '/dev/ttyUSB1',
]

print("\nChecking common GPS ports:")
print("-" * 70)

found_ports = []
for port in common_ports:
    exists = os.path.exists(port)
    status = "✓ EXISTS" if exists else "✗ not found"
    print(f"{port:<20} {status}")
    if exists:
        found_ports.append(port)

# Also scan for any /dev/tty* devices
print("\n" + "=" * 70)
print("All /dev/tty* and /dev/serial* devices:")
print("-" * 70)

all_devices = []
all_devices.extend(glob.glob('/dev/tty*'))
all_devices.extend(glob.glob('/dev/serial*'))
all_devices.sort()

for dev in all_devices:
    # Filter out non-physical devices
    if any(x in dev for x in ['tty0', 'tty1', 'tty2', 'tty3', 'tty4', 'tty5', 
                                'tty6', 'tty7', 'tty8', 'tty9', 'ttyprintk']):
        continue
    print(f"  {dev}")

print("\n" + "=" * 70)
print("RECOMMENDATION:")
print("-" * 70)

if '/dev/serial0' in found_ports:
    print("✓ Use /dev/serial0 (recommended for Raspberry Pi GPS HAT)")
    print("  This is the primary UART when Bluetooth is disabled.")
elif '/dev/ttyAMA0' in found_ports:
    print("✓ Use /dev/ttyAMA0")
    print("  This is the hardware UART.")
elif found_ports:
    print(f"✓ Try: {found_ports[0]}")
else:
    print("✗ No obvious GPS serial port found!")
    print("\nTroubleshooting:")
    print("  1. Check GPS HAT is properly seated on GPIO pins")
    print("  2. Verify UART is enabled:")
    print("     Run: grep enable_uart /boot/config.txt")
    print("     Should show: enable_uart=1")
    print("  3. Check if Bluetooth is using the UART:")
    print("     Run: ls -l /dev/serial*")

print("=" * 70)
