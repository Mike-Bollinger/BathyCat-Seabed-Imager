#!/usr/bin/env python3
"""
BathyImager Performance Diagnostic
=================================

Quick test to identify what's causing reduced capture rates.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_component_performance():
    """Test individual component performance"""
    print("🚀 BathyImager Performance Diagnostic")
    print("====================================")
    
    # Load config
    try:
        with open("../config/bathyimager_config.json", 'r') as f:
            config_data = json.load(f)
        print(f"✅ Config loaded - Target FPS: {config_data.get('capture_fps', 'Unknown')}")
    except Exception as e:
        print(f"❌ Config load failed: {e}")
        return
    
    print("\n--- Component Performance Tests ---")
    
    # Test camera capture speed
    try:
        from camera import Camera
        from config import BathyImagerConfig
        
        config = BathyImagerConfig("../config/bathyimager_config.json")
        print(f"📷 Testing camera capture speed...")
        
        camera = Camera(config, None)  # No logger for speed test
        camera.start()
        
        if camera.is_initialized:
            # Test 10 captures
            start_time = time.time()
            successful_captures = 0
            
            for i in range(10):
                frame = camera.capture_frame()
                if frame is not None:
                    successful_captures += 1
                time.sleep(0.01)  # Small delay like main loop
            
            end_time = time.time()
            test_duration = end_time - start_time
            capture_rate = successful_captures / test_duration
            
            print(f"   ✅ Camera: {successful_captures}/10 captures in {test_duration:.2f}s")
            print(f"   📊 Camera Rate: {capture_rate:.2f} fps (theoretical max)")
            
            if capture_rate < 4.0:
                print(f"   ⚠️  Camera is limiting factor (< 4 fps)")
            else:
                print(f"   ✅ Camera can support 4+ fps")
                
        else:
            print(f"   ❌ Camera initialization failed")
            
        camera.stop()
        
    except Exception as e:
        print(f"   ❌ Camera test failed: {e}")
    
    # Test GPS performance
    try:
        from gps import GPS
        
        print(f"\n🛰️  Testing GPS performance...")
        
        gps = GPS(config, None)  # No logger for speed test
        gps.start()
        
        # Wait a moment for GPS to initialize
        time.sleep(2)
        
        # Test GPS fix retrieval speed
        start_time = time.time()
        gps_tests = 0
        valid_fixes = 0
        
        for i in range(20):
            fix = gps.get_current_fix()
            gps_tests += 1
            if fix and fix.is_valid:
                valid_fixes += 1
            time.sleep(0.01)
        
        end_time = time.time()
        gps_duration = end_time - start_time
        gps_rate = gps_tests / gps_duration
        
        print(f"   ✅ GPS: {gps_tests} fix checks in {gps_duration:.2f}s")
        print(f"   📊 GPS Rate: {gps_rate:.1f} checks/sec")
        print(f"   🛰️  Valid fixes: {valid_fixes}/{gps_tests}")
        
        if gps_duration / gps_tests > 0.1:  # > 100ms per GPS check
            print(f"   ⚠️  GPS might be slowing capture (slow fix retrieval)")
        else:
            print(f"   ✅ GPS performance looks good")
            
        gps.stop()
        
    except Exception as e:
        print(f"   ❌ GPS test failed: {e}")
    
    # Test image processing speed
    try:
        from image_processor import ImageProcessor
        import numpy as np
        
        print(f"\n🖼️  Testing image processing speed...")
        
        processor = ImageProcessor(config, None)
        
        # Create test frame
        test_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        test_timestamp = datetime.now()
        
        # Test processing speed
        start_time = time.time()
        processed_images = 0
        
        for i in range(5):
            processed = processor.process_frame(test_frame, None, test_timestamp, None)
            if processed:
                processed_images += 1
        
        end_time = time.time()
        processing_duration = end_time - start_time
        processing_rate = processed_images / processing_duration
        
        print(f"   ✅ Processing: {processed_images}/5 images in {processing_duration:.2f}s")
        print(f"   📊 Processing Rate: {processing_rate:.2f} fps")
        
        if processing_duration / processed_images > 0.2:  # > 200ms per image
            print(f"   ⚠️  Image processing might be slowing capture")
        else:
            print(f"   ✅ Image processing performance looks good")
            
    except Exception as e:
        print(f"   ❌ Image processing test failed: {e}")
    
    # Test storage speed
    try:
        from storage import Storage
        
        print(f"\n💾 Testing storage speed...")
        
        storage = Storage(config, None)
        
        # Create test processed image data
        test_data = b"x" * 1000000  # 1MB test file
        test_timestamp = datetime.now()
        
        # Test storage speed
        start_time = time.time()
        saves = 0
        
        for i in range(3):
            # Simulate saving (we'll use a temporary filename pattern)
            try:
                filepath = storage.save_image(test_data, test_timestamp)
                if filepath:
                    saves += 1
                    # Clean up test file
                    if os.path.exists(filepath):
                        os.remove(filepath)
            except Exception as e:
                print(f"     Storage test {i+1} failed: {e}")
        
        end_time = time.time()
        storage_duration = end_time - start_time
        storage_rate = saves / storage_duration if saves > 0 else 0
        
        print(f"   ✅ Storage: {saves}/3 saves in {storage_duration:.2f}s")
        print(f"   📊 Storage Rate: {storage_rate:.2f} saves/sec")
        
        if saves > 0 and storage_duration / saves > 0.15:  # > 150ms per save
            print(f"   ⚠️  Storage might be slowing capture")
        else:
            print(f"   ✅ Storage performance looks good")
            
    except Exception as e:
        print(f"   ❌ Storage test failed: {e}")
    
    print(f"\n--- Summary ---")
    print(f"🎯 Target: 4.0 fps (250ms per capture cycle)")
    print(f"📊 Actual: ~2.0 fps (500ms per capture cycle)")
    print(f"")
    print(f"💡 Recommendations:")
    print(f"   • Check camera resolution settings (1920x1080 might be too high)")
    print(f"   • Consider reducing JPEG quality from 85 to 75")
    print(f"   • Disable debug logging in production")
    print(f"   • Check USB storage device speed")
    print(f"")
    print(f"🔧 Quick fixes to try:")
    print(f"   • Lower resolution: camera_width=1280, camera_height=720") 
    print(f"   • Lower quality: jpeg_quality=75")
    print(f"   • Check log_level: should be 'INFO' not 'DEBUG'")

if __name__ == "__main__":
    # Change to project directory if needed
    if os.path.basename(os.getcwd()) == "tests":
        os.chdir("..")
    
    test_component_performance()