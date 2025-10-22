#!/usr/bin/env python3
"""
Camera Module for BathyCat Seabed Imager
========================================

Handles USB camera interfacing using OpenCV with proper error handling,
configuration management, and frame capture optimization.

Features:
- USB camera detection and initialization
- Configurable resolution, format, and camera settings
- Frame capture with error handling
- Camera health monitoring
- Auto-exposure and white balance control
"""

import cv2
import logging
import time
from typing import Optional, Tuple, Dict, Any
import numpy as np


class CameraError(Exception):
    """Custom exception for camera-related errors."""
    pass


class Camera:
    """
    USB Camera interface for BathyCat system.
    
    Provides reliable camera access with configuration management and error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize camera with configuration.
        
        Args:
            config: Camera configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_initialized = False
        self.last_frame_time = 0
        self.frame_count = 0
        
        # Camera settings from config
        self.device_id = config.get('camera_device_id', 0)
        self.width = config.get('camera_width', 1920)
        self.height = config.get('camera_height', 1080)
        self.fps = config.get('camera_fps', 30)
        self.format = config.get('camera_format', 'MJPG')
        self.auto_exposure = config.get('camera_auto_exposure', True)
        self.auto_white_balance = config.get('camera_auto_white_balance', True)
        self.contrast = config.get('camera_contrast', 50)
        self.saturation = config.get('camera_saturation', 60)
        self.exposure = config.get('camera_exposure', -6)
        self.white_balance = config.get('camera_white_balance', 4000)
        
    def initialize(self) -> bool:
        """
        Initialize camera connection and configure settings.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing camera {self.device_id}")
            
            # Try to initialize camera with different backends and indices
            self.cap = self._open_camera_with_fallback()
            
            if not self.cap or not self.cap.isOpened():
                raise CameraError(f"Failed to open camera device {self.device_id}")
            
            # Configure camera settings
            self._configure_camera()
            
            # Test capture a frame to verify functionality
            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise CameraError("Failed to capture test frame")
            
            self.is_initialized = True
            self.logger.info("Camera initialized successfully")
            self.logger.info(f"Camera resolution: {self.width}x{self.height}")
            self.logger.info(f"Camera FPS: {self.fps}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            self._cleanup()
            return False
    
    def _configure_camera(self) -> None:
        """Configure camera properties based on config."""
        if not self.cap:
            raise CameraError("Camera not initialized")
        
        # Set video format
        if self.format == 'MJPG':
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Set FPS
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Configure exposure - try multiple methods as OpenCV constants vary
        if self.auto_exposure:
            # Try different auto-exposure values as they vary by camera and OpenCV version
            tried_values = []
            
            # Method 1: Standard values
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            auto_exp_val = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
            tried_values.append(f"0.75→{auto_exp_val}")
            
            # Method 2: If 0.75 didn't work, try 1
            if abs(auto_exp_val - 0.75) > 0.01:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)
                auto_exp_val = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
                tried_values.append(f"1.0→{auto_exp_val}")
                
            # Method 3: If neither worked, try 3 (some cameras use this)
            if auto_exp_val in [0, 0.25]:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3.0)
                auto_exp_val = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
                tried_values.append(f"3.0→{auto_exp_val}")
            
            self.logger.info(f"Camera auto-exposure ENABLED (tried: {', '.join(tried_values)})")
            
            # Also try to disable manual exposure controls that might override auto
            try:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, -1)  # Let camera decide
            except:
                pass
        else:
            # Manual exposure - be more explicit about disabling auto first
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Disable auto
            time.sleep(0.1)  # Brief pause for camera to switch modes
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
            actual_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
            self.logger.info(f"Camera manual exposure set to {self.exposure} (got: {actual_exposure})")
        
        # Configure white balance with better error handling
        if self.auto_white_balance:
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 1)
            actual_auto_wb = self.cap.get(cv2.CAP_PROP_AUTO_WB)
            
            if actual_auto_wb == 1:
                self.logger.info("Camera auto-white balance ENABLED")
            else:
                self.logger.warning(f"Auto white balance may not be supported (set: 1, got: {actual_auto_wb})")
        else:
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)  # Disable auto WB
            time.sleep(0.1)  # Brief pause 
            self.cap.set(cv2.CAP_PROP_WB_TEMPERATURE, self.white_balance)
            actual_wb_temp = self.cap.get(cv2.CAP_PROP_WB_TEMPERATURE)
            self.logger.info(f"Camera manual white balance set to {self.white_balance}K (got: {actual_wb_temp}K)")
        
        # Set other properties if supported
        try:
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
            self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation)
        except Exception as e:
            self.logger.debug(f"Could not set contrast/saturation: {e}")
        
        # Add overexposure protection - reduce gain if supported
        try:
            self.cap.set(cv2.CAP_PROP_GAIN, 0)  # Minimize gain to prevent overexposure
        except Exception as e:
            self.logger.debug(f"Could not set gain: {e}")
        
        # Log actual settings after configuration
        self._log_camera_properties()
        
        # Test for overexposure after initial configuration
        self._check_for_overexposure()
    
    def _open_camera_with_fallback(self) -> Optional[cv2.VideoCapture]:
        """Try to open camera with different backends and indices."""
        # List of (backend, description) tuples to try
        backends_to_try = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_FFMPEG, "FFmpeg"),
            (None, "Default")  # Let OpenCV choose
        ]
        
        # Try different camera indices (sometimes camera shows up on different index)
        indices_to_try = [self.device_id, 0, 1, 2, 3]
        if self.device_id not in indices_to_try:
            indices_to_try.insert(0, self.device_id)
        
        for backend, backend_name in backends_to_try:
            for index in indices_to_try:
                try:
                    self.logger.debug(f"Trying camera index {index} with {backend_name} backend")
                    
                    if backend is None:
                        cap = cv2.VideoCapture(index)
                    else:
                        cap = cv2.VideoCapture(index, backend)
                    
                    if cap.isOpened():
                        # Test if we can actually read from it
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            self.logger.info(f"✓ Camera opened successfully: index {index}, backend {backend_name}")
                            self.device_id = index  # Update device_id to working index
                            return cap
                        else:
                            cap.release()
                            
                except Exception as e:
                    self.logger.debug(f"Failed to open camera index {index} with {backend_name}: {e}")
                    
        self.logger.error("Failed to open camera with any backend/index combination")
        return None
    
    def _log_camera_properties(self) -> None:
        """Log actual camera properties for debugging."""
        if not self.cap:
            return
        
        try:
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            self.logger.info(f"Actual camera properties:")
            self.logger.info(f"  Resolution: {actual_width}x{actual_height}")
            self.logger.info(f"  FPS: {actual_fps}")
            
            # Log auto exposure and white balance status
            try:
                auto_exposure = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
                exposure_value = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                auto_wb = self.cap.get(cv2.CAP_PROP_AUTO_WB)
                wb_temp = self.cap.get(cv2.CAP_PROP_WB_TEMPERATURE)
                
                self.logger.info(f"  Auto exposure: {auto_exposure} (0.25=manual, 0.75=auto)")
                self.logger.info(f"  Exposure value: {exposure_value}")
                self.logger.info(f"  Auto white balance: {auto_wb} (0=manual, 1=auto)")
                self.logger.info(f"  White balance temp: {wb_temp}K")
                
            except Exception as e:
                self.logger.debug(f"Could not read exposure/WB properties: {e}")
            
        except Exception as e:
            self.logger.debug(f"Could not read camera properties: {e}")
    
    def _check_for_overexposure(self) -> None:
        """Check for overexposure and attempt automatic correction."""
        if not self.cap:
            return
        
        try:
            # Use shorter delay to not block initialization
            time.sleep(0.5)
            
            # Capture test frame
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.logger.debug("Could not capture test frame for exposure check")
                return
            
            # Calculate mean brightness
            mean_brightness = np.mean(frame)
            self.logger.info(f"Initial camera brightness: {mean_brightness:.1f}/255")
            
            # Check for severe overexposure (completely white images)
            if mean_brightness > 250:
                self.logger.warning("Camera appears severely OVEREXPOSED - attempting quick correction")
                
                # Try to fix overexposure with minimal delay
                if self.auto_exposure:
                    # Switch to manual with very low exposure
                    self.logger.info("Switching to manual exposure to fix overexposure")
                    self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual
                    self.cap.set(cv2.CAP_PROP_EXPOSURE, -10)  # Very low exposure
                else:
                    # Already in manual mode, reduce exposure further
                    current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                    new_exposure = min(current_exposure - 5, -10)  # Reduce significantly
                    self.cap.set(cv2.CAP_PROP_EXPOSURE, new_exposure)
                    self.logger.info(f"Reduced manual exposure from {current_exposure} to {new_exposure}")
                
                # Quick test without full delay
                time.sleep(0.2)
                ret, frame = self.cap.read()
                if ret:
                    new_brightness = np.mean(frame)
                    self.logger.info(f"After exposure correction: {new_brightness:.1f}/255")
                    
                    if new_brightness < 240:  # Improved
                        self.logger.info("✓ Overexposure correction appears successful")
                    else:
                        self.logger.error("❌ Still overexposed - may need hardware adjustment")
            
            elif mean_brightness < 5:
                self.logger.warning("Camera appears severely UNDEREXPOSED")
            else:
                self.logger.info("✓ Camera exposure appears normal")
                
        except Exception as e:
            self.logger.debug(f"Error in overexposure check: {e}")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera.
        
        Returns:
            np.ndarray: Captured frame, or None if capture failed
        """
        if not self.is_initialized or not self.cap:
            self.logger.error("Camera not initialized")
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                self.logger.error("Failed to capture frame")
                return None
            
            # Update statistics
            self.frame_count += 1
            self.last_frame_time = time.time()
            
            self.logger.debug(f"Captured frame {self.frame_count}, size: {frame.shape}")
            return frame
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return None
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Get camera information and status.
        
        Returns:
            dict: Camera information dictionary
        """
        info = {
            'device_id': self.device_id,
            'initialized': self.is_initialized,
            'frame_count': self.frame_count,
            'last_frame_time': self.last_frame_time,
            'configured_resolution': f"{self.width}x{self.height}",
            'configured_fps': self.fps,
            'format': self.format
        }
        
        if self.cap and self.is_initialized:
            try:
                info.update({
                    'actual_width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'actual_height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'actual_fps': int(self.cap.get(cv2.CAP_PROP_FPS)),
                    'backend': self.cap.getBackendName()
                })
            except Exception as e:
                self.logger.debug(f"Could not get detailed camera info: {e}")
        
        return info
    
    def is_healthy(self) -> bool:
        """
        Check camera health status.
        
        Returns:
            bool: True if camera is healthy, False otherwise
        """
        if not self.is_initialized or not self.cap:
            return False
        
        # Check if we can capture a frame
        try:
            ret, _ = self.cap.read()
            return ret
        except Exception:
            return False
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect camera.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        self.logger.info("Attempting camera reconnection")
        self._cleanup()
        return self.initialize()
    
    def _cleanup(self) -> None:
        """Clean up camera resources."""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_initialized = False
    
    def close(self) -> None:
        """Close camera connection and clean up resources."""
        self.logger.info("Closing camera")
        self._cleanup()


