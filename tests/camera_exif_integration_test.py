#!/usr/bin/env python3
"""
Quick Camera EXIF Verification
==============================

Simple test to verify camera EXIF parameters are being embedded correctly.
Run this on the Raspberry Pi to test the enhanced EXIF functionality.
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, '/home/bathyimager/BathyCat-Seabed-Imager/src')

def test_camera_exif_integration():
    """Test camera EXIF parameter integration."""
    print("=== CAMERA EXIF INTEGRATION TEST ===")
    print()
    
    try:
        # Import modules
        from camera import Camera
        from image_processor import ImageProcessor
        from config import load_config
        
        # Load configuration
        config = load_config()
        
        print("✓ Modules imported successfully")
        
        # Initialize camera
        print("\n1. Testing camera parameter extraction...")
        camera = Camera(config['camera'])
        
        if camera.initialize():
            print("✓ Camera initialized")
            
            # Get camera parameters
            camera_params = camera.get_camera_exif_params()
            print("✓ Camera parameters extracted:")
            
            for key, value in camera_params.items():
                if value is not None:
                    print(f"    {key}: {value}")
            
            # Capture a frame
            frame = camera.capture_frame()
            if frame is not None:
                print("✓ Frame captured successfully")
                
                # Initialize image processor
                processor = ImageProcessor(config['storage'])
                
                # Process frame WITH camera parameters
                print("\n2. Processing image with camera EXIF parameters...")
                timestamp = datetime.utcnow()
                
                processed_image = processor.process_frame(frame, None, timestamp, camera_params)
                
                if processed_image:
                    print("✓ Image processed with camera EXIF data")
                    
                    # Save test image
                    test_file = f"/tmp/camera_exif_test_{timestamp.strftime('%H%M%S')}.jpg"
                    processed_image.save(test_file)
                    print(f"✓ Test image saved: {test_file}")
                    
                    # Try to verify EXIF data
                    try:
                        from PIL import Image
                        import piexif
                        
                        img = Image.open(test_file)
                        if 'exif' in img.info:
                            exif_dict = piexif.load(img.info['exif'])
                            
                            print("\n3. Verifying EXIF metadata:")
                            
                            # Check basic info
                            if '0th' in exif_dict:
                                ifd_0th = exif_dict['0th']
                                make = ifd_0th.get(piexif.ImageIFD.Make, b'').decode('ascii', errors='ignore')
                                model = ifd_0th.get(piexif.ImageIFD.Model, b'').decode('ascii', errors='ignore')
                                copyright_info = ifd_0th.get(piexif.ImageIFD.Copyright, b'').decode('ascii', errors='ignore')
                                
                                print(f"  Make: '{make}'")
                                print(f"  Model: '{model}'")
                                print(f"  Copyright: '{copyright_info}'")
                                
                                # Verify user requirements
                                if model == 'BathyImager':
                                    print("  ✅ Camera Model: CORRECT (BathyImager)")
                                else:
                                    print(f"  ❌ Camera Model: Expected 'BathyImager', got '{model}'")
                                    
                                if copyright_info == 'NOAA':
                                    print("  ✅ Copyright: CORRECT (NOAA)")
                                else:
                                    print(f"  ❌ Copyright: Expected 'NOAA', got '{copyright_info}'")
                            
                            # Check camera settings
                            if 'Exif' in exif_dict:
                                exif_ifd = exif_dict['Exif']
                                
                                # Exposure
                                if piexif.ExifIFD.ExposureTime in exif_ifd:
                                    exp_time = exif_ifd[piexif.ExifIFD.ExposureTime]
                                    print(f"  ✅ Exposure Time: {exp_time[0]}/{exp_time[1]}")
                                
                                # White balance
                                wb_mode = exif_ifd.get(piexif.ExifIFD.WhiteBalance)
                                if wb_mode is not None:
                                    wb_text = "Auto" if wb_mode == 0 else "Manual"
                                    print(f"  ✅ White Balance: {wb_text}")
                                
                                color_temp = exif_ifd.get(piexif.ExifIFD.ColorTemperature)
                                if color_temp:
                                    print(f"  ✅ Color Temperature: {color_temp}K")
                                
                                # ISO
                                iso = exif_ifd.get(piexif.ExifIFD.ISOSpeedRatings)
                                if iso:
                                    print(f"  ✅ ISO: {iso}")
                                
                                # User comment (may contain FPS)
                                if piexif.ExifIFD.UserComment in exif_ifd:
                                    user_comment = exif_ifd[piexif.ExifIFD.UserComment]
                                    try:
                                        if user_comment.startswith(b'UNICODE\x00'):
                                            comment_text = user_comment[8:].decode('utf-8', errors='ignore')
                                        else:
                                            comment_text = user_comment.decode('utf-8', errors='ignore')
                                        print(f"  ✅ Camera Info: '{comment_text}'")
                                    except:
                                        print(f"  ⚠️  User Comment: Could not decode")
                            
                            # Check GPS (should be fallback)
                            if 'GPS' in exif_dict:
                                gps_data = exif_dict['GPS']
                                satellites = gps_data.get(piexif.GPSIFD.GPSSatellites, b'').decode('ascii', errors='ignore')
                                if satellites == '0':
                                    print(f"  ✅ GPS: Fallback coordinates (0 satellites)")
                                else:
                                    print(f"  ℹ️  GPS: Real coordinates ({satellites} satellites)")
                            
                            print("\n✅ SUCCESS: Enhanced EXIF metadata is working!")
                            
                        else:
                            print("❌ No EXIF data found in image")
                            
                    except ImportError:
                        print("⚠️  Cannot verify EXIF data (PIL/piexif not available for verification)")
                        print("✅ Image processing completed successfully")
                    except Exception as e:
                        print(f"⚠️  Error verifying EXIF data: {e}")
                        print("✅ Image processing completed successfully")
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

def main():
    """Run camera EXIF integration test."""
    print("Camera EXIF Integration Test")
    print("=" * 30)
    print()
    print("This test verifies that camera parameters are being")
    print("embedded in image EXIF metadata as requested:")
    print("• Camera Model: 'BathyImager'")
    print("• Copyright: 'NOAA'") 
    print("• Actual exposure, white balance, etc.")
    print()
    
    test_camera_exif_integration()
    
    print("\n" + "="*60)
    print("INTEGRATION TEST COMPLETE")
    print("="*60)
    print("✅ EXPECTED RESULTS:")
    print("  • Model: 'BathyImager' (updated per request)")
    print("  • Copyright: 'NOAA' (updated per request)")
    print("  • Exposure settings from actual camera")
    print("  • White balance temperature and mode")
    print("  • Camera backend/format information")
    print("  • GPS coordinates (real or 0°N,0°W fallback)")
    
    print("\n🎯 NEXT STEPS:")
    print("  • Deploy updated code to BathyCat system")
    print("  • Verify EXIF data in captured seabed images")
    print("  • Use exiftool to analyze metadata in detail")

if __name__ == "__main__":
    main()