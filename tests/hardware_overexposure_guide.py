#!/usr/bin/env python3
"""
Hardware Overexposure Solutions for BathyCat
==========================================

This script provides specific guidance for fixing camera hardware overexposure
when software exposure controls don't work.
"""

import cv2
import numpy as np
import subprocess
import os

def test_lighting_solutions():
    """Test different lighting/physical solutions for overexposure."""
    print("=== HARDWARE OVEREXPOSURE SOLUTIONS ===")
    print()
    print("Your camera has HARDWARE overexposure that doesn't respond to software controls.")
    print("This means the camera sensor is receiving too much light at the hardware level.")
    print()
    
    print("🔧 IMMEDIATE SOLUTIONS (try in order):")
    print()
    
    print("1. REDUCE AMBIENT LIGHTING:")
    print("   • Turn off all room lights")
    print("   • Close curtains/blinds")  
    print("   • Move to darker room")
    print("   • Test camera in dim lighting")
    print()
    
    print("2. PHYSICAL CAMERA BLOCKING:")
    print("   • Cover 50% of camera lens with tape")
    print("   • Use neutral density filter if available")
    print("   • Point camera at dark surface (black paper)")
    print("   • Adjust camera angle away from light sources")
    print()
    
    print("3. CAMERA SETTINGS HARDWARE ACCESS:")
    print("   • Try v4l2-ctl direct controls (Linux only)")
    print("   • Check if camera has physical brightness wheel")
    print("   • Look for camera manufacturer software")
    print()
    
    print("4. ALTERNATIVE CAMERA:")
    print("   • Try different USB camera if available")
    print("   • Some cameras have better exposure control")
    print("   • Lower resolution cameras often work better")
    print()

def create_brightness_test():
    """Create a simple brightness measurement test."""
    print("5. BRIGHTNESS MEASUREMENT TEST:")
    print("   Run this test after trying each solution above:")
    print()
    
    test_code = '''
import cv2
import numpy as np

# Test current brightness
cap = cv2.VideoCapture(0)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        brightness = np.mean(frame)
        print(f"Camera brightness: {brightness:.1f}/255")
        if brightness > 240:
            print("❌ Still severely overexposed (>240)")
        elif brightness > 200:
            print("⚠️  Overexposed but improving (200-240)")  
        elif brightness > 100:
            print("✓ Getting better (100-200)")
        else:
            print("✅ Normal exposure (<100)")
    cap.release()
else:
    print("❌ Camera access failed")
'''
    
    # Write test to file
    with open('brightness_test.py', 'w') as f:
        f.write(test_code)
    
    print("   Saved as: brightness_test.py")
    print("   Run: python3 brightness_test.py")
    print()

def check_v4l2_controls():
    """Show V4L2 control options if on Linux."""
    print("6. V4L2 DIRECT CAMERA CONTROLS (Linux/Pi only):")
    print()
    
    v4l2_commands = [
        "# List all camera controls:",
        "v4l2-ctl --list-ctrls",
        "",
        "# Set specific controls (try each):",
        "v4l2-ctl --set-ctrl=exposure_auto=1          # Manual exposure",
        "v4l2-ctl --set-ctrl=exposure_absolute=1      # Minimum exposure", 
        "v4l2-ctl --set-ctrl=brightness=0             # Minimum brightness",
        "v4l2-ctl --set-ctrl=contrast=16              # Low contrast",
        "v4l2-ctl --set-ctrl=saturation=32            # Low saturation",
        "v4l2-ctl --set-ctrl=gain=0                   # Minimum gain",
        "",
        "# Test after each command:",
        "python3 brightness_test.py"
    ]
    
    for cmd in v4l2_commands:
        print(f"   {cmd}")
    print()

def show_hardware_info():
    """Display hardware-specific information."""
    print("7. CAMERA HARDWARE INFO:")
    print()
    print("   Your camera: Microdia Webcam Vitade AF")
    print("   • This is a consumer webcam, not industrial camera")
    print("   • May have limited exposure control")
    print("   • Often designed for well-lit environments")
    print("   • Auto-exposure may be hardware-locked")
    print()
    print("   For seabed imaging, consider:")
    print("   • Industrial USB camera with manual controls")
    print("   • Camera with hardware exposure dial")
    print("   • Camera specifically designed for variable lighting")
    print()

def main():
    """Main hardware overexposure solution guide."""
    print("BathyCat Hardware Overexposure Solutions")
    print("=" * 45)
    print()
    print("PROBLEM: Camera brightness 254.3/255 - hardware overexposure")
    print("SOFTWARE: OpenCV exposure controls return 5000.0 (not working)")
    print("SOLUTION: Hardware/physical lighting control required")
    print()
    
    test_lighting_solutions()
    create_brightness_test()
    check_v4l2_controls() 
    show_hardware_info()
    
    print("=" * 60)
    print("RECOMMENDED ORDER OF OPERATIONS:")
    print("=" * 60)
    print("1. Run: python3 tests/quick_camera_fix.py  # Fix service first")
    print("2. Turn off all lights in room")
    print("3. Run: python3 brightness_test.py        # Measure brightness") 
    print("4. If still >240, cover 50% of camera lens")
    print("5. Run: python3 brightness_test.py        # Test again")
    print("6. If still >200, try v4l2-ctl commands")
    print("7. If still overexposed, need different camera")
    print()
    print("📊 TARGET: Get brightness below 200 (ideally 50-150)")
    print("🎯 SUCCESS: When images show detail instead of pure white")

if __name__ == "__main__":
    main()