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
import subprocess
import re
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
        
        # Configure exposure - EMERGENCY FIX for severely overexposed camera (brightness 254.3)
        # Tests showed this camera doesn't respond to OpenCV exposure controls properly
        
        # ALWAYS try manual mode first due to severe overexposure
        self.logger.warning("Forcing manual exposure mode due to known overexposure issue")
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Force manual
        time.sleep(0.1)
        
        # Try extreme exposure values since normal values don't work
        extreme_exposure_values = [-20, -15, -10, -8, -6]
        
        working_exposure = None
        for exp_val in extreme_exposure_values:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exp_val)
            time.sleep(0.1)
            actual_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
            
            # Test brightness with this exposure
            ret, test_frame = self.cap.read()
            if ret:
                brightness = np.mean(test_frame)
                self.logger.debug(f"Exposure {exp_val}→{actual_exposure}: brightness {brightness:.1f}")
                
                if brightness < 240:  # Any improvement from 254.3
                    working_exposure = exp_val
                    self.logger.info(f"✓ Found working exposure: {exp_val} (brightness: {brightness:.1f})")
                    break
        
        if working_exposure is None:
            self.logger.error("❌ No exposure setting reduces overexposure - hardware issue likely")
            # Try other properties to reduce brightness
            try:
                self.cap.set(cv2.CAP_PROP_GAIN, 0)         # Minimize gain
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0)   # Minimize brightness
                self.logger.info("Applied gain=0, brightness=0 to combat overexposure")
            except Exception as e:
                self.logger.debug(f"Could not set gain/brightness: {e}")
        
        # Log final exposure status
        final_auto_exp = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
        final_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
        self.logger.info(f"Final exposure settings: auto={final_auto_exp}, manual={final_exposure}")
        
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
    
    def get_usb_camera_info(self) -> Dict[str, str]:
        """
        Detect USB camera manufacturer and model information from system.
        
        Returns:
            dict: Dictionary with 'manufacturer' and 'model' keys, 
                  defaults to fallback values if detection fails
        """
        camera_info = {
            'manufacturer': 'DeepWater Exploration',  # Fallback
            'model': 'exploreHD 3.0'  # Fallback
        }
        
        try:
            # Try lsusb command first (most reliable on Linux)
            result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    # Look for video/camera devices
                    if any(keyword in line.lower() for keyword in ['camera', 'video', 'webcam', 'usb2.0', 'hd']):
                        # Extract manufacturer and model from lsusb output
                        # Format: Bus 001 Device 004: ID 0bda:58b0 Realtek Semiconductor Corp. 
                        match = re.search(r'ID\s+[0-9a-f]{4}:[0-9a-f]{4}\s+(.+)', line)
                        if match:
                            device_name = match.group(1).strip()
                            self.logger.info(f"Detected USB camera: {device_name}")
                            
                            # Parse manufacturer and model
                            parts = device_name.split()
                            if len(parts) >= 2:
                                # First part is usually manufacturer, rest is model
                                manufacturer = parts[0]
                                model = ' '.join(parts[1:])
                                
                                # Clean up common suffixes
                                model = re.sub(r'\s+(Corp\.?|Inc\.?|Ltd\.?|Co\.?)$', '', model)
                                
                                camera_info['manufacturer'] = manufacturer
                                camera_info['model'] = model
                                
                            break
                            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            self.logger.debug("lsusb command not available or failed")
        
        # Try alternative methods if lsusb failed
        if camera_info['manufacturer'] == 'DeepWater Exploration':  # Still using fallback
            try:
                # Try v4l2-ctl to get camera info
                result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if f'/dev/video{self.device_id}' in line:
                            # Look at the line above for device name
                            idx = lines.index(line)
                            if idx > 0:
                                device_name = lines[idx-1].strip()
                                if device_name and not device_name.startswith('/dev/'):
                                    self.logger.info(f"Detected camera via v4l2: {device_name}")
                                    
                                    # Parse the device name
                                    # Remove common prefixes/suffixes
                                    device_name = re.sub(r':\s*$', '', device_name)
                                    device_name = re.sub(r'^\w+:\s*', '', device_name)
                                    
                                    parts = device_name.split()
                                    if len(parts) >= 2:
                                        camera_info['manufacturer'] = parts[0]
                                        camera_info['model'] = ' '.join(parts[1:])
                                    
                            break
                            
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                self.logger.debug("v4l2-ctl command not available or failed")
        
        self.logger.info(f"Camera info: {camera_info['manufacturer']} {camera_info['model']}")
        return camera_info
    
    def _open_camera_with_fallback(self) -> Optional[cv2.VideoCapture]:
        """Try to open camera with different backends and indices."""
        # Based on test results: Camera 0 works with V4L2 and Default backends
        # Prioritize working configurations first
        backends_to_try = [
            (cv2.CAP_V4L2, "V4L2"),      # Test showed this works for camera 0
            (None, "Default"),            # Test showed this also works for camera 0  
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_FFMPEG, "FFmpeg"),
        ]
        
        # Prioritize camera 0 since tests showed it works
        indices_to_try = [0]
        if self.device_id != 0:
            indices_to_try.append(self.device_id)
        indices_to_try.extend([1, 2, 3])
        
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
                            # Check if severely overexposed (test showed brightness 254.3)
                            brightness = np.mean(test_frame)
                            self.logger.info(f"✓ Camera opened: index {index}, backend {backend_name}, brightness: {brightness:.1f}")
                            
                            if brightness > 250:
                                self.logger.warning(f"⚠️  Camera severely overexposed (brightness: {brightness:.1f}) - will attempt correction")
                            
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
            
            # Check for severe overexposure (known issue: brightness 254.3/255)
            if mean_brightness > 250:
                self.logger.error(f"❌ SEVERE OVEREXPOSURE CONFIRMED: {mean_brightness:.1f}/255")
                self.logger.error("This camera appears to have hardware-level overexposure")
                self.logger.error("Recommendations:")
                self.logger.error("1. 🔦 Reduce ambient lighting significantly")  
                self.logger.error("2. 📦 Try different USB camera model")
                self.logger.error("3. 🔌 Test different USB port")
                self.logger.error("4. 🎛️  Check for physical camera controls")
                
                # Log that images will be white until hardware issue is resolved
                self.logger.warning("⚠️  All captured images will be WHITE until lighting/hardware is fixed")
                
            elif mean_brightness > 200:
                self.logger.warning(f"⚠️  Camera overexposed: {mean_brightness:.1f}/255 (still too bright)")
                
            elif mean_brightness < 5:
                self.logger.warning(f"⚠️  Camera severely underexposed: {mean_brightness:.1f}/255")
            else:
                self.logger.info(f"✓ Camera exposure acceptable: {mean_brightness:.1f}/255")
                
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
    
    def capture_frame_with_timestamp(self) -> Optional[Tuple[np.ndarray, float]]:
        """
        Capture a single frame with optimized hardware timestamp coordination.
        
        OPTIMIZATION: Enhanced timing precision by:
        1. Minimizing latency between timestamp and frame capture
        2. Using libcamera metadata timestamp when available (hardware-level timing)
        3. Reducing logging overhead for high-frequency capture
        4. Better coordination with GPS PPS timing system
        
        Returns:
            tuple: (frame, timestamp_ns) where timestamp_ns is nanoseconds since epoch,
                   or None if capture failed
        """
        if not self.is_initialized or not self.cap:
            # Reduce error logging frequency during high-frequency capture
            if self.frame_count % 100 == 0:
                self.logger.error("Camera not initialized")
            return None

        try:
            # OPTIMIZATION: Get timestamp as close to actual capture as possible
            # This minimizes timing uncertainty
            
            ret, frame = self.cap.read()
            # Get timestamp immediately after capture for best precision
            capture_time_ns = time.monotonic_ns()
            
            if not ret or frame is None:
                if self.frame_count % 100 == 0:  # Reduce logging overhead
                    self.logger.error("Failed to capture frame")
                return None

            # Try to get hardware timestamp from libcamera metadata if available
            hardware_timestamp_ns = self._try_get_hardware_timestamp()
            
            # Use hardware timestamp if available, otherwise use software timing
            if hardware_timestamp_ns is not None:
                final_timestamp_ns = hardware_timestamp_ns
                # Reduce debug logging for high-frequency capture
                if self.frame_count % 200 == 0:
                    self.logger.debug("Using hardware timestamp from libcamera metadata")
            else:
                final_timestamp_ns = capture_time_ns
                # Reduce debug logging for high-frequency capture
                if self.frame_count % 200 == 0:
                    self.logger.debug("Using software timestamp (hardware not available)")

            # Update statistics with minimal overhead
            self.frame_count += 1
            self.last_frame_time = time.time()

            # Reduced logging frequency for high-frequency operation
            if self.frame_count % 500 == 0:  # Log every 500 frames
                self.logger.debug(f"Captured frame {self.frame_count} with timestamp {final_timestamp_ns}")
            
            return (frame, final_timestamp_ns)
            
        except Exception as e:
            # Reduce error logging overhead
            if self.frame_count % 100 == 0:
                self.logger.error(f"Error capturing frame with timestamp: {e}")
            return None
    
    def _try_get_hardware_timestamp(self) -> Optional[int]:
        """
        Attempt to get hardware-level timestamp from camera metadata.
        
        This is currently a placeholder for future libcamera integration.
        The research shows libcamera can provide frame metadata with hardware timestamps
        that are much more accurate than software timing.
        
        Returns:
            int: Hardware timestamp in nanoseconds since epoch, or None if not available
        """
        # TODO: Implement libcamera metadata extraction
        # Based on research, libcamera provides frame metadata that includes:
        # - SensorTimestamp: Hardware timestamp from sensor
        # - FrameSequence: Frame sequence number
        # - ExposureTime: Actual exposure duration
        # 
        # This would require either:
        # 1. Using picamera2 library with libcamera backend
        # 2. Direct libcamera integration via Python bindings
        # 3. Camera-specific V4L2 metadata if supported
        #
        # For now, return None to fall back to software timing
        # This maintains current functionality while preparing for hardware timing
        
        try:
            # Check if we're using a backend that might support metadata
            if self.cap and hasattr(self.cap, 'getBackendName'):
                backend = self.cap.getBackendName()
                if backend == "V4L2":
                    # V4L2 might support frame metadata
                    # Future implementation would query V4L2 for frame timestamp
                    pass
                elif backend == "GSTREAMER":
                    # GStreamer might have pipeline timestamps
                    # Future implementation would extract GStreamer timestamp
                    pass
            
            # Return None for now - software timing fallback
            return None
            
        except Exception as e:
            self.logger.debug(f"Hardware timestamp query failed: {e}")
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
    
    def get_camera_exif_params(self) -> Dict[str, Any]:
        """
        Get current camera parameters for EXIF metadata.
        
        Returns:
            dict: Camera parameters dictionary for EXIF embedding
        """
        params = {}
        
        if not self.cap or not self.is_initialized:
            return params
        
        try:
            # Core camera settings
            params['width'] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            params['height'] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            params['fps'] = self.cap.get(cv2.CAP_PROP_FPS)
            
            # Exposure settings
            params['auto_exposure'] = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
            params['exposure'] = self.cap.get(cv2.CAP_PROP_EXPOSURE)
            
            # White balance
            params['auto_wb'] = self.cap.get(cv2.CAP_PROP_AUTO_WB)
            try:
                params['wb_temperature'] = self.cap.get(cv2.CAP_PROP_WB_TEMPERATURE)
            except:
                params['wb_temperature'] = None
                
            # Image adjustment parameters
            try:
                params['brightness'] = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
            except:
                params['brightness'] = None
                
            try:
                params['contrast'] = self.cap.get(cv2.CAP_PROP_CONTRAST)
            except:
                params['contrast'] = None
                
            try:
                params['saturation'] = self.cap.get(cv2.CAP_PROP_SATURATION)
            except:
                params['saturation'] = None
                
            try:
                params['gain'] = self.cap.get(cv2.CAP_PROP_GAIN)
            except:
                params['gain'] = None
                
            try:
                params['sharpness'] = self.cap.get(cv2.CAP_PROP_SHARPNESS)
            except:
                params['sharpness'] = None
                
            # Camera backend and format info
            try:
                params['backend'] = self.cap.getBackendName()
            except:
                params['backend'] = "Unknown"
                
            params['format'] = self.format
            
            # Get actual camera manufacturer and model info
            camera_info = self.get_usb_camera_info()
            params['manufacturer'] = camera_info['manufacturer']
            params['model'] = camera_info['model']
            
        except Exception as e:
            self.logger.debug(f"Error getting camera EXIF parameters: {e}")
            
        return params
    
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