#!/usr/bin/env python3
"""
Main Service Application for BathyCat Seabed Imager
==================================================

Coordinates all system modules including camera, GPS, image processing, 
storage, and LED feedback to provide autonomous image capture with geotagging.

Features:
- System initialization and coordination
- Continuous image capture loop
- GPS fix monitoring and validation
- Error handling and recovery
- Status reporting and logging
- Service lifecycle management
"""

import sys
import time
import signal
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import json

# Import BathyCat modules
from camera import Camera, CameraError
# Import GPS with explicit local module to avoid conflict with system gps module
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from gps import GPS, GPSError, GPSFix
from image_processor import ImageProcessor, ImageProcessingError
from storage import StorageManager, StorageError
from led_status import LEDManager


@dataclass
class SystemStatus:
    """System status data structure."""
    running: bool = False
    start_time: Optional[datetime] = None
    images_captured: int = 0
    last_capture_time: Optional[datetime] = None
    errors_encountered: int = 0
    last_error_time: Optional[datetime] = None
    gps_fix_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'images_captured': self.images_captured,
            'last_capture_time': self.last_capture_time.isoformat() if self.last_capture_time else None,
            'errors_encountered': self.errors_encountered,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'gps_fix_time': self.gps_fix_time.isoformat() if self.gps_fix_time else None
        }


