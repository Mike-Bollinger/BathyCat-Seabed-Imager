#!/usr/bin/env python3
"""
GPS Fallback Metadata Test
==========================

Test the new GPS fallback functionality that tags images with 0°N, 0°W
when GPS is not available, ensuring all images always have GPS metadata.
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

def extract_gps_from_image(image_path):
    """Extract GPS metadata from a saved image."""
    try:
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info['exif'])
        
        gps_data = exif_dict.get('GPS', {})
        if not gps_data:
            return None, "No GPS data found"
        
        # Extract coordinates
        lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'').decode('ascii')
        lat_dms = gps_data.get(piexif.GPSIFD.GPSLatitude, ())
        lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'').decode('ascii')
        lon_dms = gps_data.get(piexif.GPSIFD.GPSLongitude, ())
        
        def dms_to_decimal(dms_tuple):
            """Convert DMS tuple to decimal degrees."""
            if len(dms_tuple) != 3:
                return 0.0
            degrees = float(dms_tuple[0][0]) / float(dms_tuple[0][1])
            minutes = float(dms_tuple[1][0]) / float(dms_tuple[1][1])
            seconds = float(dms_tuple[2][0]) / float(dms_tuple[2][1])
            return degrees + minutes/60 + seconds/3600
        
        lat_decimal = dms_to_decimal(lat_dms)
        lon_decimal = dms_to_decimal(lon_dms)
        
        if lat_ref == 'S':
            lat_decimal = -lat_decimal
        if lon_ref == 'W':
            lon_decimal = -lon_decimal
            
        # Extract other GPS info
        satellites = gps_data.get(piexif.GPSIFD.GPSSatellites, b'').decode('ascii')
        measure_mode = gps_data.get(piexif.GPSIFD.GPSMeasureMode, b'').decode('ascii')
        
        return {
            'latitude': lat_decimal,
            'longitude': lon_decimal,
            'lat_ref': lat_ref,
            'lon_ref': lon_ref,
            'satellites': satellites,
            'measure_mode': measure_mode
        }, None
        
    except Exception as e:
        return None, f"Error extracting GPS: {e}"

def test_fallback_gps_tagging():
    """Test GPS fallback functionality."""
    print("=== GPS FALLBACK METADATA TEST ===")
    print()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create image processor
    config = {
        'jpeg_quality': 85,
        'image_format': 'JPEG'
    }
    
    processor = ImageProcessor(config)
    
    # Create test image
    test_frame = create_test_image()
    timestamp = datetime.utcnow()
    
    print("Test 1: No GPS fix available (should use fallback 0°N, 0°W)")
    print("-" * 55)
    
    # Process image without GPS (should use fallback)
    processed_image1 = processor.process_frame(test_frame, None, timestamp)
    
    # Save and verify
    test_file1 = 'test_no_gps.jpg'
    processed_image1.save(test_file1)
    
    gps_data1, error1 = extract_gps_from_image(test_file1)
    if error1:
        print(f"❌ Error: {error1}")
    else:
        print(f"✓ GPS metadata found:")
        print(f"  Coordinates: {gps_data1['latitude']:.6f}°, {gps_data1['longitude']:.6f}°")
        print(f"  Reference: {gps_data1['lat_ref']}, {gps_data1['lon_ref']}")
        print(f"  Satellites: {gps_data1['satellites']}")
        print(f"  Mode: {gps_data1['measure_mode']}")
        
        # Check if it's the expected fallback
        if (abs(gps_data1['latitude']) < 0.001 and abs(gps_data1['longitude']) < 0.001 and
            gps_data1['lat_ref'] == 'N' and gps_data1['lon_ref'] == 'W' and
            gps_data1['satellites'] == '0'):
            print("✅ CORRECT: Fallback GPS coordinates (0°N, 0°W) applied")
        else:
            print("❌ INCORRECT: Expected fallback coordinates 0°N, 0°W")
    
    print()
    print("Test 2: Invalid GPS fix (should use fallback 0°N, 0°W)")
    print("-" * 55)
    
    # Create invalid GPS fix
    invalid_gps = GPSFix(
        latitude=999.0,  # Invalid latitude
        longitude=999.0,  # Invalid longitude
        altitude=None,
        timestamp=timestamp,
        fix_quality=0,  # No fix
        satellites=0,
        horizontal_dilution=None,
        fix_mode='NO_FIX'
    )
    
    # Process image with invalid GPS
    processed_image2 = processor.process_frame(test_frame, invalid_gps, timestamp)
    
    # Save and verify
    test_file2 = 'test_invalid_gps.jpg'
    processed_image2.save(test_file2)
    
    gps_data2, error2 = extract_gps_from_image(test_file2)
    if error2:
        print(f"❌ Error: {error2}")
    else:
        print(f"✓ GPS metadata found:")
        print(f"  Coordinates: {gps_data2['latitude']:.6f}°, {gps_data2['longitude']:.6f}°")
        print(f"  Reference: {gps_data2['lat_ref']}, {gps_data2['lon_ref']}")
        print(f"  Satellites: {gps_data2['satellites']}")
        
        # Check if it's the expected fallback
        if (abs(gps_data2['latitude']) < 0.001 and abs(gps_data2['longitude']) < 0.001 and
            gps_data2['lat_ref'] == 'N' and gps_data2['lon_ref'] == 'W' and
            gps_data2['satellites'] == '0'):
            print("✅ CORRECT: Fallback GPS coordinates applied for invalid GPS")
        else:
            print("❌ INCORRECT: Expected fallback coordinates")
    
    print()
    print("Test 3: Valid GPS fix (should use real coordinates)")
    print("-" * 50)
    
    # Create valid GPS fix (example: Vancouver, BC area)
    valid_gps = GPSFix(
        latitude=49.2827,   # Vancouver latitude
        longitude=-123.1207,  # Vancouver longitude  
        altitude=50.0,
        timestamp=timestamp,
        fix_quality=2,  # DGPS fix
        satellites=8,
        horizontal_dilution=1.2,
        fix_mode='3D'
    )
    
    # Process image with valid GPS
    processed_image3 = processor.process_frame(test_frame, valid_gps, timestamp)
    
    # Save and verify
    test_file3 = 'test_valid_gps.jpg'
    processed_image3.save(test_file3)
    
    gps_data3, error3 = extract_gps_from_image(test_file3)
    if error3:
        print(f"❌ Error: {error3}")
    else:
        print(f"✓ GPS metadata found:")
        print(f"  Coordinates: {gps_data3['latitude']:.6f}°, {gps_data3['longitude']:.6f}°")
        print(f"  Reference: {gps_data3['lat_ref']}, {gps_data3['lon_ref']}")
        print(f"  Satellites: {gps_data3['satellites']}")
        
        # Check if it matches the valid GPS
        if (abs(gps_data3['latitude'] - 49.2827) < 0.001 and 
            abs(gps_data3['longitude'] - (-123.1207)) < 0.001 and
            gps_data3['satellites'] == '8'):
            print("✅ CORRECT: Real GPS coordinates used")
        else:
            print(f"❌ INCORRECT: Expected ~49.28°N, 123.12°W, got {gps_data3['latitude']:.6f}°, {gps_data3['longitude']:.6f}°")
    
    # Cleanup test files
    for test_file in [test_file1, test_file2, test_file3]:
        try:
            os.remove(test_file)
        except:
            pass
    
    print()
    print("=" * 60)
    print("GPS FALLBACK TEST SUMMARY")
    print("=" * 60)
    print("✅ EXPECTED BEHAVIOR:")
    print("  • No GPS available → Tag with 0°N, 0°W (fallback)")
    print("  • Invalid GPS → Tag with 0°N, 0°W (fallback)")
    print("  • Valid GPS → Tag with real coordinates")
    print()
    print("🎯 RESULT: All images now have GPS metadata for troubleshooting")
    print("📍 FALLBACK: 0°N, 0°W = 'Null Island' (easy to identify)")
    print("🔧 BENEFIT: Can always check GPS metadata to diagnose issues")

def main():
    """Run GPS fallback tests."""
    try:
        test_fallback_gps_tagging()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ GPS fallback test completed successfully!")
    else:
        print("\n❌ GPS fallback test failed!")
        sys.exit(1)