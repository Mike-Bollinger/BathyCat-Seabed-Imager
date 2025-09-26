#!/usr/bin/env python3
"""
Simple BathyCat Camera Test
===========================
This script isolates just the camera capture to identify the NumPy boolean error.
"""

import sys
import os
sys.path.append('/opt/bathycat/src')

import cv2
import numpy as np
from config import Config

def test_simple_capture():
    """Test simple camera capture without all the BathyCat complexity."""
    print("=== Simple BathyCat Camera Test ===")
    
    # Load config
    try:
        config = Config('/etc/bathycat/config.json')
        print(f"✅ Config loaded: camera_device_id={config.camera_device_id}")
        print(f"   Resolution: {config.camera_width}x{config.camera_height}")
        print(f"   FPS: {config.camera_fps}")
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Open camera directly (like BathyCat does)
    print("\n--- Testing Camera Open ---")
    try:
        camera = cv2.VideoCapture(config.camera_device_id, cv2.CAP_V4L2)
        if not camera.isOpened():
            print("❌ Camera failed to open")
            return False
        print("✅ Camera opened successfully")
    except Exception as e:
        print(f"❌ Camera open error: {e}")
        return False
    
    # Configure camera (like BathyCat does)
    print("\n--- Configuring Camera ---")
    try:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        camera.set(cv2.CAP_PROP_FPS, config.camera_fps)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = camera.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ Camera configured: {actual_width}x{actual_height} @ {actual_fps}fps")
    except Exception as e:
        print(f"❌ Camera config error: {e}")
        camera.release()
        return False
    
    # Test capture loop (mimicking BathyCat's exact logic)
    print("\n--- Testing Capture Loop ---")
    try:
        for i in range(5):  # Test 5 captures
            print(f"Capture {i+1}/5...")
            
            # Exact same logic as BathyCat
            ret, frame = camera.read()
            print(f"  ret={ret}, frame_type={type(frame)}")
            
            # Test the exact same boolean checks
            if not ret:
                print("  ❌ ret is False")
                continue
                
            if frame is None:
                print("  ❌ frame is None")
                continue
                
            if frame.size == 0:
                print("  ❌ frame.size is 0")
                continue
            
            print(f"  ✅ Frame captured: {frame.shape}, size={frame.size}")
            
            # Test the problematic 'is not None' check
            try:
                result = (frame is not None)
                print(f"  ✅ 'frame is not None' test: {result}")
            except Exception as bool_error:
                print(f"  ❌ Boolean evaluation error: {bool_error}")
                raise bool_error
            
            # Save test image
            test_filename = f"/tmp/simple_test_{i+1}.jpg"
            cv2.imwrite(test_filename, frame)
            print(f"  ✅ Saved: {test_filename}")
            
            # Small delay
            import time
            time.sleep(0.1)
            
    except Exception as e:
        print(f"❌ Capture loop error: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        camera.release()
        return False
    
    camera.release()
    print("\n✅ Simple camera test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_simple_capture()
    if not success:
        print("\n❌ Test failed - this shows where the BathyCat issue is")
        sys.exit(1)
    else:
        print("\n✅ Test passed - camera hardware works fine")
        sys.exit(0)