def test_camera(config: Dict[str, Any]) -> bool:
    """
    Test camera functionality with given configuration.
    
    Args:
        config: Camera configuration dictionary
        
    Returns:
        bool: True if camera test passed, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        camera = Camera(config)
        
        if not camera.initialize():
            logger.error("Camera initialization failed")
            return False
        
        # Capture a few test frames
        for i in range(3):
            frame = camera.capture_frame()
            if frame is None:
                logger.error(f"Failed to capture test frame {i+1}")
                return False
            
            logger.info(f"Test frame {i+1}: {frame.shape}")
            time.sleep(0.5)
        
        # Print camera info
        info = camera.get_camera_info()
        logger.info(f"Camera info: {info}")
        
        # Test health check
        health = camera.is_healthy()
        logger.info(f"Camera health: {health}")
        
        camera.close()
        logger.info("Camera test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Camera test failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'camera_device_id': 0,
        'camera_width': 1920,
        'camera_height': 1080,
        'camera_fps': 30,
        'camera_format': 'MJPG',
        'camera_auto_exposure': True,
        'camera_auto_white_balance': True,
        'camera_contrast': 50,
        'camera_saturation': 60,
        'camera_exposure': -6,
        'camera_white_balance': 4000
    }
    
    success = test_camera(test_config)
    exit(0 if success else 1)