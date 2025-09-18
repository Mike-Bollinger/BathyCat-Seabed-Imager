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
                    self.logger.debug("Attempting image capture...")
                    
                    # Capture image
                    image_data = self.camera.capture_image()
                    self.logger.debug(f"Capture result type: {type(image_data)}")
                    
                    # Fix: Use 'is not None' instead of truthiness check for NumPy arrays
                    if image_data is not None:
                        self.logger.debug(f"Image captured successfully: {image_data.shape}")
                        
                        # Get current GPS data
                        gps_data = self.gps.get_current_position()
                        self.logger.debug(f"GPS data retrieved: {type(gps_data)}")
                        
                        # Process and save image
                        self.logger.debug("Processing image...")
                        await self.processor.process_image(
                            image_data, gps_data, current_time
                        )
                        self.logger.debug("Image processing complete")
                        
                        self.stats['images_captured'] += 1
                        
                        # Update next capture time
                        next_capture += frame_interval
                        
                        # Prevent drift by checking if we're behind
                        if next_capture < current_time:
                            next_capture = current_time + frame_interval
                    
                    else:
                        self.logger.warning("Failed to capture image - camera returned None")
                        self.stats['errors'] += 1
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                import traceback
                self.logger.debug(f"Capture loop traceback: {traceback.format_exc()}")
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
