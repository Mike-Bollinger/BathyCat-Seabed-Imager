"""
Enhanced Camera Controller with fswebcam Integration
Handles H264 USB cameras that don't work with OpenCV
"""

import cv2
import numpy as np
import asyncio
import subprocess
import os
import tempfile
import time
from pathlib import Path
import logging

class HybridCameraController:
    """Camera controller that tries OpenCV first, falls back to fswebcam"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.device_id = getattr(config, 'camera_device_id', 0)
        self.width = getattr(config, 'camera_width', 1920)
        self.height = getattr(config, 'camera_height', 1080)
        self.fps = getattr(config, 'camera_fps', 30)
        
        self.camera = None
        self.capture_method = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize camera with fallback methods"""
        self.logger.info(f"Initializing hybrid camera controller")
        
        # Try OpenCV methods first
        if await self._try_opencv_methods():
            self.capture_method = "opencv"
            self.is_initialized = True
            self.logger.info("✅ OpenCV camera initialization successful")
            return True
            
        # Fall back to fswebcam
        if await self._try_fswebcam_method():
            self.capture_method = "fswebcam"
            self.is_initialized = True
            self.logger.info("✅ fswebcam camera initialization successful")
            return True
            
        self.logger.error("❌ All camera initialization methods failed")
        return False
    
    async def _try_opencv_methods(self) -> bool:
        """Try various OpenCV access methods"""
        methods = [
            ("Device path with MJPEG", "/dev/video0", None, True),
            ("Index with MJPEG", self.device_id, cv2.CAP_V4L2, True),
            ("Device path V4L2", "/dev/video0", cv2.CAP_V4L2, False),
            ("Index V4L2", self.device_id, cv2.CAP_V4L2, False),
            ("Index ANY", self.device_id, cv2.CAP_ANY, False),
        ]
        
        for name, device, backend, force_mjpeg in methods:
            try:
                self.logger.debug(f"Trying OpenCV method: {name}")
                
                if backend is not None:
                    camera = cv2.VideoCapture(device, backend)
                else:
                    camera = cv2.VideoCapture(device)
                
                if camera.isOpened():
                    # Configure camera
                    if force_mjpeg:
                        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                        camera.set(cv2.CAP_PROP_FOURCC, fourcc)
                    
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    camera.set(cv2.CAP_PROP_FPS, self.fps)
                    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # Test frame capture
                    ret, frame = camera.read()
                    if ret and frame is not None:
                        self.camera = camera
                        self.logger.info(f"✅ OpenCV success with {name}")
                        return True
                    else:
                        self.logger.debug(f"❌ {name}: No frame captured")
                        camera.release()
                else:
                    self.logger.debug(f"❌ {name}: Failed to open")
                    if camera:
                        camera.release()
                        
            except Exception as e:
                self.logger.debug(f"❌ {name}: Exception {e}")
                
        return False
    
    async def _try_fswebcam_method(self) -> bool:
        """Test fswebcam method"""
        try:
            # Test fswebcam capture
            temp_path = "/tmp/fswebcam_test.jpg"
            cmd = [
                "fswebcam", 
                "-d", f"/dev/video{self.device_id}",
                "--no-banner",
                "-r", f"{self.width}x{self.height}",
                "--jpeg", "95",
                "--skip", "5",
                temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(temp_path):
                # Verify we can load with OpenCV
                test_img = cv2.imread(temp_path)
                os.unlink(temp_path)  # Clean up
                
                if test_img is not None:
                    self.logger.info("✅ fswebcam test successful")
                    return True
                else:
                    self.logger.error("❌ fswebcam: OpenCV can't read image")
            else:
                self.logger.error(f"❌ fswebcam failed: {stderr.decode()}")
                
        except Exception as e:
            self.logger.error(f"❌ fswebcam test exception: {e}")
            
        return False
    
    async def capture_image(self) -> tuple[bool, np.ndarray, dict]:
        """Capture image using the initialized method"""
        if not self.is_initialized:
            return False, None, {}
        
        timestamp = time.time()
        
        if self.capture_method == "opencv":
            return await self._capture_opencv(timestamp)
        elif self.capture_method == "fswebcam":
            return await self._capture_fswebcam(timestamp)
        else:
            return False, None, {}
    
    async def _capture_opencv(self, timestamp: float) -> tuple[bool, np.ndarray, dict]:
        """Capture using OpenCV"""
        try:
            ret, frame = self.camera.read()
            if ret and frame is not None:
                metadata = {
                    'timestamp': timestamp,
                    'width': frame.shape[1],
                    'height': frame.shape[0],
                    'channels': frame.shape[2] if len(frame.shape) > 2 else 1,
                    'capture_method': 'opencv'
                }
                return True, frame, metadata
            else:
                self.logger.error("OpenCV frame capture failed")
                return False, None, {}
                
        except Exception as e:
            self.logger.error(f"OpenCV capture exception: {e}")
            return False, None, {}
    
    async def _capture_fswebcam(self, timestamp: float) -> tuple[bool, np.ndarray, dict]:
        """Capture using fswebcam"""
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='bathycat_')
        os.close(temp_fd)  # Close the file descriptor, keep the path
        
        try:
            cmd = [
                "fswebcam",
                "-d", f"/dev/video{self.device_id}",
                "--no-banner", 
                "-r", f"{self.width}x{self.height}",
                "--jpeg", "95",
                "--skip", "5",
                temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(temp_path):
                # Load with OpenCV
                image = cv2.imread(temp_path)
                
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
                    self.logger.error("fswebcam: OpenCV failed to load image")
                    return False, None, {}
            else:
                self.logger.error(f"fswebcam capture failed: {stderr.decode()}")
                return False, None, {}
                
        except Exception as e:
            self.logger.error(f"fswebcam capture exception: {e}")
            return False, None, {}
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def shutdown(self):
        """Shutdown camera"""
        self.logger.info("Shutting down hybrid camera...")
        
        if self.camera and self.capture_method == "opencv":
            self.camera.release()
            self.camera = None
            
        self.is_initialized = False
        self.capture_method = None
        self.logger.info("Camera shutdown complete")

# Backward compatibility alias
CameraController = HybridCameraController