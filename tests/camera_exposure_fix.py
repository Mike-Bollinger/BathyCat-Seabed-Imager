#!/usr/bin/env python3
"""
Camera Exposure Emergency Fix
============================

This script attempts more aggressive exposure control methods
to fix the severe overexposure issue (brightness 254.3/255).
"""

import cv2
import numpy as np
import time

def test_extreme_exposure_values():
    """Test extreme exposure values to combat overexposure."""
    print("=== EXTREME EXPOSURE TESTING ===")
    
    cap = cv2.VideoCapture(0)  # Using working camera 0
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return False
    
    print("Camera opened successfully")
    
    # Get initial camera properties
    initial_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
    initial_auto_exp = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
    print(f"Initial exposure: {initial_exposure}")
    print(f"Initial auto exposure: {initial_auto_exp}")
    
    # Try extreme manual exposure values
    extreme_values = [-20, -15, -10, -8, -6, -4, -2, 0]
    
    print("\nTesting extreme manual exposure values:")
    
    # Force manual mode first
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    time.sleep(0.5)
    
    for exp_val in extreme_values:
        print(f"\nTrying exposure: {exp_val}")
        cap.set(cv2.CAP_PROP_EXPOSURE, exp_val)
        time.sleep(0.3)  # Give camera time to adjust
        
        actual_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
        print(f"  Set: {exp_val}, Got: {actual_exposure}")
        
        ret, frame = cap.read()
        if ret:
            brightness = np.mean(frame)
            print(f"  Brightness: {brightness:.1f}/255")
            
            # Save frame for analysis
            cv2.imwrite(f"exposure_test_{exp_val}_{brightness:.0f}.jpg", frame)
            
            if brightness < 200:  # Any improvement?
                print(f"  ✓ IMPROVEMENT! Brightness reduced to {brightness:.1f}")
                cap.release()
                return exp_val, brightness
            else:
                print(f"  ❌ Still overexposed")
    
    cap.release()
    return None, 254.3

def test_other_camera_properties():
    """Test other camera properties that might affect exposure."""
    print("\n=== TESTING OTHER CAMERA PROPERTIES ===")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return
    
    # Properties that might affect brightness/exposure
    properties_to_test = [
        (cv2.CAP_PROP_BRIGHTNESS, "Brightness", [0, 32, 64, 128]),
        (cv2.CAP_PROP_CONTRAST, "Contrast", [0, 16, 32, 64]),
        (cv2.CAP_PROP_GAMMA, "Gamma", [50, 100, 200]),
        (cv2.CAP_PROP_GAIN, "Gain", [0, 1, 2, 4]),
        (cv2.CAP_PROP_SATURATION, "Saturation", [0, 32, 64])
    ]
    
    for prop, name, test_values in properties_to_test:
        print(f"\nTesting {name}:")
        
        initial_val = cap.get(prop)
        print(f"  Initial {name}: {initial_val}")
        
        for val in test_values:
            cap.set(prop, val)
            actual_val = cap.get(prop)
            
            if abs(actual_val - val) < 1:  # Property was set successfully
                time.sleep(0.2)
                ret, frame = cap.read()
                if ret:
                    brightness = np.mean(frame)
                    print(f"  {name}={val}: brightness={brightness:.1f}")
                    
                    if brightness < 200:
                        print(f"    ✓ IMPROVEMENT with {name}={val}")
                        cv2.imwrite(f"property_test_{name}_{val}_{brightness:.0f}.jpg", frame)
            else:
                print(f"  {name}={val}: not supported (got {actual_val})")
    
    cap.release()

def test_camera_resolution_effect():
    """Test if different resolutions affect exposure."""
    print("\n=== TESTING RESOLUTION EFFECT ===")
    
    resolutions = [
        (320, 240, "QVGA"),
        (640, 480, "VGA"), 
        (1280, 720, "HD"),
        (1920, 1080, "FHD")
    ]
    
    for width, height, name in resolutions:
        print(f"\nTesting {name} ({width}x{height}):")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            continue
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual
        cap.set(cv2.CAP_PROP_EXPOSURE, -10)  # Low exposure
        
        time.sleep(0.5)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        ret, frame = cap.read()
        if ret:
            brightness = np.mean(frame)
            print(f"  Resolution: {actual_width}x{actual_height}")
            print(f"  Brightness: {brightness:.1f}/255")
            
            if brightness < 200:
                print(f"  ✓ IMPROVEMENT at {name} resolution!")
                cv2.imwrite(f"resolution_test_{name}_{brightness:.0f}.jpg", frame)
        
        cap.release()

