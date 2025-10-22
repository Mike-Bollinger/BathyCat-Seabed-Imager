#!/usr/bin/env python3
"""
EXIF and Camera Analysis Script
=============================

This script analyzes the EXIF data from the provided images and investigates
camera exposure/white balance settings in detail.
"""

import sys
import os
from PIL import Image
import piexif
from PIL.ExifTags import TAGS

def analyze_exif_data(image_path):
    """Analyze EXIF data from an image file."""
    print(f"\n=== ANALYZING EXIF DATA: {os.path.basename(image_path)} ===")
    
    try:
        with Image.open(image_path) as img:
            print(f"Image size: {img.size}")
            print(f"Image mode: {img.mode}")
            
            # Check for EXIF data
            exif_data = img.info.get('exif')
            if not exif_data:
                print("❌ NO EXIF DATA FOUND")
                return
            
            # Parse EXIF with piexif
            try:
                exif_dict = piexif.load(exif_data)
                print("✓ EXIF data loaded successfully")
                
                # Check main EXIF sections
                sections = ['0th', 'Exif', 'GPS', 'Interop', '1st']
                for section in sections:
                    if section in exif_dict and exif_dict[section]:
                        print(f"✓ {section} section present: {len(exif_dict[section])} entries")
                    else:
                        print(f"❌ {section} section empty/missing")
                
                # GPS specific analysis
                if 'GPS' in exif_dict and exif_dict['GPS']:
                    print("\n--- GPS EXIF DATA ---")
                    gps_data = exif_dict['GPS']
                    for key, value in gps_data.items():
                        try:
                            if key == piexif.GPSIFD.GPSLatitude:
                                print(f"GPS Latitude: {value}")
                            elif key == piexif.GPSIFD.GPSLongitude:
                                print(f"GPS Longitude: {value}")
                            elif key == piexif.GPSIFD.GPSLatitudeRef:
                                print(f"GPS Latitude Ref: {value}")
                            elif key == piexif.GPSIFD.GPSLongitudeRef:
                                print(f"GPS Longitude Ref: {value}")
                            else:
                                print(f"GPS Key {key}: {value}")
                        except:
                            print(f"GPS Key {key}: {value}")
                else:
                    print("\n❌ NO GPS DATA IN EXIF")
                
                # Camera settings analysis
                if 'Exif' in exif_dict and exif_dict['Exif']:
                    print("\n--- CAMERA SETTINGS ---")
                    exif_section = exif_dict['Exif']
                    
                    # Look for exposure settings
                    exposure_keys = {
                        piexif.ExifIFD.ExposureTime: "Exposure Time",
                        piexif.ExifIFD.FNumber: "F Number", 
                        piexif.ExifIFD.ExposureProgram: "Exposure Program",
                        piexif.ExifIFD.ISOSpeedRatings: "ISO Speed",
                        piexif.ExifIFD.ExposureBiasValue: "Exposure Bias",
                        piexif.ExifIFD.MeteringMode: "Metering Mode",
                        piexif.ExifIFD.Flash: "Flash",
                        piexif.ExifIFD.WhiteBalance: "White Balance"
                    }
                    
                    for key, name in exposure_keys.items():
                        if key in exif_section:
                            print(f"{name}: {exif_section[key]}")
                        else:
                            print(f"{name}: NOT SET")
                
                # Software/camera info
                if '0th' in exif_dict and exif_dict['0th']:
                    print("\n--- CAMERA/SOFTWARE INFO ---")
                    main_section = exif_dict['0th']
                    
                    info_keys = {
                        piexif.ImageIFD.Make: "Camera Make",
                        piexif.ImageIFD.Model: "Camera Model", 
                        piexif.ImageIFD.Software: "Software",
                        piexif.ImageIFD.DateTime: "Date/Time",
                        piexif.ImageIFD.Artist: "Artist"
                    }
                    
                    for key, name in info_keys.items():
                        if key in main_section:
                            value = main_section[key]
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='ignore')
                            print(f"{name}: {value}")
                        else:
                            print(f"{name}: NOT SET")
                
            except Exception as e:
                print(f"❌ EXIF parsing error: {e}")
                
                # Try alternative EXIF reading
                print("\nTrying alternative EXIF reading...")
                try:
                    exif = img._getexif()
                    if exif:
                        print("✓ Alternative EXIF method worked")
                        for key, value in exif.items():
                            tag = TAGS.get(key, key)
                            print(f"{tag}: {value}")
                    else:
                        print("❌ No EXIF data via alternative method")
                except Exception as e2:
                    print(f"❌ Alternative EXIF method failed: {e2}")
                    
    except Exception as e:
        print(f"❌ Failed to open image: {e}")

def analyze_camera_issues():
    """Analyze potential camera exposure/white balance issues."""
    print("\n" + "="*60)
    print("CAMERA EXPOSURE/WHITE BALANCE ANALYSIS")
    print("="*60)
    
    print("\n🔍 POTENTIAL CAUSES OF WHITE IMAGES:")
    print("1. Extreme overexposure (too much light)")
    print("2. Manual exposure set too high")
    print("3. Auto-exposure malfunction")
    print("4. White balance severely incorrect")
    print("5. Camera sensor saturation")
    print("6. Incorrect camera initialization")
    
    print("\n🔧 INVESTIGATION STEPS:")
    print("1. Check actual OpenCV camera property values")
    print("2. Verify camera supports auto-exposure/WB")
    print("3. Test manual exposure settings")
    print("4. Check camera initialization sequence")
    print("5. Test with different cameras/USB ports")
    
    print("\n⚠️  COMMON OPENCV CAMERA ISSUES:")
    print("- CAP_PROP_AUTO_EXPOSURE values vary by camera")
    print("- Some cameras use different auto-exposure constants")
    print("- White balance properties may not be supported")
    print("- Camera may need warm-up time after property changes")
    print("- USB camera drivers may override OpenCV settings")

def main():
    """Main analysis function."""
    print("BathyCat Image EXIF and Camera Analysis")
    print("="*50)
    
    # Look for recent images in common locations
    image_locations = [
        "/media/usb/bathyimager",
        "./test_images", 
        "../images",
        "."
    ]
    
    found_images = []
    
    # Search for JPEG images
    for location in image_locations:
        if os.path.exists(location):
            for root, dirs, files in os.walk(location):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg')):
                        found_images.append(os.path.join(root, file))
    
    if found_images:
        print(f"Found {len(found_images)} images to analyze")
        
        # Analyze the most recent few images
        found_images.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        for i, img_path in enumerate(found_images[:5]):  # Analyze first 5
            analyze_exif_data(img_path)
            if i < 4:  # Don't print separator after last image
                print("\n" + "-"*50)
    else:
        print("❌ No images found in common locations")
        print("Please provide image path as argument:")
        print("python3 exif_analysis.py /path/to/image.jpg")
    
    # Always show camera analysis
    analyze_camera_issues()
    
    # If command line argument provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if os.path.exists(image_path):
            print(f"\n" + "="*50)
            print("ANALYZING PROVIDED IMAGE")
            analyze_exif_data(image_path)
        else:
            print(f"❌ Image not found: {image_path}")

if __name__ == "__main__":
    main()