#!/usr/bin/env python3
"""
Simple Camera Test for BathyCat
==============================

This script tests camera access with different backends and provides
immediate feedback on camera issues.
"""

import cv2
import numpy as np
import time

def test_camera_backends():
    """Test camera with different OpenCV backends."""
    print("=== TESTING CAMERA BACKENDS ===")
    
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_GSTREAMER, "GStreamer"), 
        (cv2.CAP_FFMPEG, "FFmpeg"),
        (None, "Default")
    ]
    
    working_cameras = []
    
    for backend, name in backends:
        print(f"\nTesting {name} backend...")
        
        for index in range(5):  # Test indices 0-4
            try:
                if backend is None:
                    cap = cv2.VideoCapture(index)
                else:
                    cap = cv2.VideoCapture(index, backend)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        mean_brightness = np.mean(frame)
                        print(f"  ✓ Camera {index} works: {frame.shape}, brightness: {mean_brightness:.1f}")
                        working_cameras.append((index, backend, name, mean_brightness))
                        
                        # Save test image
                        cv2.imwrite(f"test_camera_{index}_{name.lower()}.jpg", frame)
                        print(f"    Saved: test_camera_{index}_{name.lower()}.jpg")
                    else:
                        print(f"  ⚠  Camera {index} opens but can't capture")
                    cap.release()
                else:
                    print(f"  ❌ Camera {index} failed to open")
                    
            except Exception as e:
                print(f"  ❌ Camera {index} error: {e}")
    
    return working_cameras

def test_exposure_settings(camera_index, backend=None):
    """Test different exposure settings on a working camera."""
    print(f"\n=== TESTING EXPOSURE ON CAMERA {camera_index} ===")
    
    try:
        if backend is None:
            cap = cv2.VideoCapture(camera_index)
        else:
            cap = cv2.VideoCapture(camera_index, backend)
        
        if not cap.isOpened():
            print("❌ Failed to open camera for exposure test")
            return
        
        # Test different auto-exposure settings
        exposure_settings = [
            (0.25, "Manual (0.25)"),
            (0.75, "Auto (0.75)"),
            (1.0, "Auto (1.0)"),
            (3.0, "Auto (3.0)")
        ]
        
        for exp_val, desc in exposure_settings:
            print(f"\nTesting {desc}:")
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, exp_val)
            actual = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
            print(f"  Set: {exp_val}, Got: {actual}")
            
            # If manual mode, set low exposure
            if exp_val == 0.25:
                cap.set(cv2.CAP_PROP_EXPOSURE, -8)
                exp = cap.get(cv2.CAP_PROP_EXPOSURE)
                print(f"  Manual exposure set to: {exp}")
            
            time.sleep(0.5)  # Let camera adjust
            
            ret, frame = cap.read()
            if ret:
                brightness = np.mean(frame)
                print(f"  Frame brightness: {brightness:.1f}/255")
                
                if brightness > 250:
                    print("  ⚠️  OVEREXPOSED (white)")
                elif brightness < 10:
                    print("  ⚠️  UNDEREXPOSED (dark)")
                else:
                    print("  ✓ Normal exposure")
                
                # Save test frame
                cv2.imwrite(f"test_exposure_{exp_val}_{brightness:.0f}.jpg", frame)
        
        cap.release()
        
    except Exception as e:
        print(f"❌ Exposure test failed: {e}")

def main():
    """Run camera diagnostics."""
    print("BathyCat Simple Camera Test")
    print("=" * 30)
    
    # Test backends
    working_cameras = test_camera_backends()
    
    if working_cameras:
        print(f"\n✓ Found {len(working_cameras)} working camera configurations:")
        for index, backend, name, brightness in working_cameras:
            status = "OVEREXPOSED" if brightness > 250 else "UNDEREXPOSED" if brightness < 10 else "NORMAL"
            print(f"  Camera {index} with {name}: {status} ({brightness:.1f})")
        
        # Test exposure on the first working camera
        best_camera = working_cameras[0]
        test_exposure_settings(best_camera[0], best_camera[1])
        
        print(f"\n✓ RECOMMENDATION:")
        print(f"  Use camera index: {best_camera[0]}")
        print(f"  Use backend: {best_camera[2]}")
        
        if best_camera[3] > 250:
            print(f"  ⚠️  Camera is overexposed - check lighting or use manual exposure")
        
    else:
        print("\n❌ No working cameras found")
        print("Troubleshooting:")
        print("1. Check camera is connected: lsusb")
        print("2. Check video devices exist: ls /dev/video*")
        print("3. Check permissions: groups $USER")
        print("4. Try: sudo usermod -a -G video $USER")

if __name__ == "__main__":
    main()