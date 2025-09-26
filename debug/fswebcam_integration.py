#!/usr/bin/env python3
"""
fswebcam Integration Solution for BathyCat
Since fswebcam works but OpenCV doesn't, let's use fswebcam for capture
"""

import subprocess
import os
import sys
import time
import cv2
import numpy as np
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def analyze_fswebcam():
    """Analyze exactly what fswebcam is doing"""
    print("=== fswebcam Deep Analysis ===")
    
    # Test with maximum verbosity
    cmd = "fswebcam -d /dev/video0 --verbose --no-banner -r 1920x1080 --jpeg 95 --skip 5 /tmp/fswebcam_analysis.jpg"
    print(f"🔍 Running: {cmd}")
    
    retcode, stdout, stderr = run_command(cmd)
    print(f"Return code: {retcode}")
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    
    if os.path.exists("/tmp/fswebcam_analysis.jpg"):
        file_size = os.path.getsize("/tmp/fswebcam_analysis.jpg")
        print(f"✅ Image created: {file_size} bytes")
        return True
    else:
        print("❌ No image file created")
        return False

def test_fswebcam_wrapper():
    """Test using fswebcam as a wrapper for OpenCV"""
    print("\n=== fswebcam Wrapper Test ===")
    
    def capture_with_fswebcam(output_path, width=1920, height=1080):
        """Capture image using fswebcam"""
        cmd = f"fswebcam -d /dev/video0 --no-banner -r {width}x{height} --jpeg 95 --skip 5 {output_path}"
        retcode, stdout, stderr = run_command(cmd)
        
        if retcode == 0 and os.path.exists(output_path):
            return True
        else:
            print(f"fswebcam failed: {stderr}")
            return False
    
    # Test capture
    test_image = "/tmp/fswebcam_wrapper_test.jpg"
    if capture_with_fswebcam(test_image):
        print("✅ fswebcam capture successful")
        
        # Load with OpenCV to verify compatibility
        try:
            img = cv2.imread(test_image)
            if img is not None:
                print(f"✅ OpenCV can read fswebcam image: {img.shape}")
                print("✅ fswebcam wrapper solution viable!")
                return True
            else:
                print("❌ OpenCV cannot read fswebcam image")
                return False
        except Exception as e:
            print(f"❌ OpenCV read error: {e}")
            return False
    else:
        print("❌ fswebcam capture failed")
        return False

def test_v4l2_direct():
    """Test direct v4l2 access"""
    print("\n=== V4L2 Direct Access Test ===")
    
    # Try to read raw data from video device
    try:
        with open("/dev/video0", "rb") as f:
            data = f.read(1024)  # Read small chunk
            print(f"✅ Can read raw data from /dev/video0: {len(data)} bytes")
            print(f"First 16 bytes: {data[:16].hex()}")
            return True
    except Exception as e:
        print(f"❌ Cannot read raw data: {e}")
        return False

def create_fswebcam_camera_controller():
    """Create a camera controller that uses fswebcam instead of OpenCV"""
    print("\n=== Creating fswebcam Camera Controller ===")
    
    camera_controller_code = '''
class FswebcamCameraController:
    """Camera controller using fswebcam instead of OpenCV for capture"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.device_id = config.camera_device_id
        self.width = config.camera_width
        self.height = config.camera_height
        self.is_initialized = False
        self.temp_image_path = "/tmp/bathycat_capture.jpg"
    
    async def initialize(self) -> bool:
        """Initialize camera by testing fswebcam"""
        self.logger.info(f"Initializing fswebcam camera on /dev/video{self.device_id}")
        
        try:
            # Test capture
            if await self._test_fswebcam_capture():
                self.is_initialized = True
                self.logger.info("fswebcam camera initialization complete")
                return True
            else:
                self.logger.error("fswebcam test capture failed")
                return False
        except Exception as e:
            self.logger.error(f"fswebcam initialization error: {e}")
            return False
    
    async def _test_fswebcam_capture(self) -> bool:
        """Test fswebcam capture"""
        cmd = f"fswebcam -d /dev/video{self.device_id} --no-banner -r {self.width}x{self.height} --jpeg 95 --skip 5 {self.temp_image_path}"
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(self.temp_image_path):
                # Verify with OpenCV
                img = cv2.imread(self.temp_image_path)
                if img is not None:
                    os.remove(self.temp_image_path)  # Clean up
                    return True
            
            self.logger.error(f"fswebcam test failed: {stderr.decode()}")
            return False
            
        except Exception as e:
            self.logger.error(f"fswebcam test exception: {e}")
            return False
    
    async def capture_image(self) -> tuple[bool, np.ndarray, dict]:
        """Capture image using fswebcam"""
        if not self.is_initialized:
            return False, None, {}
        
        timestamp = time.time()
        temp_path = f"/tmp/bathycat_{timestamp}.jpg"
        
        try:
            # Capture with fswebcam
            cmd = f"fswebcam -d /dev/video{self.device_id} --no-banner -r {self.width}x{self.height} --jpeg 95 --skip 5 {temp_path}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(temp_path):
                # Load with OpenCV
                image = cv2.imread(temp_path)
                os.remove(temp_path)  # Clean up immediately
                
                if image is not None:
                    metadata = {
                        'timestamp': timestamp,
                        'width': image.shape[1],
                        'height': image.shape[0],
                        'channels': image.shape[2],
                        'capture_method': 'fswebcam'
                    }
                    return True, image, metadata
                else:
                    self.logger.error("OpenCV failed to load fswebcam image")
                    return False, None, {}
            else:
                self.logger.error(f"fswebcam capture failed: {stderr.decode()}")
                return False, None, {}
                
        except Exception as e:
            self.logger.error(f"fswebcam capture exception: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, None, {}
    
    async def shutdown(self):
        """Shutdown camera"""
        self.logger.info("Shutting down fswebcam camera...")
        # Clean up any temp files
        for temp_file in [self.temp_image_path, "/tmp/bathycat_*.jpg"]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        self.is_initialized = False
        self.logger.info("fswebcam camera shutdown complete")
'''
    
    # Save to file
    with open("/tmp/fswebcam_camera_controller.py", "w") as f:
        f.write("import asyncio\nimport cv2\nimport numpy as np\nimport os\nimport time\n\n")
        f.write(camera_controller_code)
    
    print("✅ fswebcam camera controller created at /tmp/fswebcam_camera_controller.py")
    return True

def main():
    print("🔍 fswebcam Integration Analysis")
    print("=" * 50)
    
    # Analyze what fswebcam is doing
    fswebcam_works = analyze_fswebcam()
    
    if fswebcam_works:
        print("\n✅ fswebcam confirmed working")
        
        # Test wrapper approach
        wrapper_works = test_fswebcam_wrapper()
        
        if wrapper_works:
            print("\n🎉 fswebcam wrapper solution viable!")
            create_fswebcam_camera_controller()
            
            print("\n📝 Next Steps:")
            print("1. Replace OpenCV camera code with fswebcam wrapper")
            print("2. Copy /tmp/fswebcam_camera_controller.py to your project")
            print("3. Update camera_controller.py to use FswebcamCameraController")
            print("4. Test with BathyCat")
            
        else:
            print("\n❌ fswebcam wrapper approach failed")
    
    # Also test direct v4l2 access for completeness
    test_v4l2_direct()
    
    print("\n" + "=" * 50)
    print("🏁 Analysis complete!")

if __name__ == "__main__":
    main()
