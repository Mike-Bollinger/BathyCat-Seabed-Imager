#!/usr/bin/env python3
"""
BathyCat Seabed Imager - Main Application
=========================================

Main application for controlling the underwater imaging system.
Coordinates camera capture, GPS tagging, and data storage.

Author: Mike Bollinger
Date: August 2025
"""

import asyncio
import logging
import logging.config
import signal
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from camera_controller import CameraController
from gps_controller import GPSController
from image_processor import ImageProcessor
from storage_manager import StorageManager
from config import Config


class BathyCatImager:
    """Main application class for the BathyCat Seabed Imager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the imaging system."""
        self.config = Config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize components
        self.camera = CameraController(self.config)
        self.gps = GPSController(self.config)
        self.processor = ImageProcessor(self.config)
        self.storage = StorageManager(self.config)
        
        # Control flags
        self.running = False
        self.capture_active = False
        
        # Statistics
        self.stats = {
            'images_captured': 0,
            'start_time': None,
            'last_gps_fix': None,
            'errors': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.config.dictConfig(self.config.logging_config)
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize all system components."""
        self.logger.info("Initializing BathyCat Seabed Imager...")
        
        try:
            # Initialize storage
            if not await self.storage.initialize():
                self.logger.error("Failed to initialize storage")
                return False
            
            # Initialize GPS
            if not await self.gps.initialize():
                self.logger.error("Failed to initialize GPS")
                return False
            
            # Initialize camera
            if not await self.camera.initialize():
                self.logger.error("Failed to initialize camera")
                return False
            
            # Wait for GPS fix if required
            if self.config.require_gps_fix:
                self.logger.info("Waiting for GPS fix...")
                if not await self.gps.wait_for_fix(timeout=self.config.gps_fix_timeout):
                    self.logger.error("Failed to acquire GPS fix within timeout")
                    return False
            
            self.logger.info("System initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    async def start_capture(self):
        """Start the image capture process."""
        self.logger.info("Starting image capture...")
        self.capture_active = True
        self.stats['start_time'] = datetime.now()
        
        # Create capture tasks
        tasks = [
            asyncio.create_task(self._capture_loop()),
            asyncio.create_task(self._gps_update_loop()),
            asyncio.create_task(self._status_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Capture tasks cancelled")
        except Exception as e:
            self.logger.error(f"Error in capture process: {e}")
            self.stats['errors'] += 1
    
    async def _capture_loop(self):
        """Main image capture loop."""
        frame_interval = 1.0 / self.config.capture_fps
        next_capture = time.time()
        
        self.logger.debug(f"Starting capture loop with {self.config.capture_fps} FPS")
        
        while self.running and self.capture_active:
            try:
                current_time = time.time()
                
                if current_time >= next_capture:
                    self.logger.error("📷 STEP_1: Starting image capture sequence")
                    
                    # Step 1: Capture image with individual error handling
                    try:
                        self.logger.error("📷 STEP_1A: About to call camera.capture_image()")
                        image_data = self.camera.capture_image()
                        self.logger.error(f"📷 STEP_1B: Camera returned: {type(image_data)}")
                    except Exception as cam_error:
                        self.logger.error(f"🚨 CAMERA_ERROR: {cam_error}")
                        raise cam_error
                    
                    # Step 2: Check image data with individual error handling
                    try:
                        self.logger.error("📷 STEP_2A: About to check image_data is not None")
                        is_valid = (image_data is not None)
                        self.logger.error(f"📷 STEP_2B: Image validation result: {is_valid}")
                    except Exception as check_error:
                        self.logger.error(f"🚨 IMAGE_CHECK_ERROR: {check_error}")
                        raise check_error
                    
                    if image_data is not None:
                        try:
                            self.logger.error(f"📷 STEP_3: Image OK, shape: {getattr(image_data, 'shape', 'NO_SHAPE')}")
                        except Exception as shape_error:
                            self.logger.error(f"🚨 SHAPE_ERROR: {shape_error}")
                            raise shape_error
                        
                        # Step 3: Get GPS data with individual error handling
                        try:
                            self.logger.error("🛰️ STEP_4A: About to get GPS position")
                            gps_data = self.gps.get_current_position()
                            self.logger.error(f"🛰️ STEP_4B: GPS data type: {type(gps_data)}")
                        except Exception as gps_error:
                            self.logger.error(f"🚨 GPS_ERROR: {gps_error}")
                            raise gps_error
                        
                        # Step 4: Process image with individual error handling
                        try:
                            self.logger.error("💾 STEP_5A: About to process image")
                            await self.processor.process_image(
                                image_data, gps_data, current_time
                            )
                            self.logger.error("💾 STEP_5B: Image processing complete")
                        except Exception as process_error:
                            self.logger.error(f"🚨 PROCESSING_ERROR: {process_error}")
                            import traceback
                            self.logger.error(f"🔍 PROCESSING_TRACEBACK: {traceback.format_exc()}")
                            raise process_error
                        
                        self.stats['images_captured'] += 1
                        
                        # Update next capture time
                        next_capture += frame_interval
                        
                        # Prevent drift by checking if we're behind
                        if next_capture < current_time:
                            next_capture = current_time + frame_interval
                    
                    else:
                        self.logger.error("📷 STEP_X: Camera returned None")
                        self.stats['errors'] += 1
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"🚨 CAPTURE_LOOP_ERROR: {e}")
                import traceback
                tb_str = traceback.format_exc()
                self.logger.error(f"🔍 CAPTURE_LOOP_TRACEBACK: {tb_str}")
                
                # Enhanced error analysis
                tb_lines = tb_str.split('\n')
                for i, line in enumerate(tb_lines):
                    if any(keyword in line for keyword in ['camera_controller', 'gps_controller', 'image_processor', 'bathycat_imager']):
                        self.logger.error(f"🎯 PROBLEM_FILE_LINE_{i}: {line.strip()}")
                    if 'truth value' in line.lower() or 'ambiguous' in line.lower():
                        self.logger.error(f"🔥 NUMPY_ERROR_LINE_{i}: {line.strip()}")
                
                self.stats['errors'] += 1
                await asyncio.sleep(0.1)
    
    async def _gps_update_loop(self):
        """GPS data update loop."""
        while self.running and self.capture_active:
            try:
                if await self.gps.update():
                    self.stats['last_gps_fix'] = datetime.now()
                
                await asyncio.sleep(1.0)  # Update GPS every second
                
            except Exception as e:
                self.logger.error(f"Error in GPS update loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _status_loop(self):
        """Status reporting loop."""
        while self.running and self.capture_active:
            try:
                await asyncio.sleep(30.0)  # Report every 30 seconds
                self._log_status()
                
            except Exception as e:
                self.logger.error(f"Error in status loop: {e}")
                await asyncio.sleep(30.0)
    
    def _log_status(self):
        """Log current system status."""
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        fps = self.stats['images_captured'] / uptime if uptime > 0 else 0
        
        gps_status = "GPS Fix" if self.gps.has_fix() else "No GPS"
        storage_free = self.storage.get_free_space_gb()
        
        self.logger.info(
            f"Status: {self.stats['images_captured']} images, "
            f"{fps:.1f} FPS, {gps_status}, "
            f"{storage_free:.1f}GB free, {self.stats['errors']} errors"
        )
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        self.logger.info("Shutting down BathyCat Imager...")
        
        self.capture_active = False
        
        # Shutdown components
        await self.camera.shutdown()
        await self.gps.shutdown()
        await self.processor.shutdown()
        await self.storage.shutdown()
        
        # Log final statistics
        if self.stats['start_time']:
            total_time = (datetime.now() - self.stats['start_time']).total_seconds()
            avg_fps = self.stats['images_captured'] / total_time if total_time > 0 else 0
            
            self.logger.info(
                f"Session complete: {self.stats['images_captured']} images "
                f"in {total_time:.1f}s (avg {avg_fps:.1f} FPS), "
                f"{self.stats['errors']} errors"
            )
        
        self.logger.info("Shutdown complete")
    
    async def run(self):
        """Main run method."""
        self.running = True
        
        try:
            if await self.initialize():
                await self.start_capture()
            else:
                self.logger.error("System initialization failed")
                return False
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        
        finally:
            await self.shutdown()
        
        return True


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="BathyCat Seabed Imager")
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
        default="/etc/bathycat/config.json"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    # Create and run the imager
    imager = BathyCatImager(args.config)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success = await imager.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
