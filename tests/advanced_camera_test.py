#!/usr/bin/env python3
"""
Advanced Camera Diagnostic for BathyCat
======================================

This script performs deep analysis of camera properties and exposure/white balance settings.
It tests various OpenCV property constants and camera behaviors.
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_camera_properties():
    """Test OpenCV camera properties in detail."""
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        print(f"❌ Required imports failed: {e}")
        return False
    
    print("=== ADVANCED CAMERA PROPERTY TESTING ===")
    
    # Try to open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return False
    
    print("✓ Camera opened successfully")
    
    # Test different auto-exposure values
    print("\n--- AUTO-EXPOSURE TESTING ---")
    
    # OpenCV auto-exposure constants vary by version and camera
    auto_exposure_values = [
        (0.25, "Manual exposure (common)"),
        (0.75, "Auto exposure (common)"), 
        (1, "Auto exposure (alternative)"),
        (0, "Manual exposure (alternative)"),
        (3, "Auto exposure (some cameras)"),
        (0.5, "Semi-auto exposure")
    ]
    
    original_auto_exposure = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
    print(f"Original auto-exposure value: {original_auto_exposure}")
    
    for value, description in auto_exposure_values:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, value)
        actual_value = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
        print(f"Set {value} ({description}): Got {actual_value}")
        
        # Test exposure property when in manual mode
        if value in [0, 0.25]:  # Manual modes
            cap.set(cv2.CAP_PROP_EXPOSURE, -6)
            exposure_val = cap.get(cv2.CAP_PROP_EXPOSURE)
            print(f"  Manual exposure -6: Got {exposure_val}")
    
    # Test white balance
    print("\n--- WHITE BALANCE TESTING ---")
    
    original_auto_wb = cap.get(cv2.CAP_PROP_AUTO_WB)
    print(f"Original auto white balance: {original_auto_wb}")
    
    # Test auto white balance on/off
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)
    auto_wb_on = cap.get(cv2.CAP_PROP_AUTO_WB)
    print(f"Auto WB ON: Set 1, Got {auto_wb_on}")
    
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)  
    auto_wb_off = cap.get(cv2.CAP_PROP_AUTO_WB)
    print(f"Auto WB OFF: Set 0, Got {auto_wb_off}")
    
    # Test manual white balance temperature
    if auto_wb_off == 0:  # Manual mode worked
        cap.set(cv2.CAP_PROP_WB_TEMPERATURE, 4000)
        wb_temp = cap.get(cv2.CAP_PROP_WB_TEMPERATURE)
        print(f"Manual WB 4000K: Got {wb_temp}")
    
    # Test other important properties
    print("\n--- OTHER CAMERA PROPERTIES ---")
    
    properties = [
        (cv2.CAP_PROP_BRIGHTNESS, "Brightness"),
        (cv2.CAP_PROP_CONTRAST, "Contrast"), 
        (cv2.CAP_PROP_SATURATION, "Saturation"),
        (cv2.CAP_PROP_GAIN, "Gain"),
        (cv2.CAP_PROP_GAMMA, "Gamma")
    ]
    
    for prop, name in properties:
        try:
            value = cap.get(prop)
            print(f"{name}: {value}")
        except:
            print(f"{name}: NOT SUPPORTED")
    
    # Test frame capture with different settings
    print("\n--- FRAME CAPTURE TESTING ---")
    
    # Test with auto settings
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Try auto
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)  # Auto WB
    
    print("Testing with AUTO settings...")
    time.sleep(2)  # Let camera adjust
    
    for i in range(3):
        ret, frame = cap.read()
        if ret:
            mean_brightness = np.mean(frame)
            print(f"  Frame {i+1}: {frame.shape}, Mean brightness: {mean_brightness:.1f}")
            
            # Check if image is completely white (overexposed)
            if mean_brightness > 250:
                print(f"    ⚠️  Frame {i+1} appears OVEREXPOSED (very white)")
            elif mean_brightness < 10:
                print(f"    ⚠️  Frame {i+1} appears UNDEREXPOSED (very dark)")
            else:
                print(f"    ✓ Frame {i+1} appears normal")
        else:
            print(f"  ❌ Failed to capture frame {i+1}")
        time.sleep(0.5)
    
    # Test with manual settings
    print("\nTesting with MANUAL settings...")
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual
    cap.set(cv2.CAP_PROP_EXPOSURE, -7)  # Lower exposure
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)  # Manual WB
    
    time.sleep(2)  # Let settings take effect
    
    for i in range(3):
        ret, frame = cap.read()
        if ret:
            mean_brightness = np.mean(frame)
            print(f"  Frame {i+1}: {frame.shape}, Mean brightness: {mean_brightness:.1f}")
            
            if mean_brightness > 250:
                print(f"    ⚠️  Frame {i+1} STILL OVEREXPOSED with manual settings")
            elif mean_brightness < 10:
                print(f"    ⚠️  Frame {i+1} appears UNDEREXPOSED")
            else:
                print(f"    ✓ Frame {i+1} appears normal")
        else:
            print(f"  ❌ Failed to capture frame {i+1}")
        time.sleep(0.5)
    
    # Save test frames for analysis
    print("\n--- SAVING TEST FRAMES ---")
    
    # Auto settings frame
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)
    time.sleep(1)
    
    ret, auto_frame = cap.read()
    if ret:
        cv2.imwrite("test_frame_auto.jpg", auto_frame)
        print("✓ Saved test_frame_auto.jpg")
    
    # Manual settings frame  
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -8)  # Very low exposure
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    time.sleep(1)
    
    ret, manual_frame = cap.read()
    if ret:
        cv2.imwrite("test_frame_manual.jpg", manual_frame)
        print("✓ Saved test_frame_manual.jpg")
    
    cap.release()
    return True

def analyze_opencv_version():
    """Analyze OpenCV version and camera backend."""
    try:
        import cv2
        print(f"\n=== OPENCV ANALYSIS ===")
        print(f"OpenCV version: {cv2.__version__}")
        
        # Check available camera backends
        backends = []
        backend_names = {
            cv2.CAP_V4L2: "V4L2 (Linux)",
            cv2.CAP_GSTREAMER: "GStreamer", 
            cv2.CAP_FFMPEG: "FFmpeg",
        }
        
        # Try to detect available backends
        for backend_id, name in backend_names.items():
            try:
                cap = cv2.VideoCapture(0, backend_id)
                if cap.isOpened():
                    backends.append(name)
                    cap.release()
            except:
                pass
        
        print(f"Available backends: {', '.join(backends) if backends else 'Unknown'}")
        
        # Test default backend
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            backend_name = cap.getBackendName()
            print(f"Default backend: {backend_name}")
            cap.release()
        
    except Exception as e:
        print(f"❌ OpenCV analysis failed: {e}")

def check_usb_camera_info():
    """Check USB camera information."""
    print(f"\n=== USB CAMERA INFO ===")
    
    # Check lsusb for camera devices
    try:
        import subprocess
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            camera_lines = [line for line in lines if 'camera' in line.lower() or 'video' in line.lower()]
            
            if camera_lines:
                print("USB Camera devices found:")
                for line in camera_lines:
                    print(f"  {line}")
            else:
                print("No obvious camera devices in lsusb output")
                print("Full lsusb output:")
                print(result.stdout)
        else:
            print("Could not run lsusb command")
    except:
        print("lsusb not available or failed")
    
    # Check video devices
    video_devices = []
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
    
    if video_devices:
        print(f"Video devices found: {', '.join(video_devices)}")
    else:
        print("No /dev/video* devices found")

def main():
    """Main diagnostic function."""
    print("BathyCat Advanced Camera Diagnostic")
    print("="*50)
    
    # Check OpenCV and system info
    analyze_opencv_version()
    
    # Check USB camera hardware
    check_usb_camera_info()
    
    # Test camera properties in detail
    if test_camera_properties():
        print("\n✓ Camera property testing completed")
        print("\nNext steps:")
        print("1. Check test_frame_auto.jpg and test_frame_manual.jpg")
        print("2. Compare brightness levels between auto and manual")
        print("3. If both frames are white, camera may have hardware issue")
        print("4. Try different exposure values or different USB port")
    else:
        print("\n❌ Camera property testing failed")
        print("Check camera connection and permissions")

if __name__ == "__main__":
    main()