def check_v4l2_controls():
    """Check V4L2 controls directly if available."""
    print("\n=== CHECKING V4L2 CONTROLS ===")
    
    try:
        import subprocess
        
        # List camera controls
        result = subprocess.run(['v4l2-ctl', '--list-ctrls', '--device', '/dev/video0'], 
                               capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("Available V4L2 controls:")
            controls = result.stdout
            print(controls)
            
            # Look for exposure controls
            if 'exposure' in controls.lower():
                print("\n✓ Exposure controls found in V4L2")
                
                # Try to set exposure via v4l2-ctl
                exposure_values = [1, 10, 50, 100, 500]
                
                for exp_val in exposure_values:
                    print(f"\nTrying v4l2-ctl exposure: {exp_val}")
                    
                    set_result = subprocess.run(['v4l2-ctl', '--set-ctrl', f'exposure_absolute={exp_val}', '--device', '/dev/video0'],
                                              capture_output=True, text=True, timeout=5)
                    
                    if set_result.returncode == 0:
                        print(f"  ✓ Set exposure_absolute={exp_val}")
                        
                        # Test with OpenCV
                        cap = cv2.VideoCapture(0)
                        if cap.isOpened():
                            time.sleep(0.5)
                            ret, frame = cap.read()
                            if ret:
                                brightness = np.mean(frame)
                                print(f"  Brightness after v4l2 control: {brightness:.1f}")
                                
                                if brightness < 200:
                                    print(f"  ✓ SUCCESS with v4l2-ctl exposure={exp_val}")
                                    cv2.imwrite(f"v4l2_exposure_{exp_val}_{brightness:.0f}.jpg", frame)
                                    cap.release()
                                    return exp_val
                            cap.release()
                    else:
                        print(f"  ❌ Failed to set v4l2 exposure: {set_result.stderr}")
            else:
                print("No exposure controls found in V4L2")
        else:
            print("v4l2-ctl not available or failed")
            
    except Exception as e:
        print(f"V4L2 control test failed: {e}")
    
    return None

def main():
    """Run comprehensive exposure fix testing."""
    print("Camera Exposure Emergency Fix")
    print("=" * 35)
    
    # Test 1: Extreme manual exposure values
    working_exposure, brightness = test_extreme_exposure_values()
    
    if working_exposure is not None:
        print(f"\n✓ FOUND WORKING EXPOSURE: {working_exposure} (brightness: {brightness:.1f})")
        return working_exposure
    
    # Test 2: Other camera properties
    test_other_camera_properties()
    
    # Test 3: Different resolutions
    test_camera_resolution_effect()
    
    # Test 4: V4L2 direct controls
    v4l2_exposure = check_v4l2_controls()
    if v4l2_exposure:
        return v4l2_exposure
    
    print("\n" + "="*50)
    print("EMERGENCY RECOMMENDATIONS:")
    print("="*50)
    print("1. 🔦 LIGHTING: Cover camera or reduce ambient light significantly")
    print("2. 🎛️  HARDWARE: Camera may have physical exposure dial/button")
    print("3. 📦 DIFFERENT CAMERA: This camera may not support software exposure control")
    print("4. 🔌 USB POWER: Try different USB port (some ports provide different power)")
    print("5. 💻 TEST WITH OTHER SOFTWARE: Try 'cheese' or 'guvcview' to verify camera works")
    
    print(f"\nTest images saved - check if any show improvement:")
    import os
    test_images = [f for f in os.listdir('.') if f.startswith(('exposure_test_', 'property_test_', 'resolution_test_', 'v4l2_'))]
    for img in sorted(test_images):
        print(f"  {img}")
    
    return None

if __name__ == "__main__":
    result = main()