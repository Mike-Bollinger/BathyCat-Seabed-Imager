#!/usr/bin/env python3
"""
Test script to verify EXIF metadata is being properly embedded in images
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import piexif
import logging

def test_image_metadata(image_path):
    """Test if an image has the expected metadata"""
    print(f"Testing image: {image_path}")
    
    try:
        # Open the image
        image = Image.open(image_path)
        print(f"Image size: {image.size}")
        print(f"Image mode: {image.mode}")
        
        # Get EXIF data
        exif_dict = piexif.load(image_path)
        
        print("\n=== EXIF Data Analysis ===")
        
        # Check GPS data
        if "GPS" in exif_dict and exif_dict["GPS"]:
            print("GPS Data found:")
            gps = exif_dict["GPS"]
            for tag_id, value in gps.items():
                tag_name = piexif.GPSIFD.get(tag_id, f"Unknown GPS tag {tag_id}")
                print(f"  {tag_name}: {value}")
        else:
            print("No GPS data found")
        
        # Check 0th IFD (main image data)
        if "0th" in exif_dict and exif_dict["0th"]:
            print("\nMain Image Data:")
            ifd = exif_dict["0th"]
            for tag_id, value in ifd.items():
                tag_name = piexif.ImageIFD.get(tag_id, f"Unknown tag {tag_id}")
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except:
                        value = f"<bytes: {len(value)} chars>"
                print(f"  {tag_name}: {value}")
        else:
            print("No main image data found")
            
        # Check EXIF IFD
        if "Exif" in exif_dict and exif_dict["Exif"]:
            print("\nEXIF Data:")
            exif_ifd = exif_dict["Exif"]
            for tag_id, value in exif_ifd.items():
                tag_name = piexif.ExifIFD.get(tag_id, f"Unknown EXIF tag {tag_id}")
                print(f"  {tag_name}: {value}")
        else:
            print("No EXIF IFD data found")
            
        # Check 1st IFD (thumbnail data)
        if "1st" in exif_dict and exif_dict["1st"]:
            print("\nThumbnail Data:")
            print(f"  Thumbnail size: {len(exif_dict.get('thumbnail', b''))} bytes")
        
        return True
        
    except Exception as e:
        print(f"Error reading image metadata: {e}")
        return False

def main():
    """Main test function"""
    # Check if image path provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Look for recent images
        import glob
        import datetime
        
        # Try different possible locations
        possible_paths = [
            "/media/usb/bathyimager/**/*.jpg",
            "/tmp/*.jpg",
            "*.jpg"
        ]
        
        image_files = []
        for pattern in possible_paths:
            image_files.extend(glob.glob(pattern, recursive=True))
        
        if not image_files:
            print("No image files found. Please provide an image path as argument.")
            print("Usage: python test_metadata.py <image_path>")
            return
        
        # Use the most recent image
        image_path = max(image_files, key=os.path.getctime)
        print(f"Using most recent image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return
    
    test_image_metadata(image_path)

if __name__ == "__main__":
    main()