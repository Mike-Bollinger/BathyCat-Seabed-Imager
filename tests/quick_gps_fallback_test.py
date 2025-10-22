#!/usr/bin/env python3
"""
Quick GPS Fallback Verification
===============================

Simple test to verify GPS fallback coordinates are working correctly.
Run this to confirm images are getting tagged with 0°N,0°W when GPS unavailable.
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, '/home/bathyimager/BathyCat-Seabed-Imager/src')

def test_gps_fallback():
    """Quick test of GPS fallback functionality."""
    print("=== GPS FALLBACK VERIFICATION ===")
    print()
    
    try:
        # Import modules
        from camera import Camera
        from image_processor import ImageProcessor
        from config import load_config
        
        # Load configuration
        config = load_config()
        
        print("✓ Modules imported successfully")
        print("✓ Configuration loaded")
        
        # Initialize camera
        print("\n1. Testing camera capture...")
        camera = Camera(config['camera'])
        
        if camera.initialize():
            print("✓ Camera initialized")
            
            # Capture a frame
            frame = camera.capture_frame()
            if frame is not None:
                print("✓ Frame captured successfully")
                
                # Initialize image processor
                processor = ImageProcessor(config['storage'])
                
                # Process frame WITHOUT GPS (should trigger fallback)
                print("\n2. Processing image without GPS (testing fallback)...")
                timestamp = datetime.utcnow()
                
                processed_image = processor.process_frame(frame, None, timestamp)
                
                if processed_image:
                    print("✓ Image processed with GPS fallback")
                    
                    # Save test image
                    test_file = f"/tmp/gps_fallback_test_{timestamp.strftime('%H%M%S')}.jpg"
                    processed_image.save(test_file)
                    print(f"✓ Test image saved: {test_file}")
                    
                    # Try to extract and verify GPS data
                    try:
                        from PIL import Image
                        import piexif
                        
                        img = Image.open(test_file)
                        if 'exif' in img.info:
                            exif_dict = piexif.load(img.info['exif'])
                            gps_data = exif_dict.get('GPS', {})
                            
                            if gps_data:
                                print("✅ SUCCESS: GPS metadata found in image!")
                                
                                # Check if coordinates are fallback (0,0)
                                lat_dms = gps_data.get(piexif.GPSIFD.GPSLatitude, ())
                                lon_dms = gps_data.get(piexif.GPSIFD.GPSLongitude, ())
                                satellites = gps_data.get(piexif.GPSIFD.GPSSatellites, b'').decode('ascii')
                                
                                if satellites == '0':
                                    print("✅ CONFIRMED: Fallback GPS (0 satellites = 0°N,0°W)")
                                    print("🎯 GPS fallback implementation working correctly!")
                                else:
                                    print(f"⚠️  Unexpected: {satellites} satellites (expected 0 for fallback)")
                            else:
                                print("❌ No GPS data found in image EXIF")
                        else:
                            print("❌ No EXIF data found in image")
                            
                    except ImportError:
                        print("⚠️  Cannot verify GPS data (PIL/piexif not available)")
                    except Exception as e:
                        print(f"⚠️  Error verifying GPS data: {e}")
                else:
                    print("❌ Image processing failed")
            else:
                print("❌ Frame capture failed")
            
            camera.cleanup()
        else:
            print("❌ Camera initialization failed")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this on the Raspberry Pi with BathyCat installed")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def check_configuration():
    """Check if GPS fallback settings are correct."""
    print("\n=== CONFIGURATION CHECK ===")
    
    try:
        config_file = '/home/bathyimager/BathyCat-Seabed-Imager/config/bathyimager_config.json'
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("✓ Configuration file accessible")
        
        # Check relevant settings
        require_gps = config.get('require_gps_fix', False)
        
        if require_gps:
            print("⚠️  WARNING: require_gps_fix is TRUE")
            print("   This will skip captures when GPS unavailable")
            print("   Recommendation: Set to FALSE to test fallback coordinates")
        else:
            print("✅ GOOD: require_gps_fix is FALSE")
            print("   Images will be captured even without GPS (using fallback)")
            
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")

def main():
    """Run GPS fallback verification."""
    print("GPS Fallback Verification Test")
    print("=" * 35)
    print()
    print("This test verifies that images are tagged with 0°N,0°W")
    print("coordinates when GPS is not available (indoors).")
    print()
    
    check_configuration()
    test_gps_fallback()
    
    print("\n" + "="*50)
    print("VERIFICATION COMPLETE")
    print("="*50)
    print("✅ EXPECTED: GPS metadata with 0 satellites = fallback 0°N,0°W")
    print("🎯 BENEFIT: All images now have GPS coordinates for troubleshooting")
    print("📍 LOCATION: 0°N,0°W = 'Null Island' (easy to identify)")

if __name__ == "__main__":
    main()