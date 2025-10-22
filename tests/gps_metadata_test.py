#!/usr/bin/env python3
"""
GPS Fix and Metadata Test
========================

This script tests GPS fix acquisition and image metadata creation
to diagnose why GPS coordinates might not be appearing in images.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_gps_fix():
    """Test GPS fix acquisition."""
    print("=== GPS FIX TEST ===")
    
    try:
        from config import ConfigManager
        from gps import GPS, GPSFix
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        print(f"GPS port: {config.get('gps_port', 'NOT SET')}")
        print(f"GPS time sync: {config.get('gps_time_sync', False)}")
        print(f"Require GPS fix: {config.get('require_gps_fix', False)}")
        
        # Initialize GPS
        gps = GPS(config)
        
        if not gps.connect():
            print("❌ GPS connection failed")
            return None
        
        print("✓ GPS connected")
        
        if not gps.start_reading():
            print("❌ GPS reading failed")
            gps.disconnect()
            return None
        
        print("✓ GPS reading started")
        
        # Wait for GPS data
        print("Waiting 10 seconds for GPS data...")
        time.sleep(10)
        
        # Get current fix
        current_fix = gps.get_current_fix()
        
        if current_fix:
            print("✓ GPS fix obtained:")
            print(f"  Latitude: {current_fix.latitude}")
            print(f"  Longitude: {current_fix.longitude}")
            print(f"  Fix quality: {current_fix.fix_quality}")
            print(f"  Satellites: {current_fix.satellites}")
            print(f"  Is valid: {current_fix.is_valid}")
            
            # Test if coordinates would pass our validation
            coords_valid = (current_fix.latitude != 0 and current_fix.longitude != 0 and
                           -90 <= current_fix.latitude <= 90 and -180 <= current_fix.longitude <= 180)
            print(f"  Coordinates pass validation: {coords_valid}")
            
        else:
            print("❌ No GPS fix obtained")
        
        gps.disconnect()
        return current_fix
        
    except Exception as e:
        print(f"❌ GPS test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def test_image_metadata_creation(gps_fix):
    """Test image metadata creation with GPS fix."""
    print("\n=== IMAGE METADATA TEST ===")
    
    try:
        from config import ConfigManager
        from image_processor import ImageProcessor
        import numpy as np
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        print(f"Enable metadata: {config.get('enable_metadata', False)}")
        print(f"Image format: {config.get('image_format', 'NOT SET')}")
        
        # Create processor
        processor = ImageProcessor(config)
        
        # Create test image
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        print(f"✓ Test frame created: {test_frame.shape}")
        
        # Process with GPS fix
        timestamp = datetime.utcnow()
        
        if gps_fix:
            print(f"Processing with GPS fix: {gps_fix.latitude:.6f}, {gps_fix.longitude:.6f}")
        else:
            print("Processing without GPS fix")
        
        processed_image = processor.process_frame(test_frame, gps_fix, timestamp)
        
        if processed_image:
            print(f"✓ Image processed: {len(processed_image)} bytes")
            
            # Save test image
            test_path = "gps_metadata_test.jpg"
            if processor.save_image(processed_image, test_path):
                print(f"✓ Test image saved: {test_path}")
                
                # Try to extract GPS metadata
                extracted_gps = processor.extract_gps_from_image(test_path)
                if extracted_gps:
                    print("✓ GPS metadata successfully extracted:")
                    print(f"  Extracted lat: {extracted_gps['latitude']:.6f}")
                    print(f"  Extracted lon: {extracted_gps['longitude']:.6f}")
                    
                    # Compare with original
                    if gps_fix:
                        lat_diff = abs(extracted_gps['latitude'] - gps_fix.latitude)
                        lon_diff = abs(extracted_gps['longitude'] - gps_fix.longitude)
                        print(f"  Latitude diff: {lat_diff:.8f}")
                        print(f"  Longitude diff: {lon_diff:.8f}")
                        
                        if lat_diff < 0.001 and lon_diff < 0.001:
                            print("✓ GPS coordinates match original data")
                        else:
                            print("⚠️  GPS coordinates don't match original")
                else:
                    print("❌ No GPS metadata found in saved image")
                    
                    # Try manual EXIF check
                    try:
                        from PIL import Image
                        import piexif
                        
                        with Image.open(test_path) as img:
                            exif_data = img.info.get('exif')
                            if exif_data:
                                print("EXIF data is present, but no GPS section")
                                exif_dict = piexif.load(exif_data)
                                print(f"EXIF sections: {list(exif_dict.keys())}")
                                for section, data in exif_dict.items():
                                    if data:
                                        print(f"  {section}: {len(data) if isinstance(data, dict) else 'non-dict'}")
                            else:
                                print("No EXIF data in image at all")
                    except Exception as e:
                        print(f"Manual EXIF check failed: {e}")
                
                # Clean up test file
                try:
                    os.remove(test_path)
                except:
                    pass
                
            else:
                print("❌ Failed to save test image")
        else:
            print("❌ Image processing failed")
            
    except Exception as e:
        print(f"❌ Image metadata test failed: {e}")
        import traceback
        print(traceback.format_exc())

def create_mock_gps_fix():
    """Create a mock GPS fix for testing."""
    print("\n=== CREATING MOCK GPS FIX ===")
    
    try:
        from gps import GPSFix
        from datetime import datetime
        
        # Create a realistic GPS fix
        mock_fix = GPSFix(
            latitude=40.7128,  # NYC coordinates
            longitude=-74.0060,
            altitude=10.0,
            timestamp=datetime.utcnow(),
            fix_quality=2,  # DGPS fix
            satellites=8,
            horizontal_dilution=1.2,
            fix_mode='3D'
        )
        
        print(f"✓ Mock GPS fix created:")
        print(f"  Lat: {mock_fix.latitude}")
        print(f"  Lon: {mock_fix.longitude}")
        print(f"  Valid: {mock_fix.is_valid}")
        
        return mock_fix
        
    except Exception as e:
        print(f"❌ Failed to create mock GPS fix: {e}")
        return None

def main():
    """Main test function."""
    print("BathyCat GPS Fix and Metadata Test")
    print("=" * 45)
    
    # Setup logging to see detailed messages
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test 1: Try to get real GPS fix
    gps_fix = test_gps_fix()
    
    # Test 2: If no real GPS, create mock fix
    if not gps_fix:
        print("\n⚠️  No real GPS fix available, testing with mock data")
        gps_fix = create_mock_gps_fix()
    
    # Test 3: Test image metadata creation
    if gps_fix:
        test_image_metadata_creation(gps_fix)
    
    # Test 4: Test without GPS fix
    print("\n=== TESTING WITHOUT GPS FIX ===")
    test_image_metadata_creation(None)
    
    print("\n=== SUMMARY ===")
    if gps_fix:
        print("✓ GPS functionality appears to be working")
        print("If GPS metadata is still missing from real images:")
        print("1. Check service logs: sudo journalctl -u bathyimager -f")
        print("2. Ensure GPS has outdoor signal during image capture")
        print("3. Verify 'enable_metadata': true in config")
    else:
        print("❌ GPS not working - check connection and outdoor signal")

if __name__ == "__main__":
    main()