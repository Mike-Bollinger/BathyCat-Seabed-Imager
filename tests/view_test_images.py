#!/usr/bin/env python3
"""
SSH Image Viewer for BathyCat Test Images
=========================================

Displays test images as ASCII art over SSH connection.
Can show basic image statistics and simple visual representation.

Usage:
    python view_test_images.py [image_path]
    python view_test_images.py --latest        # Show latest test image
    python view_test_images.py --all           # Show all test images
"""

import argparse
import sys
from pathlib import Path
import cv2
import numpy as np


class SSHImageViewer:
    """View images over SSH using ASCII representation."""
    
    def __init__(self):
        self.ascii_chars = " .:-=+*#%@"
    
    def get_image_info(self, image_path):
        """Get basic image information."""
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return None
            
            height, width, channels = img.shape
            file_size = image_path.stat().st_size
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            info = {
                'path': image_path,
                'dimensions': (width, height),
                'channels': channels,
                'file_size': file_size,
                'min_val': int(gray.min()),
                'max_val': int(gray.max()),
                'mean_val': float(gray.mean()),
                'std_val': float(gray.std()),
                'data': gray
            }
            
            return info
            
        except Exception as e:
            print(f"Error reading image {image_path}: {e}")
            return None
    
    def image_to_ascii(self, image_data, width=80, height=24):
        """Convert image to ASCII art."""
        try:
            # Resize image to fit terminal
            h, w = image_data.shape
            aspect_ratio = h / w
            new_width = min(width, w)
            new_height = int(aspect_ratio * new_width * 0.5)  # 0.5 for character aspect ratio
            new_height = min(new_height, height)
            
            resized = cv2.resize(image_data, (new_width, new_height))
            
            # Convert to ASCII
            ascii_art = []
            for row in resized:
                ascii_row = ""
                for pixel in row:
                    # Map pixel value (0-255) to ASCII character
                    char_index = int((pixel / 255.0) * (len(self.ascii_chars) - 1))
                    ascii_row += self.ascii_chars[char_index]
                ascii_art.append(ascii_row)
            
            return ascii_art
            
        except Exception as e:
            return [f"ASCII conversion error: {e}"]
    
    def display_image_info(self, info):
        """Display comprehensive image information."""
        if not info:
            print("❌ Could not load image information")
            return
        
        print("📷 IMAGE INFORMATION")
        print("=" * 60)
        print(f"File: {info['path'].name}")
        print(f"Dimensions: {info['dimensions'][0]} x {info['dimensions'][1]} pixels")
        print(f"Channels: {info['channels']}")
        print(f"File Size: {info['file_size']:,} bytes ({info['file_size']/1024:.1f} KB)")
        print(f"Pixel Values: min={info['min_val']}, max={info['max_val']}, mean={info['mean_val']:.1f}")
        print(f"Standard Deviation: {info['std_val']:.2f}")
        print()
        
        # Image quality assessment
        print("📊 QUALITY ASSESSMENT:")
        if info['max_val'] == 0:
            print("❌ Completely black image (no data)")
        elif info['max_val'] < 50:
            print("⚠️  Very dark image")
        elif info['std_val'] < 5:
            print("⚠️  Very uniform image (low contrast)")
        elif info['std_val'] > 50:
            print("✅ Good contrast and detail")
        else:
            print("✅ Normal image with reasonable contrast")
        
        print("=" * 60)
    
    def display_ascii_art(self, info, width=80, height=20):
        """Display ASCII art representation of image."""
        if not info:
            return
        
        print(f"\n🎨 ASCII REPRESENTATION ({width}x{height}):")
        print("-" * width)
        
        ascii_art = self.image_to_ascii(info['data'], width, height)
        for line in ascii_art:
            print(line)
        
        print("-" * width)
    
    def view_image(self, image_path, show_ascii=True, ascii_width=80, ascii_height=20):
        """View a single image with full information."""
        print(f"\n🔍 Viewing: {image_path}")
        
        info = self.get_image_info(image_path)
        self.display_image_info(info)
        
        if show_ascii and info:
            self.display_ascii_art(info, ascii_width, ascii_height)
    
    def find_test_images(self, test_dir="/tmp/camera_test"):
        """Find all test images in directory."""
        test_path = Path(test_dir)
        if not test_path.exists():
            return []
        
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            image_files.extend(test_path.glob(ext))
        
        return sorted(image_files, key=lambda x: x.stat().st_mtime)
    
    def view_latest(self):
        """View the most recent test image."""
        images = self.find_test_images()
        if not images:
            print("❌ No test images found in /tmp/camera_test/")
            print("Run camera_test_stream.py --save-images first")
            return
        
        latest = images[-1]
        print(f"📸 Showing latest image ({len(images)} total found)")
        self.view_image(latest)
    
    def view_all_summary(self):
        """View summary of all test images."""
        images = self.find_test_images()
        if not images:
            print("❌ No test images found in /tmp/camera_test/")
            return
        
        print(f"📸 Found {len(images)} test images in /tmp/camera_test/")
        print("=" * 80)
        
        total_size = 0
        valid_images = 0
        
        for i, img_path in enumerate(images, 1):
            info = self.get_image_info(img_path)
            if info:
                valid_images += 1
                total_size += info['file_size']
                
                # Show basic info in compact format
                dims = f"{info['dimensions'][0]}x{info['dimensions'][1]}"
                size = f"{info['file_size']/1024:.1f}KB"
                quality = "✅" if info['std_val'] > 10 and info['max_val'] > 50 else "⚠️ "
                
                print(f"{i:3d}. {img_path.name:<30} {dims:>10} {size:>8} {quality}")
            else:
                print(f"{i:3d}. {img_path.name:<30} {'ERROR':>10} {'':>8} ❌")
        
        print("=" * 80)
        print(f"Valid Images: {valid_images}/{len(images)}")
        print(f"Total Size: {total_size/1024/1024:.1f} MB")
        print(f"Average Size: {total_size/len(images)/1024:.1f} KB per image")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SSH Image Viewer for BathyCat Test Images",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "image_path",
        nargs="?",
        help="Path to specific image file to view"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="View the most recent test image"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show summary of all test images"
    )
    parser.add_argument(
        "--no-ascii",
        action="store_true",
        help="Skip ASCII art display (info only)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=80,
        help="ASCII art width (default: 80)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=20,
        help="ASCII art height (default: 20)"
    )
    
    args = parser.parse_args()
    
    viewer = SSHImageViewer()
    
    if args.latest:
        viewer.view_latest()
    elif args.all:
        viewer.view_all_summary()
    elif args.image_path:
        image_path = Path(args.image_path)
        if not image_path.exists():
            print(f"❌ Image file not found: {image_path}")
            sys.exit(1)
        viewer.view_image(image_path, not args.no_ascii, args.width, args.height)
    else:
        # Default: show latest if available, otherwise show usage
        images = viewer.find_test_images()
        if images:
            print("No arguments provided - showing latest test image:")
            viewer.view_latest()
        else:
            print("No test images found. Usage examples:")
            print("  python view_test_images.py --latest")
            print("  python view_test_images.py --all")
            print("  python view_test_images.py /path/to/image.jpg")
            print("\nRun camera_test_stream.py --save-images first to generate test images")


if __name__ == "__main__":
    main()