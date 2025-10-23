#!/usr/bin/env python3
"""
Test script to verify EXIF metadata functionality
Creates a test image and verifies metadata is properly embedded
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from PIL import Image
from datetime import datetime
import tempfile
import logging

# Import our modules
from image_processor import ImageProcessor
from gps import GPSFix

def create_test_image():
    """Create a test image using numpy"""
    # Create a simple test image (480x640, RGB)
    img_array = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    # Add some pattern so it's not just noise
    img_array[100:200, 100:200] = [255, 0, 0]  # Red square
    img_array[300:400, 400:500] = [0, 255, 0]  # Green square
    
    return Image.fromarray(img_array, 'RGB')

def create_test_gps_fix():
    """Create a test GPS fix"""
    fix = GPSFix()
    fix.latitude = 40.7128  # New York City
    fix.longitude = -74.0060
    fix.altitude = 10.0
    fix.speed = 0.0
    fix.course = 0.0
    fix.satellites = 8
    fix.fix_quality = 1
    fix.timestamp = datetime.utcnow()
    return fix

def create_test_camera_params():
    """Create test camera parameters"""
    return {
        'make': 'BathyImager',
        'model': 'BathyImager',
        'exposure_time': (1, 30),  # 1/30 second
        'f_number': (28, 10),  # f/2.8
        'iso_speed': 100,
        'focal_length': (35, 10),  # 3.5mm
        'white_balance': 0,  # Auto
        'flash': 0,  # No flash
        'color_space': 1,  # sRGB
    }

def main():
    """Test the metadata functionality"""
    print("=== BathyCat EXIF Metadata Test ===\n")
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create test image
    print("Creating test image...")
    test_image = create_test_image()
    print(f"Test image created: {test_image.size} {test_image.mode}")
    
    # Create test GPS fix
    print("Creating test GPS fix...")
    gps_fix = create_test_gps_fix()
    print(f"GPS fix: {gps_fix.latitude:.6f}, {gps_fix.longitude:.6f}")
    
    # Create test camera parameters
    print("Creating test camera parameters...")
    camera_params = create_test_camera_params()
    print(f"Camera params: {len(camera_params)} parameters")
    
    # Create image processor (use default config)
    print("Initializing image processor...")
    config = {
        'jpeg_quality': 85,
        'enable_metadata': True
    }
    processor = ImageProcessor(config)
    
    # Process the image
    print("Processing image with metadata...")
    timestamp = datetime.utcnow()
    processed_image = processor.process_frame(test_image, gps_fix, timestamp, camera_params)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        temp_path = tmp_file.name
        
    print(f"Saving processed image to: {temp_path}")
    processed_image.save(temp_path, 'JPEG', quality=85)
    
    # Test the metadata
    print("\n=== Testing Saved Image Metadata ===")
    
    # Import our test function
    sys.path.append(os.path.dirname(__file__))
    from test_metadata import test_image_metadata
    
    success = test_image_metadata(temp_path)
    
    print(f"\nTest completed. Image saved at: {temp_path}")
    print("You can examine this file with any EXIF viewer to verify metadata.")
    
    if success:
        print("✓ Metadata test PASSED - EXIF data found in image")
    else:
        print("✗ Metadata test FAILED - No EXIF data found")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)