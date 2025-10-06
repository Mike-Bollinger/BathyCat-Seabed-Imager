#!/usr/bin/env python3
"""
Camera Controller for BathyCat Seabed Imager
===========================================

Handles USB camera operations for high-frequency image capture.
Supports various camera backends including OpenCV and V4L2.

Author: Mike Bollinger
Date: August 2025
"""

import asyncio
import cv2
import logging
import numpy as np
import time
from typing import Optional, Tuple, Dict, Any
from pathlib import Path


class CameraController:
    """Controls USB camera for image capture."""
    
    def __init__(self, config):
        """Initialize camera controller."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.camera = None
        self.is_initialized = False
        self.capture_count = 0
        
        # Camera settings
        self.device_id = config.camera_device_id
        self.width = config.camera_width
        self.height = config.camera_height
        self.fps = config.camera_fps
        self.format = config.camera_format
        
        # Performance tracking
        self.last_capture_time = 0
        self.capture_times = []
    
    async def initialize(self) -> bool:
        """Initialize the camera."""
        self.logger.info(f"Initializing camera device {self.device_id}")
        
        try:
            # Try multiple camera access methods
            access_methods = [
                ("Index with V4L2", self.device_id, cv2.CAP_V4L2),
                ("Index with ANY", self.device_id, cv2.CAP_ANY),
                ("Index only", self.device_id, None),
                ("Device path", f"/dev/video{self.device_id}", None),
                ("Device path with V4L2", f"/dev/video{self.device_id}", cv2.CAP_V4L2),
            ]
            
            for method_name, device, backend in access_methods:
                self.logger.debug(f"Trying {method_name}: device={device}, backend={backend}")
                
                if backend is not None:
                    self.camera = cv2.VideoCapture(device, backend)
                else:
                    self.camera = cv2.VideoCapture(device)
                
                if self.camera.isOpened():
                    self.logger.info(f"Camera opened successfully using {method_name}")
                    break
                else:
                    self.logger.debug(f"{method_name} failed")
                    self.camera.release()
                    self.camera = None
            
            if not self.camera or not self.camera.isOpened():
                self.logger.error("Failed to open camera")
                return False
            
            # Configure camera settings
            await self._configure_camera()
            
            # Test capture
            if not await self._test_capture():
                self.logger.error("Camera test capture failed")
                return False
            
            self.is_initialized = True
            self.logger.info("Camera initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            return False
    
    async def _configure_camera(self):
        """Configure camera parameters."""
        self.logger.info("Configuring camera settings...")
        
        # Set resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Set FPS
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Set format if supported
        if hasattr(cv2, 'CAP_PROP_FOURCC'):
            if self.format.upper() == 'MJPG':
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            elif self.format.upper() == 'YUYV':
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y','U','Y','V'))
        
        # Optimization settings
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer delay
        
        # Log actual settings
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
        
        self.logger.info(
            f"Camera configured: {actual_width}x{actual_height} @ {actual_fps}fps"
        )
        
        # Additional camera optimizations for underwater imaging
        await self._optimize_for_underwater()
    
    async def _optimize_for_underwater(self):
        """Optimize camera settings for underwater conditions."""
        self.logger.info("Applying underwater optimizations...")
        
        try:
            # Auto-exposure settings
            if self.config.camera_auto_exposure:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            else:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                if hasattr(self.config, 'camera_exposure'):
                    self.camera.set(cv2.CAP_PROP_EXPOSURE, self.config.camera_exposure)
            
            # White balance for underwater
            if hasattr(cv2, 'CAP_PROP_AUTO_WB'):
                if self.config.camera_auto_white_balance:
                    self.camera.set(cv2.CAP_PROP_AUTO_WB, 1)
                else:
                    self.camera.set(cv2.CAP_PROP_AUTO_WB, 0)
                    if hasattr(self.config, 'camera_white_balance'):
                        self.camera.set(cv2.CAP_PROP_WB_TEMPERATURE, self.config.camera_white_balance)
            
            # Contrast and saturation for seabed imaging
            if hasattr(cv2, 'CAP_PROP_CONTRAST'):
                contrast = getattr(self.config, 'camera_contrast', 50)
                self.camera.set(cv2.CAP_PROP_CONTRAST, contrast)
            
            if hasattr(cv2, 'CAP_PROP_SATURATION'):
                saturation = getattr(self.config, 'camera_saturation', 60)
                self.camera.set(cv2.CAP_PROP_SATURATION, saturation)
                
        except Exception as e:
            self.logger.warning(f"Some camera optimizations failed: {e}")
    
    async def _test_capture(self) -> bool:
        """Test camera capture capability."""
        self.logger.info("Testing camera capture...")
        
        try:
            for attempt in range(3):
                ret, frame = self.camera.read()
                if ret and (frame is not None):
                    height, width = frame.shape[:2]
                    self.logger.info(f"Test capture successful: {width}x{height}")
                    return True
                
                await asyncio.sleep(0.1)
            
            self.logger.error("Test capture failed after 3 attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"Test capture error: {e}")
            return False
    
    def capture_image(self):
        """Capture a single image from the camera."""
        if not self.is_initialized:
            self.logger.error("Camera not initialized")
            return None
            
        try:
            # Flush buffer by reading multiple frames to get the latest
            self.logger.debug("📷 CAM_CAPTURE_1: Flushing camera buffer")
            for _ in range(3):  # Flush old frames
                ret, _ = self.camera.read()
                if not ret:
                    break
                    
            # Now capture the actual frame
            self.logger.debug("📷 CAM_CAPTURE_2: Capturing fresh frame")
            ret, frame = self.camera.read()
            self.logger.debug(f"📷 CAM_CAPTURE_3: ret={ret}, frame_type={type(frame)}")
            
            # Fix: Separate boolean checks to avoid NumPy array evaluation issues
            if not ret:
                self.logger.error("🚨 CAM_ERROR_1: camera.read() returned False")
                return None
                
            if frame is None:
                self.logger.error("🚨 CAM_ERROR_2: frame is None")
                return None
                
            # Additional validation for frame
            if frame.size == 0:
                self.logger.error("🚨 CAM_ERROR_3: Captured empty frame")
                return None
                
            # Check if frame is completely black (potential issue)
            if frame.max() == 0:
                self.logger.warning("🚨 CAM_WARNING: Frame is completely black")
                
            # Check frame dimensions
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                self.logger.error(f"🚨 CAM_ERROR_4: Invalid frame shape: {frame.shape}")
                return None
                
            self.capture_count += 1
            self.last_capture_time = time.time()
            self.logger.debug(f"✅ Image captured successfully: {frame.shape}, min/max: {frame.min()}/{frame.max()}")
            
            return frame
            
        except Exception as e:
            self.logger.error(f"🚨 CAM_CAPTURE_ERROR: {e}")
            import traceback
            self.logger.error(f"🔍 CAM_TRACEBACK: {traceback.format_exc()}")
            return None
    
    async def capture_burst(self, count: int) -> list:
        """Capture multiple images in rapid succession."""
        images = []
        
        for i in range(count):
            image = await self.capture_image()
            if image is not None:
                images.append(image)
            else:
                self.logger.warning(f"Failed to capture image {i+1}/{count}")
            
            # Small delay to prevent overwhelming the camera
            await asyncio.sleep(0.01)
        
        return images
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera information and current settings."""
        if not self.is_initialized:
            return {}
        
        info = {
            'device_id': self.device_id,
            'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.camera.get(cv2.CAP_PROP_FPS),
            'capture_count': self.capture_count,
            'last_capture_time': self.last_capture_time,
        }
        
        # Add average capture time if available
        if self.capture_times:
            info['avg_capture_time_ms'] = (sum(self.capture_times) / len(self.capture_times)) * 1000
        
        return info
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get camera performance statistics."""
        if not self.capture_times:
            return {}
        
        times = self.capture_times
        return {
            'avg_capture_time_ms': sum(times) / len(times) * 1000,
            'min_capture_time_ms': min(times) * 1000,
            'max_capture_time_ms': max(times) * 1000,
            'total_captures': self.capture_count
        }
    
    async def reset_camera(self) -> bool:
        """Reset the camera connection."""
        self.logger.info("Resetting camera...")
        
        try:
            if self.camera:
                self.camera.release()
            
            await asyncio.sleep(1.0)
            
            return await self.initialize()
            
        except Exception as e:
            self.logger.error(f"Camera reset failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the camera gracefully."""
        self.logger.info("Shutting down camera...")
        
        try:
            if self.camera:
                self.camera.release()
                self.camera = None
            
            self.is_initialized = False
            
            # Log final statistics
            if self.capture_times:
                stats = self.get_performance_stats()
                self.logger.info(
                    f"Camera stats: {stats['total_captures']} captures, "
                    f"avg {stats['avg_capture_time_ms']:.1f}ms"
                )
            
            self.logger.info("Camera shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Camera shutdown error: {e}")


class CameraError(Exception):
    """Custom exception for camera-related errors."""
    pass
