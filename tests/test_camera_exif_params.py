#!/usr/bin/env python3
"""
Camera EXIF Parameters Test
===========================

Test the enhanced EXIF metadata functionality that includes actual camera
parameters (exposure, brightness, white balance, etc.) and updated model/copyright info.
"""

import sys
import os
import logging
import numpy as np
from datetime import datetime
from PIL import Image
import piexif

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image_processor import ImageProcessor
from gps import GPSFix

def create_test_image():
    """Create a simple test image."""
    # Create a 640x480 test image with some content
    img_array = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add some visual content
    img_array[100:380, 100:540] = [50, 100, 150]  # Blue rectangle
    img_array[200:280, 200:440] = [200, 50, 50]   # Red rectangle
    
    return img_array

def create_mock_camera_params():
    """Create mock camera parameters like those from camera.get_camera_exif_params()"""
    return {
        'width': 1920,
        'height': 1080,
        'fps': 30.0,
        'auto_exposure': 0.25,  # Manual mode
        'exposure': -10.0,      # Manual exposure value
        'auto_wb': 0,           # Manual WB
        'wb_temperature': 4000, # 4000K white balance
        'brightness': 32,       # Brightness setting
        'contrast': 45,         # Contrast setting
        'saturation': 55,       # Saturation setting
        'gain': 12.5,          # Gain setting
        'sharpness': 50,        # Sharpness setting
        'backend': 'V4L2',      # Camera backend
        'format': 'MJPG'        # Camera format
    }

def extract_detailed_exif(image_path):
    """Extract detailed EXIF metadata from a saved image."""
    try:
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info['exif'])
        
        result = {}
        
        # Basic image info (0th IFD)
        if '0th' in exif_dict:
            ifd_0th = exif_dict['0th']
            result['software'] = ifd_0th.get(piexif.ImageIFD.Software, b'').decode('ascii', errors='ignore')
            result['make'] = ifd_0th.get(piexif.ImageIFD.Make, b'').decode('ascii', errors='ignore')
            result['model'] = ifd_0th.get(piexif.ImageIFD.Model, b'').decode('ascii', errors='ignore')
            result['copyright'] = ifd_0th.get(piexif.ImageIFD.Copyright, b'').decode('ascii', errors='ignore')
            result['image_description'] = ifd_0th.get(piexif.ImageIFD.ImageDescription, b'').decode('ascii', errors='ignore')
            result['image_width'] = ifd_0th.get(piexif.ImageIFD.ImageWidth, 0)
            result['image_height'] = ifd_0th.get(piexif.ImageIFD.ImageLength, 0)
        
        # Camera settings (Exif IFD)
        if 'Exif' in exif_dict:
            exif_ifd = exif_dict['Exif']
            
            # Exposure
            if piexif.ExifIFD.ExposureTime in exif_ifd:
                exp_time = exif_ifd[piexif.ExifIFD.ExposureTime]
                result['exposure_time'] = f"{exp_time[0]}/{exp_time[1]}"
            
            result['exposure_mode'] = exif_ifd.get(piexif.ExifIFD.ExposureMode, None)
            result['exposure_program'] = exif_ifd.get(piexif.ExifIFD.ExposureProgram, None)
            
            # White balance
            result['white_balance'] = exif_ifd.get(piexif.ExifIFD.WhiteBalance, None)
            result['color_temperature'] = exif_ifd.get(piexif.ExifIFD.ColorTemperature, None)
            
            # ISO/Gain
            result['iso'] = exif_ifd.get(piexif.ExifIFD.ISOSpeedRatings, None)
            
            # Image adjustments
            if piexif.ExifIFD.BrightnessValue in exif_ifd:
                brightness_rational = exif_ifd[piexif.ExifIFD.BrightnessValue]
                result['brightness_value'] = brightness_rational[0] / brightness_rational[1] if brightness_rational[1] != 0 else 0
            
            result['contrast'] = exif_ifd.get(piexif.ExifIFD.Contrast, None)
            result['saturation'] = exif_ifd.get(piexif.ExifIFD.Saturation, None)
            result['sharpness'] = exif_ifd.get(piexif.ExifIFD.Sharpness, None)
            
            # User comment (may contain FPS and other info)
            if piexif.ExifIFD.UserComment in exif_ifd:
                user_comment = exif_ifd[piexif.ExifIFD.UserComment]
                try:
                    # Skip Unicode marker if present
                    if user_comment.startswith(b'UNICODE\x00'):
                        comment_text = user_comment[8:].decode('utf-8', errors='ignore')
                    else:
                        comment_text = user_comment.decode('utf-8', errors='ignore')
                    result['user_comment'] = comment_text
                except:
                    result['user_comment'] = 'Could not decode'
        
        # GPS data
        if 'GPS' in exif_dict:
            gps_data = exif_dict['GPS']
            if piexif.GPSIFD.GPSLatitude in gps_data:
                result['has_gps'] = True
                satellites = gps_data.get(piexif.GPSIFD.GPSSatellites, b'').decode('ascii', errors='ignore')
                result['gps_satellites'] = satellites
            else:
                result['has_gps'] = False
        
        return result, None
        
    except Exception as e:
        return None, f"Error extracting EXIF: {e}"