class BathyCatService:
    """
    Main BathyCat service application.
    
    Coordinates all subsystems to provide autonomous seabed imaging capability.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize BathyCat service with configuration.
        
        Args:
            config: System configuration dictionary
        """
        self.config = config
        self.logger = self._setup_logging()
        
        # Service settings
        self.capture_fps = config.get('capture_fps', 4.0)
        self.capture_interval = 1.0 / self.capture_fps
        self.require_gps_fix = config.get('require_gps_fix', False)
        self.gps_fix_timeout = config.get('gps_fix_timeout', 300.0)
        self.status_report_interval = config.get('status_report_interval', 30)
        self.watchdog_enabled = config.get('watchdog_enabled', True)
        
        # System components
        self.camera: Optional[Camera] = None
        self.gps: Optional[GPS] = None
        self.image_processor: Optional[ImageProcessor] = None
        self.storage: Optional[StorageManager] = None
        self.led_manager: Optional[LEDManager] = None
        
        # Service state
        self.status = SystemStatus()
        self.is_running = False
        self.shutdown_requested = False
        
        # Image sequence counter for unique filenames (resets daily)
        self.image_sequence_counter = 0
        self.current_date = datetime.now().date()
        
        # High-precision timing system
        self._boot_time_offset = None
        self._last_monotonic_sync = 0
        self._sync_monotonic_time()
        
        # Threading
        self.main_thread: Optional[threading.Thread] = None
        self.status_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Component health tracking
        self.component_health = {
            'camera': False,
            'gps': False,
            'storage': False,
            'led': False
        }
        
        # Performance tracking
        self.last_health_check = 0
        self.health_check_interval = 10.0  # seconds
        
        # Error tracking
        self.consecutive_errors = 0
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('bathycat')
        
        # Configure logging level
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if enabled
        if self.config.get('log_to_file', True):
            base_log_file = self.config.get('log_file_path', '/media/usb/bathyimager/logs/bathyimager.log')
            try:
                import os
                # Ensure USB base directory exists
                base_dir = os.path.dirname(base_log_file)
                if not os.path.exists(base_dir):
                    logger.warning(f"USB log directory doesn't exist, creating: {base_dir}")
                    os.makedirs(base_dir, exist_ok=True)
                
                # Generate date-stamped log path (same structure as images)
                dated_log_file = self._get_dated_log_path(base_log_file)
                
                # Create file handler in append mode (adds to existing daily logs)
                file_handler = logging.FileHandler(dated_log_file, mode='a')
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                
                logger.info(f"📝 Date-stamped logging enabled: {dated_log_file}")
                
                # Track current log date for rotation detection
                self._log_date = datetime.now().strftime('%Y%m%d')
                
            except Exception as e:
                logger.warning(f"Could not setup file logging to USB: {e}")
                logger.warning(f"Trying fallback logging to /tmp/bathyimager.log")
                try:
                    # Fallback to temporary directory if USB fails
                    fallback_path = "/tmp/bathyimager.log"
                    file_handler = logging.FileHandler(fallback_path, mode='a')
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)
                    logger.warning(f"📝 Fallback logging enabled: {fallback_path}")
                except Exception as e2:
                    logger.error(f"Could not setup any file logging: {e2}")
                    logger.error("Only console logging will be available")
        
        return logger
    
    def _get_dated_log_path(self, base_log_path: str, timestamp: Optional[datetime] = None) -> str:
        """
        Generate date-stamped log path similar to image directory structure.
        
        Args:
            base_log_path: Base log file path from config
            timestamp: Timestamp for date (uses current time if None)
            
        Returns:
            str: Date-stamped log file path (e.g., /media/usb/bathyimager/logs/20241104/bathyimager.log)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Extract directory and filename from base path
        log_dir = os.path.dirname(base_log_path)
        log_filename = os.path.basename(base_log_path)
        
        # Create date directory: YYYYMMDD format (same as images)
        date_dir = f"{timestamp.year:04d}{timestamp.month:02d}{timestamp.day:02d}"
        dated_log_dir = os.path.join(log_dir, date_dir)
        
        # Ensure directory exists
        os.makedirs(dated_log_dir, exist_ok=True)
        
        full_path = os.path.join(dated_log_dir, log_filename)
        
        # Log the structure being created (only on first creation)
        if not os.path.exists(full_path):
            # This will log to console since file handler may not be set up yet
            print(f"📁 Creating dated log structure: {dated_log_dir}")
        
        # Return full dated log path
        return full_path
    
    def _rotate_log_if_needed(self) -> None:
        """
        Rotate log file to new date if date has changed since initialization.
        This ensures each day gets its own log file, similar to image directories.
        """
        if not self.config.get('log_to_file', True):
            return
            
        try:
            current_date = datetime.now().strftime('%Y%m%d')
            
            # Check if we need to rotate (compare with initialization date)
            if not hasattr(self, '_log_date') or self._log_date != current_date:
                self._log_date = current_date
                
                # Get new dated log path
                base_log_file = self.config.get('log_file_path', '/media/usb/bathyimager/logs/bathyimager.log')
                new_log_file = self._get_dated_log_path(base_log_file)
                
                # Remove existing file handlers
                for handler in self.logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        self.logger.removeHandler(handler)
                
                # Add new file handler for new date
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler = logging.FileHandler(new_log_file, mode='a')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                
                self.logger.info(f"📝 Log rotated to new date: {new_log_file}")
                
        except Exception as e:
            self.logger.warning(f"Log rotation failed: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def initialize(self) -> bool:
        """
        Initialize all system components.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing BathyCat Seabed Imager")
            
            # Initialize LED system first for status indication
            self.led_manager = LEDManager(self.config)
            if self.led_manager.initialize():
                self.component_health['led'] = True
                self.led_manager.set_power_on(True)
            else:
                self.logger.warning("LED system initialization failed")
            
            # Initialize storage system
            self.logger.info("Initializing storage system")
            self.storage = StorageManager(self.config)
            if self.storage.initialize():
                self.component_health['storage'] = True
                # Report where images will be saved
                storage_info = self.storage.get_storage_info()
                self.logger.info(f"Storage system ready - Images saving to: {storage_info['base_path']}")
                self.logger.info(f"Storage space: {storage_info['free_space_gb']:.1f} GB free of {storage_info['total_space_gb']:.1f} GB total")
            else:
                self.logger.error(f"Storage initialization failed - Images will NOT be saved")
                storage_info = self.storage.get_storage_info() if self.storage else None
                if storage_info:
                    self.logger.error(f"Failed storage path: {storage_info['base_path']}")
                return False
            
            # Initialize camera system
            self.logger.info("Initializing camera system")
            self.camera = Camera(self.config)
            if self.camera.initialize():
                self.component_health['camera'] = True
                self.logger.info("Camera system ready")
            else:
                self.logger.warning("Camera initialization failed - will retry during operation")
                self.component_health['camera'] = False
                # Don't return False - continue with service startup
            
            # Initialize GPS system
            self.logger.info("Initializing GPS system")
            self.gps = GPS(self.config)
            if self.gps.connect() and self.gps.start_reading():
                self.component_health['gps'] = True
                self.logger.info("GPS system ready")
                if self.gps.time_sync:
                    self.logger.info("GPS time synchronization enabled - system time will be synced when GPS fix acquired")
                else:
                    self.logger.info("GPS time synchronization disabled - using local system time")
            else:
                self.logger.warning("GPS initialization failed")
                if self.require_gps_fix:
                    return False
            
            # Initialize image processor
            self.logger.info("Initializing image processing")
            self.image_processor = ImageProcessor(self.config)
            self.logger.info("Image processor ready")
            
            # Wait for GPS fix if required
            if self.require_gps_fix and self.gps:
                self.logger.info("Waiting for GPS fix...")
                if self.led_manager:
                    self.led_manager.set_gps_status(False, acquiring=True)
                
                gps_fix = self.gps.wait_for_fix(self.gps_fix_timeout)
                if gps_fix:
                    self.logger.info("GPS fix acquired")
                    self.status.gps_fix_time = datetime.now()
                    if self.led_manager:
                        self.led_manager.set_gps_status(True)
                else:
                    self.logger.error("Failed to acquire GPS fix within timeout")
                    return False
            
            # Update LED status
            if self.led_manager:
                self._update_led_status()
            
            self.logger.info("BathyCat initialization complete")
            self.logger.info(f"🚀 Image sequence counter initialized: {self.image_sequence_counter}, current date: {self.current_date}")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    def start(self) -> bool:
        """
        Start the main service.
        
        Returns:
            bool: True if service started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Service already running")
            return True
        
        try:
            self.logger.info("Starting BathyCat service")
            
            # Initialize if not already done
            if not all([self.camera, self.storage, self.image_processor]):
                if not self.initialize():
                    return False
            
            # Update status
            self.status.running = True
            self.status.start_time = datetime.now()
            self.is_running = True
            self.shutdown_event.clear()
            
            # Start main capture loop
            self.main_thread = threading.Thread(target=self._main_loop, daemon=False)
            self.main_thread.start()
            
            # Start status reporting thread
            self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
            self.status_thread.start()
            
            self.logger.info(f"BathyCat service started (capture rate: {self.capture_fps} fps)")
            return True
            
        except Exception as e:
            self.logger.error(f"Service start failed: {e}")
            return False
    
    def _main_loop(self) -> None:
        """Main capture loop (runs in separate thread)."""
        self.logger.info("Main capture loop started")
        
        last_capture_time = 0
        max_consecutive_errors = 10
        
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Check if it's time to capture
                if current_time - last_capture_time >= self.capture_interval:
                    
                    # Perform health checks periodically
                    if current_time - self.last_health_check >= self.health_check_interval:
                        self._check_component_health()
                    
                    # Check if log needs to rotate to new date
                    self._rotate_log_if_needed()
                    
                    # Attempt image capture
                    if self._capture_image():
                        last_capture_time = current_time
                        self.consecutive_errors = 0
                    else:
                        self.consecutive_errors += 1
                        self.status.errors_encountered += 1
                        self.status.last_error_time = datetime.now()
                        
                        # Handle excessive errors
                        if self.consecutive_errors >= max_consecutive_errors:
                            self.logger.error(f"Too many consecutive errors ({self.consecutive_errors}), attempting recovery")
                            if not self._attempt_recovery():
                                self.logger.critical("Recovery failed, shutting down")
                                break
                            self.consecutive_errors = 0
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.consecutive_errors += 1
                time.sleep(1.0)  # Brief pause on error
        
        self.logger.info("Main capture loop ended")
    
    def _capture_image(self) -> bool:
        """
        Capture and process a single image.
        
        Returns:
            bool: True if capture successful, False otherwise
        """
        try:
            # Capture frame from camera (with retry logic)
            if not self.camera or not self.camera.is_initialized:
                # Try to reconnect camera
                self.logger.info("Attempting camera reconnection...")
                if self.camera and self.camera.reconnect():
                    self.component_health['camera'] = True
                    self.logger.info("Camera reconnected successfully")
                else:
                    self.logger.debug("Camera not available - skipping capture")
                    return False
            
            # TIMING: Start capture pipeline measurement  
            pipeline_start = time.perf_counter()
            
            # OPTIMIZED TIMING: Use hardware timestamp when available for maximum accuracy
            # Try hardware timestamping first (reduces 1.5s offset to <80ms)
            frame_with_timestamp = self.camera.capture_frame_with_timestamp()
            capture_time = (time.perf_counter() - pipeline_start) * 1000  # ms
            
            if frame_with_timestamp is None:
                self.logger.warning("Failed to capture camera frame - will try reconnect next time")
                self.component_health['camera'] = False
                if self.camera:
                    self.camera.is_initialized = False
                return False
            
            frame, hardware_timestamp_ns = frame_with_timestamp
            
            # Convert hardware timestamp to datetime (if available) or use software timestamp
            if hardware_timestamp_ns is not None:
                # Hardware timestamp is in nanoseconds since monotonic start
                # Convert to UTC using our boot time offset
                if self._boot_time_offset is not None:
                    utc_ns = hardware_timestamp_ns + self._boot_time_offset
                    timestamp = datetime.fromtimestamp(utc_ns / 1_000_000_000, tz=timezone.utc)
                    self.logger.debug("Using hardware-level camera timestamp")
                else:
                    # Fallback to software timestamp if boot offset not available
                    timestamp = self._get_precise_capture_timestamp()
                    self.logger.debug("Hardware timestamp available but boot offset missing, using software timestamp")
            else:
                # No hardware timestamp available, use software timing
                timestamp = self._get_precise_capture_timestamp()
                self.logger.debug("No hardware timestamp available, using software timestamp")
            
            # Get GPS fix
            gps_start = time.perf_counter()
            gps_fix = None
            if self.gps:
                gps_fix = self.gps.get_current_fix()
                
                # Resync monotonic time if GPS has recently synced system time
                if (self.gps.system_time_synced and 
                    hasattr(self.gps, 'last_time_sync') and
                    time.time() - self.gps.last_time_sync < 60):  # Within last minute
                    if time.time() - self._last_monotonic_sync > 60:  # Haven't synced in last minute
                        self._sync_monotonic_time()
                
                # Check if we require valid GPS fix (skip excessive debug logging for performance)
                if self.require_gps_fix and (not gps_fix or not gps_fix.is_valid):
                    return False
            gps_time = (time.perf_counter() - gps_start) * 1000  # ms
            
            # Get camera parameters for EXIF metadata
            camera_params = None
            if self.camera:
                camera_params = self.camera.get_camera_exif_params()
                
            # Process image
            process_start = time.perf_counter()
            processed_image = self.image_processor.process_frame(frame, gps_fix, timestamp, camera_params)
            process_time = (time.perf_counter() - process_start) * 1000  # ms
            
            # Update sequence counter for unique filenames
            self._update_sequence_counter(timestamp)
            
            # Save to storage
            save_start = time.perf_counter()
            self.logger.debug(f"🔢 Passing sequence counter {self.image_sequence_counter} to storage")
            filepath = self.storage.save_image(processed_image, timestamp, self.image_sequence_counter)
            save_time = (time.perf_counter() - save_start) * 1000  # ms
            
            # Calculate total pipeline time
            total_time = (time.perf_counter() - pipeline_start) * 1000  # ms
            
            if filepath:
                # Update statistics
                self.status.images_captured += 1
                self.status.last_capture_time = timestamp
                
                # Signal successful capture
                if self.led_manager:
                    self.led_manager.signal_capture()
                
                # Log pipeline timing breakdown for performance analysis
                self.logger.debug(f"🚀 Pipeline timing: Total={total_time:.1f}ms (Capture={capture_time:.1f}ms, GPS={gps_time:.1f}ms, Process={process_time:.1f}ms, Save={save_time:.1f}ms)")
                self.logger.debug(f"Image captured: {filepath}")
                return True
            else:
                self.logger.warning("Failed to save image")
                return False
                
        except Exception as e:
            self.logger.error(f"Image capture failed: {e}")
            return False
        finally:
            # Reset camera LED status
            if self.led_manager:
                self.led_manager.set_camera_status(self.component_health['camera'])
    
    def _get_accurate_timestamp(self, gps_fix: Optional['GPSFix']) -> datetime:
        """
        Get accurate timestamp using GPS time when available, system time otherwise.
        
        Args:
            gps_fix: Current GPS fix (can be None)
            
        Returns:
            datetime: Always returns UTC timestamp for consistency
        """
        # Always use UTC for consistency in image metadata
        timestamp = datetime.now(timezone.utc)
        
        # Log the time source for debugging
        if (self.gps and hasattr(self.gps, 'system_time_synced') and 
            self.gps.system_time_synced):
            self.logger.debug(f"📅 Using GPS-synchronized UTC time: {timestamp.isoformat()}")
        else:
            self.logger.debug(f"📅 Using system UTC time (GPS not yet synced): {timestamp.isoformat()}")
        
        return timestamp
        
    def _sync_monotonic_time(self) -> None:
        """
        Synchronize monotonic time with system time for high-precision timestamping.
        
        This establishes the relationship between time.monotonic_ns() (which never jumps
        but has arbitrary start point) and actual UTC time. Should be called periodically
        to account for any GPS time corrections.
        """
        try:
            # Get current times as close together as possible
            monotonic_ns = time.monotonic_ns()
            utc_time = datetime.now(timezone.utc)
            
            # Calculate offset from monotonic time to UTC epoch
            utc_ns = int(utc_time.timestamp() * 1_000_000_000)
            self._boot_time_offset = utc_ns - monotonic_ns
            self._last_monotonic_sync = time.time()
            
            self.logger.debug(f"⏱️ Monotonic time synchronized: offset = {self._boot_time_offset/1e9:.6f}s")
            
        except Exception as e:
            self.logger.warning(f"Failed to sync monotonic time: {e}")
    
    def _get_precise_capture_timestamp(self) -> datetime:
        """
        Get nanosecond-precise timestamp using GPS PPS hardware when available.
        
        Priority order:
        1. GPS PPS hardware timestamp (nanosecond precision)
        2. Monotonic clock with GPS sync (microsecond precision)
        3. System time fallback
        
        Returns:
            datetime: UTC timestamp with best available precision
        """
        try:
            # Try GPS PPS hardware timestamp first (nanosecond precision)
            if self.gps:
                pps_timestamp_ns = self.gps.get_hardware_timestamp()
                if pps_timestamp_ns is not None:
                    # PPS timestamp is GPS-synchronized nanosecond UTC time
                    utc_seconds = pps_timestamp_ns / 1_000_000_000
                    return datetime.fromtimestamp(utc_seconds, tz=timezone.utc)
            
            # Resync monotonic time periodically (every 5 minutes) to account for GPS corrections
            if time.time() - self._last_monotonic_sync > 300:  # 5 minutes
                self._sync_monotonic_time()
            
            # Get high-precision monotonic timestamp (microsecond precision)
            monotonic_ns = time.monotonic_ns()
            
            # Convert to UTC using our established offset
            if self._boot_time_offset is not None:
                utc_ns = monotonic_ns + self._boot_time_offset
                utc_seconds = utc_ns / 1_000_000_000
                return datetime.fromtimestamp(utc_seconds, tz=timezone.utc)
            else:
                # Fallback to system time if sync failed
                self.logger.warning("Boot time offset not available, using system time")
                return datetime.now(timezone.utc)
                
        except Exception as e:
            self.logger.warning(f"Precision timestamp failed, using system time: {e}")
            return datetime.now(timezone.utc)
    

    
    def _update_sequence_counter(self, timestamp: datetime) -> None:
        """
        Update image sequence counter, resetting daily for organized numbering.
        
        Args:
            timestamp: Current image timestamp
        """
        current_date = timestamp.date()
        
        # Reset counter if date changed (new day)
        if current_date != self.current_date:
            self.current_date = current_date
            self.image_sequence_counter = 1
            self.logger.info(f"📅 Date changed to {current_date}, resetting image sequence counter to 1")
        else:
            # Increment counter for same day
            self.image_sequence_counter += 1
            self.logger.debug(f"🔢 Incremented sequence counter to: {self.image_sequence_counter}")
            
        # Log periodic sequence info for debugging (every 100 images)
        if self.image_sequence_counter % 100 == 0:
            self.logger.debug(f"📊 Image sequence counter: {self.image_sequence_counter}")
    
    def _check_component_health(self) -> None:
        """Check health of all system components."""
        self.last_health_check = time.time()
        
        # Check camera health
        if self.camera:
            self.component_health['camera'] = self.camera.is_healthy()
        
        # Check GPS health
        if self.gps:
            self.component_health['gps'] = self.gps.is_healthy()
        
        # Check storage health
        if self.storage:
            self.component_health['storage'] = self.storage.is_healthy()
        
        # Check LED health
        if self.led_manager:
            self.component_health['led'] = self.led_manager.is_healthy()
        
        # Update LED status based on health
        self._update_led_status()
        
        # Log health status
        unhealthy_components = [name for name, healthy in self.component_health.items() if not healthy]
        if unhealthy_components:
            self.logger.warning(f"Unhealthy components: {', '.join(unhealthy_components)}")
    
    def _update_led_status(self) -> None:
        """Update LED status indicators."""
        if not self.led_manager:
            return
        
        try:
            # Get GPS status
            has_gps_fix = False
            gps_acquiring = False
            
            if self.gps:
                fix = self.gps.get_current_fix()
                has_gps_fix = fix is not None and fix.is_valid
                # GPS is acquiring if it's connected and running but no valid fix
                gps_acquiring = (self.gps.is_connected and self.gps.is_running and 
                               not has_gps_fix)
            
            # Update GPS LED specifically
            if self.gps and (self.gps.is_connected and self.gps.is_running):
                self.led_manager.set_gps_status(has_gps_fix, acquiring=gps_acquiring)
            else:
                self.led_manager.set_gps_status(False, acquiring=False)
            
            # Update other LED statuses
            self.led_manager.set_camera_status(
                active=self.component_health['camera'],
                error=not self.component_health['camera']
            )
            
            # Update error LED for critical failures
            critical_errors = []
            
            # Storage failure (most critical - can't save images)
            if not self.component_health['storage']:
                critical_errors.append("storage")
            
            # Camera completely failed (can't capture images)
            if self.camera and not self.camera.is_connected:
                critical_errors.append("camera_disconnected")
            
            # GPS hardware failure (if GPS is required)
            if self.require_gps_fix and self.gps and not self.gps.is_connected:
                critical_errors.append("gps_disconnected")
            
            # Too many consecutive capture errors
            if self.consecutive_errors > 5:
                critical_errors.append("capture_failure")
            
            # Low disk space (less than 1GB)
            if self.storage and hasattr(self.storage, 'free_space'):
                if self.storage.free_space < 1.0:  # Less than 1GB
                    critical_errors.append("low_disk_space")
            
            # Check for system temperature issues (if available)
            try:
                import psutil
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if 'cpu_thermal' in temps and temps['cpu_thermal']:
                        cpu_temp = temps['cpu_thermal'][0].current
                        if cpu_temp > 80.0:  # Critical temperature threshold
                            critical_errors.append("high_temperature")
            except (ImportError, Exception):
                pass  # psutil not available or temperature not readable
            
            has_critical_error = len(critical_errors) > 0
            self.led_manager.set_error_condition(has_critical_error, critical=has_critical_error)
            
            # Log critical errors for debugging
            if has_critical_error:
                self.logger.warning(f"Critical errors detected: {', '.join(critical_errors)}")
            
        except Exception as e:
            self.logger.debug(f"LED status update error: {e}")
    
    def _attempt_recovery(self) -> bool:
        """
        Attempt to recover from system errors.
        
        Returns:
            bool: True if recovery successful, False otherwise
        """
        self.logger.info("Attempting system recovery")
        recovery_success = True
        
        # Try to recover camera (non-critical - will retry later)
        if not self.component_health['camera'] and self.camera:
            self.logger.info("Attempting camera recovery")
            if self.camera.reconnect():
                self.component_health['camera'] = True
                self.logger.info("Camera recovery successful")
            else:
                self.logger.warning("Camera recovery failed - will retry during next capture attempt")
                # Don't fail recovery for camera - it will retry during capture
        
        # Try to recover GPS (non-critical if not required)
        if not self.component_health['gps'] and self.gps:
            self.logger.info("Attempting GPS recovery")
            if self.gps.reconnect():
                self.component_health['gps'] = True
                self.logger.info("GPS recovery successful")
            else:
                self.logger.warning("GPS recovery failed")
                # Only fail recovery if GPS is absolutely required
                if self.require_gps_fix:
                    self.logger.error("GPS is required but unavailable")
                    recovery_success = False
                else:
                    self.logger.info("GPS not required - continuing without GPS")
        
        # Check storage (critical component)
        if not self.component_health['storage']:
            self.logger.critical("Storage system unavailable - cannot continue")
            recovery_success = False
        
        return recovery_success
    
    def _status_loop(self) -> None:
        """Status reporting loop (runs in separate thread)."""
        while not self.shutdown_event.is_set():
            try:
                # Generate status report
                status_report = self.get_status()
                self.logger.info(f"Status: {status_report['summary']}")
                
                # Wait for next report interval
                if self.shutdown_event.wait(self.status_report_interval):
                    break
                    
            except Exception as e:
                self.logger.error(f"Status reporting error: {e}")
                time.sleep(5.0)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            dict: System status information
        """
        # Calculate runtime
        runtime = None
        if self.status.start_time:
            runtime = (datetime.now() - self.status.start_time).total_seconds()
        
        # Calculate capture rate
        capture_rate = 0.0
        if runtime and runtime > 0:
            capture_rate = self.status.images_captured / runtime
        
        # Get storage status for summary
        storage_status = "UNKNOWN"
        if self.storage:
            storage_info = self.storage.get_storage_info()
            if storage_info['is_available']:
                # Show storage location and free space
                storage_status = f"OK ({storage_info['free_space_gb']:.1f}GB free)"
            else:
                storage_status = "UNAVAILABLE"
        
        # Build enhanced status summary with storage info
        summary = f"Running: {self.is_running}, Images: {self.status.images_captured}, Rate: {capture_rate:.2f}/s, Storage: {storage_status}"
        
        return {
            'service': self.status.to_dict(),
            'components': {
                'camera': self.camera.get_camera_info() if self.camera else None,
                'gps': self.gps.get_gps_info() if self.gps else None,
                'storage': self.storage.get_storage_info() if self.storage else None,
                'led': self.led_manager.get_status() if self.led_manager else None
            },
            'health': self.component_health.copy(),
            'runtime_seconds': runtime,
            'capture_rate_fps': capture_rate,
            'summary': summary
        }
    
    def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        if self.shutdown_requested:
            return

        self.logger.info("Shutting down BathyImager service")
        self.shutdown_requested = True
        self.shutdown_event.set()
        
        # Update status
        self.status.running = False
        self.is_running = False
        
        # Wait for threads to finish
        if self.main_thread and self.main_thread.is_alive():
            self.logger.info("Waiting for main thread to finish")
            self.main_thread.join(timeout=10.0)
        
        # Cleanup components
        if self.camera:
            self.camera.close()
        
        if self.gps:
            self.gps.disconnect()
        
        if self.led_manager:
            self.led_manager.cleanup()
        
        self.logger.info("BathyImager service shutdown complete")
    
    def run(self) -> int:
        """
        Run the service (blocking call).
        
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        try:
            if not self.start():
                self.logger.error("Failed to start service")
                return 1
            
            # Wait for shutdown signal
            if self.main_thread:
                self.main_thread.join()
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            return 0
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            return 1
        finally:
            self.shutdown()


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    import os
    
    if config_path is None:
        # Look for config in common locations - prioritize local development directory
        possible_paths = [
            '../config/bathyimager_config.json',  # Development: run from src/ directory
            './config/bathyimager_config.json',   # Development: run from root directory  
            '/etc/bathycat/bathyimager_config.json',      # Production system config
            '/usr/local/etc/bathycat/bathyimager_config.json',  # Alternative system config
            # Legacy paths for backward compatibility
            '/etc/bathycat/config.json',
            '/usr/local/etc/bathycat/config.json',
            './config/bathycat_config.json',
            '../config/bathycat_config.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        else:
            raise FileNotFoundError("Configuration file not found")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def main() -> int:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='BathyCat Seabed Imager Service')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--test', '-t', action='store_true', help='Run in test mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--no-leds', action='store_true', help='Disable LED functionality for testing')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Adjust log level if verbose
        if args.verbose:
            config['log_level'] = 'DEBUG'
            
        # Disable LEDs if requested
        if args.no_leds:
            config['leds_enabled'] = False
        
        # Create and run service
        service = BathyCatService(config)
        
        if args.test:
            # Test mode - run briefly then exit
            service.logger.info("Running in test mode")
            if service.initialize():
                service.logger.info("Test initialization successful")
                status = service.get_status()
                print(json.dumps(status, indent=2, default=str))
                return 0
            else:
                service.logger.error("Test initialization failed")
                return 1
        else:
            # Normal operation
            return service.run()
        
    except Exception as e:
        logging.error(f"Service failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())