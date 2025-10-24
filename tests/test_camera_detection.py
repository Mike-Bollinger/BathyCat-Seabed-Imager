#!/usr/bin/env python3
"""
Test camera manufacturer and model detection
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_camera_detection():
    """Test camera manufacturer/model detection"""
    try:
        from camera import Camera
        
        # Create minimal config for testing
        test_config = {
            'camera_device_id': 0,
            'camera_width': 1920,
            'camera_height': 1080,
            'camera_fps': 30,
            'camera_format': 'MJPG',
            'camera_auto_exposure': True,
            'camera_auto_white_balance': True,
            'camera_contrast': 50,
            'camera_saturation': 60,
            'camera_exposure': -6,
            'camera_white_balance': 4000
        }
        
        print("=== Camera Detection Test ===")
        
        # Test USB camera info detection (without initializing camera)
        camera = Camera(test_config)
        camera_info = camera.get_usb_camera_info()
        
        print(f"Detected Manufacturer: {camera_info['manufacturer']}")
        print(f"Detected Model: {camera_info['model']}")
        
        # Try to initialize camera and get full parameters
        print("\n=== Full Camera Parameters Test ===")
        if camera.initialize():
            print("Camera initialized successfully")
            
            params = camera.get_camera_exif_params()
            print(f"Camera Parameters:")
            for key, value in params.items():
                print(f"  {key}: {value}")
                
            camera.cleanup()
        else:
            print("Camera initialization failed (this is expected if no camera is connected)")
            
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_camera_detection()
    exit(0 if success else 1)