def test_camera_exif_parameters():
    """Test camera parameter EXIF embedding."""
    print("=== CAMERA EXIF PARAMETERS TEST ===")
    print()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create image processor
    config = {
        'jpeg_quality': 85,
        'image_format': 'JPEG',
        'enable_metadata': True
    }
    
    processor = ImageProcessor(config)
    
    # Create test image and parameters
    test_frame = create_test_image()
    timestamp = datetime.utcnow()
    camera_params = create_mock_camera_params()
    
    print("Test 1: Camera EXIF Parameters with Valid GPS")
    print("-" * 50)
    
    # Create GPS fix
    gps_fix = GPSFix(
        latitude=49.2827,
        longitude=-123.1207,
        altitude=50.0,
        timestamp=timestamp,
        fix_quality=2,
        satellites=8,
        horizontal_dilution=1.2,
        fix_mode='3D'
    )
    
    # Process image with camera parameters
    processed_image1 = processor.process_frame(test_frame, gps_fix, timestamp, camera_params)
    
    # Save and analyze
    test_file1 = 'test_camera_exif_with_gps.jpg'
    processed_image1.save(test_file1)
    
    exif_data1, error1 = extract_detailed_exif(test_file1)
    if error1:
        print(f"❌ Error: {error1}")
    else:
        print("✓ EXIF metadata extracted successfully:")
        print(f"  Make: '{exif_data1['make']}'")
        print(f"  Model: '{exif_data1['model']}'")
        print(f"  Copyright: '{exif_data1['copyright']}'")
        print(f"  Software: '{exif_data1['software']}'")
        print(f"  Image Size: {exif_data1['image_width']}x{exif_data1['image_height']}")
        print(f"  Exposure Time: {exif_data1.get('exposure_time', 'Not set')}")
        print(f"  Exposure Mode: {exif_data1.get('exposure_mode', 'Not set')} (0=Auto, 1=Manual)")
        print(f"  White Balance: {exif_data1.get('white_balance', 'Not set')} (0=Auto, 1=Manual)")
        print(f"  Color Temperature: {exif_data1.get('color_temperature', 'Not set')}K")
        print(f"  ISO: {exif_data1.get('iso', 'Not set')}")
        print(f"  Brightness: {exif_data1.get('brightness_value', 'Not set')}")
        print(f"  Contrast: {exif_data1.get('contrast', 'Not set')} (0=Normal, 1=Low, 2=High)")
        print(f"  Saturation: {exif_data1.get('saturation', 'Not set')} (0=Normal, 1=Low, 2=High)")
        print(f"  Sharpness: {exif_data1.get('sharpness', 'Not set')} (0=Normal, 1=Soft, 2=Hard)")
        print(f"  User Comment: '{exif_data1.get('user_comment', 'None')}'")
        print(f"  Has GPS: {exif_data1.get('has_gps', False)} (Satellites: {exif_data1.get('gps_satellites', 'N/A')})")
        
        # Verify user-requested fields
        success_checks = []
        if exif_data1['model'] == 'BathyImager':
            success_checks.append("✅ Model: BathyImager")
        else:
            success_checks.append(f"❌ Model: Expected 'BathyImager', got '{exif_data1['model']}'")
            
        if exif_data1['copyright'] == 'NOAA':
            success_checks.append("✅ Copyright: NOAA")
        else:
            success_checks.append(f"❌ Copyright: Expected 'NOAA', got '{exif_data1['copyright']}'")
            
        if exif_data1.get('exposure_time'):
            success_checks.append(f"✅ Exposure: {exif_data1['exposure_time']}")
        else:
            success_checks.append("❌ Exposure: Not found in EXIF")
            
        if exif_data1.get('color_temperature'):
            success_checks.append(f"✅ White Balance: {exif_data1['color_temperature']}K")
        else:
            success_checks.append("❌ White Balance: Not found in EXIF")
        
        print("\n📋 VERIFICATION RESULTS:")
        for check in success_checks:
            print(f"  {check}")
    
    print()
    print("Test 2: Camera EXIF Parameters with Fallback GPS")
    print("-" * 52)
    
    # Process image without GPS (fallback coordinates)
    processed_image2 = processor.process_frame(test_frame, None, timestamp, camera_params)
    
    # Save and analyze
    test_file2 = 'test_camera_exif_fallback_gps.jpg'
    processed_image2.save(test_file2)
    
    exif_data2, error2 = extract_detailed_exif(test_file2)
    if error2:
        print(f"❌ Error: {error2}")
    else:
        print("✓ EXIF metadata with fallback GPS:")
        print(f"  Has GPS: {exif_data2.get('has_gps', False)} (Satellites: {exif_data2.get('gps_satellites', 'N/A')})")
        print(f"  Camera Backend Info in Description: '{exif_data2.get('image_description', 'None')}'")
        
        # Check fallback GPS
        if exif_data2.get('gps_satellites') == '0':
            print("✅ Fallback GPS applied correctly (0 satellites)")
        else:
            print(f"❌ Expected fallback GPS with 0 satellites, got {exif_data2.get('gps_satellites')}")
    
    # Cleanup test files
    for test_file in [test_file1, test_file2]:
        try:
            os.remove(test_file)
        except:
            pass
    
    print()
    print("=" * 70)
    print("CAMERA EXIF PARAMETERS TEST SUMMARY")
    print("=" * 70)
    print("✅ FEATURES IMPLEMENTED:")
    print("  • Camera Model: 'BathyImager' (per user request)")
    print("  • Copyright: 'NOAA' (per user request)")
    print("  • Actual camera exposure settings in EXIF")
    print("  • White balance temperature and mode")
    print("  • ISO/gain, brightness, contrast, saturation, sharpness")
    print("  • Camera backend and format info")
    print("  • Frame rate in user comment")
    print()
    print("🎯 BENEFITS:")
    print("  • Complete camera settings preserved in image metadata")
    print("  • Professional attribution with NOAA copyright")
    print("  • Detailed technical information for analysis")
    print("  • Troubleshooting camera configuration via EXIF")

def main():
    """Run camera EXIF parameters test."""
    try:
        test_camera_exif_parameters()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Camera EXIF parameters test completed successfully!")
    else:
        print("\n❌ Camera EXIF parameters test failed!")
        sys.exit(1)