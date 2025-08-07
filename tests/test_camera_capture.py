#!/usr/bin/env python3
"""
BathyCat Camera Capture Test
===========================

Simple test script to verify camera functionality on Raspberry Pi.
This test runs without GPS and captures images to verify the camera system works.

Usage: python3 test_camera_capture.py [--duration 30] [--fps 2]
"""

import cv2
import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path

class CameraTest:
    def __init__(self, output_dir=None, fps=2, duration=30):
        # Default to USB storage locations if not specified
        if output_dir is None:
            usb_paths = [
                "/media/usb-storage/bathycat/test_images",
                "/media/bathycat/test_images", 
                "/mnt/usb/bathycat/test_images",
                "./test_images"  # Fallback to local directory
            ]
            
            # Find first available USB storage path
            self.output_dir = None
            for path in usb_paths:
                parent = Path(path).parent
                if parent.exists() and parent.is_dir():
                    self.output_dir = Path(path)
                    print(f"Using USB storage: {self.output_dir}")
                    break
            
            # Use fallback if no USB storage found
            if self.output_dir is None:
                self.output_dir = Path("./test_images")
                print(f"⚠️  No USB storage found, using local: {self.output_dir}")
        else:
            self.output_dir = Path(output_dir)
            
        self.fps = fps
        self.duration = duration
        self.frame_interval = 1.0 / fps
        self.camera = None
        self.images_captured = 0
        
        # Create output directory and session subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"test_session_{timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"BathyCat Camera Test")
        print(f"==================")
        print(f"Session directory: {self.session_dir.absolute()}")
        print(f"Target FPS: {fps}")
        print(f"Test duration: {duration} seconds")
        print()

    def find_camera(self):
        """Find available camera devices"""
        print("Searching for cameras...")
        
        # Try different camera indices
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Test if we can read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        print(f"Found camera {i}: {width}x{height} @ {fps}fps")
                        cap.release()
                        return i
                cap.release()
            except Exception as e:
                continue
        
        return None

    def setup_camera(self, camera_index):
        """Setup camera with optimal settings"""
        print(f"Setting up camera {camera_index}...")
        
        self.camera = cv2.VideoCapture(camera_index)
        
        if not self.camera.isOpened():
            raise Exception(f"Could not open camera {camera_index}")
        
        # Set camera properties for high-quality capture
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Get actual settings
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
        
        print(f"Camera configured: {width}x{height} @ {actual_fps}fps")
        
        # Warm up camera
        print("Warming up camera...")
        for i in range(10):
            ret, frame = self.camera.read()
            if not ret:
                raise Exception("Failed to read from camera during warmup")
        
        print("Camera ready!")
        return True

    def capture_image(self, frame_number):
        """Capture a single image"""
        ret, frame = self.camera.read()
        
        if not ret or frame is None:
            print(f"Failed to capture frame {frame_number}")
            return False
        
        # Generate filename with timestamp
        timestamp = datetime.now()
        filename = f"test_image_{timestamp.strftime('%Y%m%d_%H%M%S')}_{frame_number:04d}.jpg"
        filepath = self.session_dir / filename
        
        # Save image with high quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        success = cv2.imwrite(str(filepath), frame, encode_params)
        
        if success:
            file_size = filepath.stat().st_size
            print(f"Captured: {filename} ({file_size/1024:.1f}KB)")
            self.images_captured += 1
            
            # Also create a metadata file
            metadata = {
                "filename": filename,
                "timestamp": timestamp.isoformat(),
                "frame_number": frame_number,
                "file_size_bytes": file_size,
                "resolution": {
                    "width": frame.shape[1],
                    "height": frame.shape[0]
                },
                "test_session": str(self.session_dir.name)
            }
            
            metadata_file = self.session_dir / f"{filename}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            return True
        else:
            print(f"Failed to save: {filename}")
            return False

    def run_test(self):
        """Run the camera capture test"""
        try:
            # Find camera
            camera_index = self.find_camera()
            if camera_index is None:
                print("ERROR: No cameras found!")
                print("\nTroubleshooting:")
                print("1. Check if camera is connected")
                print("2. Try: lsusb | grep -i camera")
                print("3. Check permissions: ls -l /dev/video*")
                print("4. Test with: fswebcam test.jpg")
                return False
            
            # Setup camera
            if not self.setup_camera(camera_index):
                return False
            
            print(f"\nStarting capture test...")
            print(f"Will capture for {self.duration} seconds at {self.fps} FPS")
            print("Press Ctrl+C to stop early\n")
            
            start_time = time.time()
            last_capture_time = 0
            frame_number = 0
            
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check if test duration exceeded
                if elapsed >= self.duration:
                    break
                
                # Check if it's time to capture next frame
                if current_time - last_capture_time >= self.frame_interval:
                    frame_number += 1
                    success = self.capture_image(frame_number)
                    last_capture_time = current_time
                    
                    # Print progress every 10 frames
                    if frame_number % 10 == 0:
                        rate = self.images_captured / elapsed if elapsed > 0 else 0
                        print(f"Progress: {elapsed:.1f}s, {self.images_captured} images, {rate:.2f} fps actual")
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        except Exception as e:
            print(f"ERROR: {e}")
            return False
        finally:
            if self.camera:
                self.camera.release()
        
        # Print results
        end_time = time.time()
        actual_duration = end_time - start_time
        actual_fps = self.images_captured / actual_duration if actual_duration > 0 else 0
        
        print(f"\n" + "="*50)
        print(f"TEST RESULTS")
        print(f"="*50)
        print(f"Duration: {actual_duration:.2f} seconds")
        print(f"Images captured: {self.images_captured}")
        print(f"Target FPS: {self.fps}")
        print(f"Actual FPS: {actual_fps:.2f}")
        print(f"Success rate: {(actual_fps/self.fps*100):.1f}%" if self.fps > 0 else "N/A")
        print(f"Session directory: {self.session_dir.absolute()}")
        
        # Check if any images were captured
        if self.images_captured > 0:
            print(f"\n✅ SUCCESS: Camera is working!")
            print(f"Check the images in: {self.session_dir.absolute()}")
            
            # Create test summary file
            summary = {
                "test_completed": datetime.now().isoformat(),
                "test_duration": actual_duration,
                "images_captured": self.images_captured,
                "target_fps": self.fps,
                "actual_fps": actual_fps,
                "success_rate": (actual_fps/self.fps*100) if self.fps > 0 else 0,
                "session_directory": str(self.session_dir),
                "storage_type": "USB" if "/media/" in str(self.session_dir) or "/mnt/" in str(self.session_dir) else "Local"
            }
            
            summary_file = self.session_dir / "test_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"Test summary saved: {summary_file}")
            
        else:
            print(f"\n❌ FAILED: No images were captured")
            return False
        
        return True

    def cleanup(self):
        """Clean up resources"""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='Test BathyCat camera capture')
    parser.add_argument('--duration', type=int, default=30, 
                        help='Test duration in seconds (default: 30)')
    parser.add_argument('--fps', type=float, default=2.0,
                        help='Target frames per second (default: 2.0)')
    parser.add_argument('--output', type=str, default='./test_images',
                        help='Output directory (default: ./test_images)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.duration <= 0:
        print("ERROR: Duration must be positive")
        return 1
    
    if args.fps <= 0:
        print("ERROR: FPS must be positive")
        return 1
    
    # Run test
    test = CameraTest(
        output_dir=args.output,
        fps=args.fps,
        duration=args.duration
    )
    
    try:
        success = test.run_test()
        return 0 if success else 1
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return 1
    finally:
        test.cleanup()

if __name__ == "__main__":
    sys.exit(main())
