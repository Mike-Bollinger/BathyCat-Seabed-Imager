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
from datetime import datetime, timedelta
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
            log_file = self.config.get('log_file_path', '/var/log/bathycat/bathycat.log')
            try:
                import os
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                
            except Exception as e:
                logger.warning(f"Could not setup file logging: {e}")
        
        return logger
    
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
                self.logger.info("Storage system ready")
            else:
                self.logger.error("Storage initialization failed")
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
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Check if it's time to capture
                if current_time - last_capture_time >= self.capture_interval:
                    
                    # Perform health checks periodically
                    if current_time - self.last_health_check >= self.health_check_interval:
                        self._check_component_health()
                    
                    # Attempt image capture
                    if self._capture_image():
                        last_capture_time = current_time
                        consecutive_errors = 0
                    else:
                        consecutive_errors += 1
                        self.status.errors_encountered += 1
                        self.status.last_error_time = datetime.now()
                        
                        # Handle excessive errors
                        if consecutive_errors >= max_consecutive_errors:
                            self.logger.error(f"Too many consecutive errors ({consecutive_errors}), attempting recovery")
                            if not self._attempt_recovery():
                                self.logger.critical("Recovery failed, shutting down")
                                break
                            consecutive_errors = 0
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                consecutive_errors += 1
                time.sleep(1.0)  # Brief pause on error
        
        self.logger.info("Main capture loop ended")
    
    def _capture_image(self) -> bool:
        """
        Capture and process a single image.
        
        Returns:
            bool: True if capture successful, False otherwise
        """
        try:
            # Update LED status for capture
            if self.led_manager:
                self.led_manager.set_camera_status(True, capturing=True)
            
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
            
            frame = self.camera.capture_frame()
            if frame is None:
                self.logger.warning("Failed to capture camera frame - will try reconnect next time")
                self.component_health['camera'] = False
                if self.camera:
                    self.camera.is_initialized = False
                return False
            
            # Get GPS fix
            gps_fix = None
            if self.gps:
                gps_fix = self.gps.get_current_fix()
                
                # Check if we require valid GPS fix
                if self.require_gps_fix and (not gps_fix or not gps_fix.is_valid):
                    self.logger.debug("Skipping capture - no valid GPS fix")
                    return False
            
            # Process image with metadata
            timestamp = datetime.now()
            processed_image = self.image_processor.process_frame(frame, gps_fix, timestamp)
            
            # Save to storage
            filepath = self.storage.save_image(processed_image, timestamp)
            if filepath:
                # Update statistics
                self.status.images_captured += 1
                self.status.last_capture_time = timestamp
                
                # Signal successful capture
                if self.led_manager:
                    self.led_manager.signal_capture()
                
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
            # Get GPS fix status
            has_gps_fix = False
            if self.gps:
                fix = self.gps.get_current_fix()
                has_gps_fix = fix is not None and fix.is_valid
            
            # Update all LED statuses
            self.led_manager.update_status(
                camera_healthy=self.component_health['camera'],
                gps_healthy=self.component_health['gps'],
                storage_healthy=self.component_health['storage'],
                has_gps_fix=has_gps_fix
            )
            
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
        
        # Try to recover camera
        if not self.component_health['camera'] and self.camera:
            self.logger.info("Attempting camera recovery")
            if self.camera.reconnect():
                self.component_health['camera'] = True
                self.logger.info("Camera recovery successful")
            else:
                self.logger.warning("Camera recovery failed")
                recovery_success = False
        
        # Try to recover GPS
        if not self.component_health['gps'] and self.gps:
            self.logger.info("Attempting GPS recovery")
            if self.gps.reconnect():
                self.component_health['gps'] = True
                self.logger.info("GPS recovery successful")
            else:
                self.logger.warning("GPS recovery failed")
                if self.require_gps_fix:
                    recovery_success = False
        
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
        
        # Build status summary
        summary = f"Running: {self.is_running}, Images: {self.status.images_captured}, Rate: {capture_rate:.2f}/s"
        
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
        
        self.logger.info("Shutting down BathyCat service")
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
        
        self.logger.info("BathyCat service shutdown complete")
    
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
        # Look for config in common locations
        possible_paths = [
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