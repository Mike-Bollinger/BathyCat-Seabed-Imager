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
    def __init__(self, output_dir=None, fps=2, duration=30, usb_only=False):
        # Force USB storage usage if not specified or if usb_only flag is set
        if output_dir is None or usb_only:
            self.output_dir = self._find_usb_storage()
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
        
    def _find_usb_storage(self):
        """Find USB storage with enhanced detection and create directory if needed"""
        import subprocess
        import os
        
        print("🔍 Searching for USB storage with enhanced detection...")
        
        # Priority order for USB storage locations
        usb_candidates = [
            "/media/usb-storage",
            "/media/bathycat", 
            "/media/bathyimager",
            "/mnt/usb",
            "/media/pi",  # Default Pi automount location
        ]
        
        # Enhanced USB device detection
        try:
            # Check lsblk for USB devices
            result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT,FSTYPE'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    # Look for mounted devices that might be USB
                    if any(fs in line.lower() for fs in ['fat32', 'exfat', 'ext4']) and '/dev/sd' in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].startswith('/'):
                            mount_point = parts[1]
                            if mount_point not in usb_candidates:
                                usb_candidates.insert(0, mount_point)
            
            # Also check mount command for USB devices
            result = subprocess.run(['mount'], capture_output=True, text=True)
            mount_lines = result.stdout.split('\n')
            for line in mount_lines:
                if '/dev/sd' in line and ' on ' in line:
                    # Extract mount point
                    parts = line.split(' on ')
                    if len(parts) >= 2:
                        mount_info = parts[1].split(' ')[0]
                        if mount_info not in usb_candidates:
                            usb_candidates.insert(0, mount_info)
        except:
            print("⚠️  Could not run system commands for USB detection")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for path in usb_candidates:
            if path not in seen:
                unique_candidates.append(path)
                seen.add(path)
        
        print(f"🔍 Checking {len(unique_candidates)} potential USB mount points...")
        
        # Test each candidate
        for mount_point in unique_candidates:
            mount_path = Path(mount_point)
            print(f"   Testing: {mount_point}")
            
            if mount_path.exists() and mount_path.is_dir():
                # Try to create bathycat directory
                bathycat_dir = mount_path / "bathycat" / "test_images"
                try:
                    bathycat_dir.mkdir(parents=True, exist_ok=True)
                    # Test write permissions
                    test_file = bathycat_dir / ".write_test"
                    test_file.write_text("test")
                    test_file.unlink()
                    
                    print(f"✅ Found accessible USB storage: {bathycat_dir}")
                    
                    # Check available space and filesystem type
                    try:
                        result = subprocess.run(['df', '-h', str(mount_path)], 
                                              capture_output=True, text=True)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) >= 2:
                                space_info = lines[1].split()
                                if len(space_info) >= 4:
                                    print(f"📊 Available space: {space_info[3]} (of {space_info[1]} total)")
                        
                        # Get filesystem type
                        result = subprocess.run(['df', '-T', str(mount_path)], 
                                              capture_output=True, text=True)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) >= 2:
                                fs_info = lines[1].split()
                                if len(fs_info) >= 2:
                                    fs_type = fs_info[1]
                                    print(f"💾 Filesystem: {fs_type}")
                                    
                                    # Warn about filesystem compatibility
                                    if fs_type.lower() in ['fat32', 'vfat']:
                                        print("⚠️  FAT32 detected - may have permission limitations")
                                    elif fs_type.lower() == 'exfat':
                                        print("✅ exFAT detected - good cross-platform compatibility")
                                    elif fs_type.lower() in ['ext4', 'ext3']:
                                        print("✅ Linux filesystem detected - full feature support")
                    except:
                        pass
                    
                    return bathycat_dir
                    
                except PermissionError:
                    print(f"❌ Permission denied: {mount_point}")
                except Exception as e:
                    print(f"❌ Cannot use {mount_point}: {e}")
            else:
                print(f"   Not accessible: {mount_point}")
        
        # If no USB storage found, provide detailed error
        print("\n❌ ERROR: No accessible USB storage found!")
        print("\nUSB Storage Troubleshooting:")
        print("=" * 50)
        print("1. 🔌 Ensure USB storage device is physically connected")
        print("2. 🔍 Check if device is detected: lsusb")
        print("3. 📋 List storage devices: lsblk")
        print("4. 🗂️  Check mounted filesystems: df -h")
        print("5. 🔧 Manual mount if needed:")
        print("   sudo mkdir -p /media/usb-storage")
        print("   sudo mount /dev/sda1 /media/usb-storage  # Replace sda1 with your device")
        print("   sudo chown -R $(whoami):$(whoami) /media/usb-storage")
        print("6. ⚙️  For automatic setup: ./scripts/setup_usb_storage.sh")
        print("7. 🧪 Test USB detection: python3 tests/test_usb_storage.py")
        
        print("\nRecommended filesystem formats for cross-platform compatibility:")
        print("- exFAT: Best for Windows/Linux compatibility")
        print("- ext4: Best for Linux performance (Windows needs special drivers)")
        print("- FAT32: Compatible but has 4GB file size limit")
        
        raise RuntimeError("USB storage required but not found")

    def find_camera(self):
        """Find available camera devices with enhanced detection"""
        print("🔍 Searching for cameras with enhanced detection...")
        
        # Check USB devices first
        try:
            import subprocess
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            if result.returncode == 0:
                camera_devices = []
                for line in result.stdout.split('\n'):
                    if any(keyword in line.lower() for keyword in ['camera', 'webcam', 'video', 'imaging']):
                        camera_devices.append(line.strip())
                
                if camera_devices:
                    print("📹 USB Camera devices detected:")
                    for device in camera_devices:
                        print(f"   {device}")
                else:
                    print("⚠️  No obvious camera devices in USB list")
        except:
            print("⚠️  Could not check USB devices")
        
        # Try different camera indices
        print("🔍 Testing video device indices...")
        for i in range(10):
            try:
                print(f"   Testing /dev/video{i}...", end=" ")
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Test if we can read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        print(f"✅ Found camera {i}: {width}x{height} @ {fps}fps")
                        cap.release()
                        return i
                    else:
                        print("❌ Can't read frames")
                else:
                    print("❌ Can't open")
                cap.release()
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        # If no cameras found, provide troubleshooting
        print("\n❌ No working cameras found!")
        print("\nCamera Troubleshooting:")
        print("=" * 40)
        print("1. 🔌 Check physical connection")
        print("2. 🔍 List USB devices: lsusb")
        print("3. 📹 Check video devices: ls -l /dev/video*")
        print("4. 🧪 Test with system tools:")
        print("   fswebcam test.jpg")
        print("   v4l2-ctl --list-devices")
        print("5. ⚙️  Check permissions:")
        print("   sudo usermod -a -G video $(whoami)")
        print("6. 🔄 Try unplugging and reconnecting camera")
        
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
            
            # Also create a metadata file with enhanced information
            metadata = {
                "filename": filename,
                "timestamp": timestamp.isoformat(),
                "frame_number": frame_number,
                "file_size_bytes": file_size,
                "resolution": {
                    "width": frame.shape[1],
                    "height": frame.shape[0],
                    "channels": frame.shape[2] if len(frame.shape) > 2 else 1
                },
                "test_session": str(self.session_dir.name),
                "camera_info": {
                    "opencv_version": cv2.__version__,
                    "test_fps": self.fps,
                    "test_duration": self.duration
                },
                "storage_info": {
                    "storage_path": str(self.output_dir),
                    "session_directory": str(self.session_dir)
                }
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
                print("\n❌ ERROR: No working cameras found!")
                print("\n🔧 Camera Troubleshooting Steps:")
                print("1. 🔌 Ensure camera is physically connected")
                print("2. 🔍 Check USB connection: lsusb | grep -i camera")
                print("3. 📹 List video devices: ls -l /dev/video*")
                print("4. 🛠️  Test camera manually:")
                print("   fswebcam -d /dev/video0 test.jpg")
                print("   v4l2-ctl --list-devices")
                print("5. 👤 Check video group permissions:")
                print("   groups $(whoami) | grep video")
                print("   sudo usermod -a -G video $(whoami)")
                print("6. 🔄 Try unplugging and reconnecting the camera")
                print("7. 🧪 Run comprehensive test: python3 tests/test_components.py")
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
    parser.add_argument('--usb-only', action='store_true',
                        help='Force USB storage usage (error if USB not available)')
    
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
        duration=args.duration,
        usb_only=args.usb_only
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
