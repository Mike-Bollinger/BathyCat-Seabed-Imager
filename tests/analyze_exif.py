#!/usr/bin/env python3
"""
EXIF Metadata Verification
=========================

Check what EXIF metadata is present in captured images and identify any missing fields.
Run this to debug EXIF issues with captured images.
"""

import sys
import os
from PIL import Image
import piexif

def analyze_image_exif(image_path):
    """Analyze EXIF metadata in an image file."""
    print(f"\n=== ANALYZING: {os.path.basename(image_path)} ===")
    
    try:
        img = Image.open(image_path)
        
        # Check if EXIF data exists
        if 'exif' not in img.info:
            print("❌ NO EXIF DATA FOUND")
            return False
        
        # Load EXIF data
        exif_dict = piexif.load(img.info['exif'])
        
        # Analyze each EXIF section
        print("\n📋 EXIF SECTIONS:")
        for section_name, section_data in exif_dict.items():
            if section_data and isinstance(section_data, dict):
                print(f"  ✓ {section_name}: {len(section_data)} fields")
            else:
                print(f"  - {section_name}: Empty")
        
        # Check basic camera info (0th IFD)
        print("\n📸 CAMERA INFORMATION:")
        if '0th' in exif_dict:
            ifd_0th = exif_dict['0th']
            
            # Required fields
            make = ifd_0th.get(piexif.ImageIFD.Make, b'').decode('ascii', errors='ignore')
            model = ifd_0th.get(piexif.ImageIFD.Model, b'').decode('ascii', errors='ignore')
            copyright_info = ifd_0th.get(piexif.ImageIFD.Copyright, b'').decode('ascii', errors='ignore')
            software = ifd_0th.get(piexif.ImageIFD.Software, b'').decode('ascii', errors='ignore')
            
            print(f"  Make: '{make}' {'✓' if make else '❌'}")
            print(f"  Model: '{model}' {'✓' if model == 'BathyImager' else '❌ Expected: BathyImager'}")
            print(f"  Copyright: '{copyright_info}' {'✓' if copyright_info == 'NOAA' else '❌ Expected: NOAA'}")
            print(f"  Software: '{software}' {'✓' if software else '❌'}")
            
            # Image dimensions
            width = ifd_0th.get(piexif.ImageIFD.ImageWidth, 0)
            height = ifd_0th.get(piexif.ImageIFD.ImageLength, 0)
            print(f"  Dimensions: {width}x{height} {'✓' if width > 0 and height > 0 else '❌'}")
        else:
            print("  ❌ No basic camera information found")
        
        # Check camera settings (Exif IFD)
        print("\n⚙️  CAMERA SETTINGS:")
        if 'Exif' in exif_dict:
            exif_ifd = exif_dict['Exif']
            
            # Exposure settings
            if piexif.ExifIFD.ExposureTime in exif_ifd:
                exp_time = exif_ifd[piexif.ExifIFD.ExposureTime]
                print(f"  ✓ Exposure Time: {exp_time[0]}/{exp_time[1]}")
            else:
                print(f"  ❌ Exposure Time: Missing")
            
            # Exposure mode
            exp_mode = exif_ifd.get(piexif.ExifIFD.ExposureMode)
            if exp_mode is not None:
                mode_text = {0: "Auto", 1: "Manual", 2: "Auto Bracket"}.get(exp_mode, f"Unknown({exp_mode})")
                print(f"  ✓ Exposure Mode: {mode_text}")
            else:
                print(f"  ❌ Exposure Mode: Missing")
            
            # White balance
            wb_mode = exif_ifd.get(piexif.ExifIFD.WhiteBalance)
            if wb_mode is not None:
                wb_text = {0: "Auto", 1: "Manual"}.get(wb_mode, f"Unknown({wb_mode})")
                print(f"  ✓ White Balance: {wb_text}")
            else:
                print(f"  ❌ White Balance: Missing")
            
            # ISO
            iso = exif_ifd.get(piexif.ExifIFD.ISOSpeedRatings)
            if iso:
                print(f"  ✓ ISO: {iso}")
            else:
                print(f"  ❌ ISO: Missing")
            
            # Brightness
            if piexif.ExifIFD.BrightnessValue in exif_ifd:
                brightness_rational = exif_ifd[piexif.ExifIFD.BrightnessValue]
                brightness_val = brightness_rational[0] / brightness_rational[1] if brightness_rational[1] != 0 else 0
                print(f"  ✓ Brightness: {brightness_val}")
            else:
                print(f"  ❌ Brightness: Missing")
            
            # Image quality settings
            contrast = exif_ifd.get(piexif.ExifIFD.Contrast)
            saturation = exif_ifd.get(piexif.ExifIFD.Saturation) 
            sharpness = exif_ifd.get(piexif.ExifIFD.Sharpness)
            
            contrast_text = {0: "Normal", 1: "Low", 2: "High"}.get(contrast, f"Unknown({contrast})")
            saturation_text = {0: "Normal", 1: "Low", 2: "High"}.get(saturation, f"Unknown({saturation})")
            sharpness_text = {0: "Normal", 1: "Soft", 2: "Hard"}.get(sharpness, f"Unknown({sharpness})")
            
            print(f"  {'✓' if contrast is not None else '❌'} Contrast: {contrast_text if contrast is not None else 'Missing'}")
            print(f"  {'✓' if saturation is not None else '❌'} Saturation: {saturation_text if saturation is not None else 'Missing'}")
            print(f"  {'✓' if sharpness is not None else '❌'} Sharpness: {sharpness_text if sharpness is not None else 'Missing'}")
            
            # User comment (camera info)
            if piexif.ExifIFD.UserComment in exif_ifd:
                user_comment = exif_ifd[piexif.ExifIFD.UserComment]
                try:
                    if user_comment.startswith(b'UNICODE\x00'):
                        comment_text = user_comment[8:].decode('utf-8', errors='ignore')
                    else:
                        comment_text = user_comment.decode('utf-8', errors='ignore')
                    print(f"  ✓ Camera Info: '{comment_text}'")
                except:
                    print(f"  ⚠️  User Comment: Could not decode")
            else:
                print(f"  ❌ Camera Info: Missing")
        else:
            print("  ❌ No camera settings found")
        
        # Check GPS data
        print("\n🌍 GPS INFORMATION:")
        if 'GPS' in exif_dict:
            gps_data = exif_dict['GPS']
            
            # GPS coordinates
            if piexif.GPSIFD.GPSLatitude in gps_data and piexif.GPSIFD.GPSLongitude in gps_data:
                lat_dms = gps_data[piexif.GPSIFD.GPSLatitude]
                lon_dms = gps_data[piexif.GPSIFD.GPSLongitude]
                lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'').decode('ascii')
                lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'').decode('ascii')
                
                # Convert DMS to decimal
                def dms_to_decimal(dms_tuple):
                    if len(dms_tuple) != 3:
                        return 0.0
                    degrees = dms_tuple[0][0] / dms_tuple[0][1]
                    minutes = dms_tuple[1][0] / dms_tuple[1][1]
                    seconds = dms_tuple[2][0] / dms_tuple[2][1]
                    return degrees + minutes/60 + seconds/3600
                
                lat_decimal = dms_to_decimal(lat_dms)
                lon_decimal = dms_to_decimal(lon_dms)
                
                if lat_ref == 'S':
                    lat_decimal = -lat_decimal
                if lon_ref == 'W':
                    lon_decimal = -lon_decimal
                
                print(f"  ✓ Coordinates: {lat_decimal:.6f}°{lat_ref}, {lon_decimal:.6f}°{lon_ref}")
                
                # Check if it's fallback coordinates (Null Island)
                if abs(lat_decimal) < 0.001 and abs(lon_decimal) < 0.001:
                    print(f"  ℹ️  This is FALLBACK GPS (Null Island - 0°N,0°W)")
                else:
                    print(f"  ℹ️  This is REAL GPS coordinates")
            else:
                print(f"  ❌ GPS Coordinates: Missing")
            
            # Satellites
            satellites = gps_data.get(piexif.GPSIFD.GPSSatellites, b'').decode('ascii', errors='ignore')
            if satellites:
                print(f"  ✓ Satellites: {satellites}")
                if satellites == '0':
                    print(f"    ℹ️  0 satellites = Fallback GPS mode")
            else:
                print(f"  ❌ Satellites: Missing")
            
            # GPS timestamp
            if piexif.GPSIFD.GPSTimeStamp in gps_data:
                print(f"  ✓ GPS Timestamp: Present")
            else:
                print(f"  ❌ GPS Timestamp: Missing")
        else:
            print("  ❌ NO GPS DATA FOUND")
        
        print(f"\n✅ ANALYSIS COMPLETE")
        return True
        
    except Exception as e:
        print(f"❌ ERROR analyzing image: {e}")
        return False

def main():
    """Analyze EXIF metadata in image files."""
    print("EXIF Metadata Verification Tool")
    print("=" * 35)
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_exif.py <image_file1> [image_file2] ...")
        print("Example: python3 analyze_exif.py /path/to/captured_image.jpg")
        return
    
    # Analyze each provided image
    success_count = 0
    total_count = 0
    
    for image_path in sys.argv[1:]:
        total_count += 1
        if os.path.exists(image_path):
            if analyze_image_exif(image_path):
                success_count += 1
        else:
            print(f"\n❌ File not found: {image_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {success_count}/{total_count} images analyzed successfully")
    print("="*60)
    
    print("\n🎯 EXPECTED METADATA:")
    print("  • Make: 'BathyCat'")
    print("  • Model: 'BathyImager'")
    print("  • Copyright: 'NOAA'")
    print("  • Exposure settings (time, mode)")
    print("  • White balance mode")
    print("  • ISO/brightness/contrast/saturation/sharpness")
    print("  • GPS coordinates (real or 0°N,0°W fallback)")
    print("  • Camera info in UserComment (FPS, WB temp)")

if __name__ == "__main__":
    main()