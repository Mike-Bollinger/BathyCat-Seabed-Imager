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
import traceback
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
        self.camera = CameraController(self.config, self.logger)
        self.gps = GPSController(self.config, self.logger)
        self.processor = ImageProcessor(self.config, self.logger)
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
        try:
            logging.config.dictConfig(self.config.logging_config)
        except Exception:
            # Fallback to basic logging if config fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize all system components."""
        self.logger.info("Initializing BathyCat Seabed Imager...")
        
        try:
            # Initialize storage first
            self.logger.info("🔄 Initializing storage manager...")
            if not await self.storage.initialize():
                self.logger.error("❌ Failed to initialize storage")
                return False
            self.logger.info("✅ Storage manager initialized successfully")
            
            # Initialize GPS
            self.logger.info("🔄 Initializing GPS controller...")
            if not await self.gps.initialize():
                self.logger.error("❌ Failed to initialize GPS")
                return False
            self.logger.info("✅ GPS controller initialized successfully")
            
            # Initialize camera
            self.logger.info("🔄 Initializing camera controller...")
            if not await self.camera.initialize():
                self.logger.error("❌ Failed to initialize camera")
                return False
            self.logger.info("✅ Camera controller initialized successfully")
            
            # Wait for GPS fix if required
            if getattr(self.config, 'require_gps_fix', False):
                self.logger.info("🔄 Waiting for GPS fix...")
                timeout = getattr(self.config, 'gps_fix_timeout', 60)
                if not await self.gps.wait_for_fix(timeout=timeout):
                    self.logger.error("❌ Failed to acquire GPS fix within timeout")
                    return False
                self.logger.info("✅ GPS fix acquired successfully")
            
            self.logger.info("🎉 System initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            self.logger.error(f"Initialization traceback: {traceback.format_exc()}")
            return False
    
    async def start_capture(self):
        """Start the image capture process."""
        self.logger.info("🚀 Starting image capture...")
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
            self.logger.error(f"❌ Error in capture process: {e}")
            self.logger.error(f"Capture process traceback: {traceback.format_exc()}")
            self.stats['errors'] += 1
    
    async def _capture_loop(self):
        """Main image capture loop."""
        fps = getattr(self.config, 'capture_fps', 1)
        frame_interval = 1.0 / fps
        next_capture = time.time()
        
        self.logger.info(f"📷 Starting capture loop with {fps} FPS")
        
        while self.running and self.capture_active:
            try:
                current_time = time.time()
                
                if current_time >= next_capture:
                    self.logger.debug("� Starting image capture sequence")
                    
                    # Step 1: Capture image
                    try:
                        success, image_data, metadata = await self.camera.capture_image()
                        if not success or image_data is None:
                            self.logger.warning("⚠️  Camera returned no image - retrying")
                            await asyncio.sleep(0.1)
                            continue
                        
                        self.logger.debug(f"✅ Image captured: {image_data.shape}")
                        
                    except Exception as cam_error:
                        self.logger.error(f"❌ Camera capture error: {cam_error}")
                        self.stats['errors'] += 1
                        await asyncio.sleep(0.5)  # Wait before retry
                        continue
                    
                    # Step 2: Get GPS data
                    try:
                        gps_data = await self.gps.get_current_position()
                        if gps_data:
                            self.stats['last_gps_fix'] = datetime.now()
                        self.logger.debug(f"🛰️  GPS data: {'✅' if gps_data else '❌'}")
                        
                    except Exception as gps_error:
                        self.logger.error(f"❌ GPS data error: {gps_error}")
                        gps_data = None  # Continue without GPS data
                    
                    # Step 3: Process and save image
                    try:
                        image_path = await self.processor.process_image(
                            image_data, gps_data, current_time, metadata
                        )
                        
                        if image_path:
                            self.stats['images_captured'] += 1
                            self.logger.debug(f"� Image saved: {image_path}")
                        else:
                            self.logger.warning("⚠️  Image processing failed - no path returned")
                            self.stats['errors'] += 1
                        
                    except Exception as process_error:
                        self.logger.error(f"❌ Image processing error: {process_error}")
                        self.logger.error(f"Processing traceback: {traceback.format_exc()}")
                        self.stats['errors'] += 1
                    
                    # Schedule next capture
                    next_capture = current_time + frame_interval
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"❌ Capture loop error: {e}")
                self.logger.error(f"Capture loop traceback: {traceback.format_exc()}")
                self.stats['errors'] += 1
                await asyncio.sleep(0.1)
    
    async def _gps_update_loop(self):
        """GPS data update loop."""
        while self.running and self.capture_active:
            try:
                await self.gps.update()
                await asyncio.sleep(1.0)  # Update GPS every second
                
            except Exception as e:
                self.logger.error(f"❌ Error in GPS update loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _status_loop(self):
        """Status reporting loop."""
        while self.running and self.capture_active:
            try:
                await asyncio.sleep(30.0)  # Report every 30 seconds
                self._log_status()
                
            except Exception as e:
                self.logger.error(f"❌ Error in status loop: {e}")
                await asyncio.sleep(30.0)
    
    def _log_status(self):
        """Log current system status."""
        if not self.stats['start_time']:
            return
            
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        fps = self.stats['images_captured'] / uptime if uptime > 0 else 0
        
        try:
            gps_status = "🛰️ GPS Fix" if self.gps.has_fix() else "❌ No GPS"
        except:
            gps_status = "❓ GPS Unknown"
            
        try:
            storage_free = self.storage.get_free_space_gb()
        except:
            storage_free = 0
        
        self.logger.info(
            f"📊 Status: {self.stats['images_captured']} images, "
            f"{fps:.1f} FPS, {gps_status}, "
            f"{storage_free:.1f}GB free, {self.stats['errors']} errors"
        )
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        self.logger.info("🛑 Shutting down BathyCat Imager...")
        
        self.capture_active = False
        
        # Shutdown components
        components = [
            ("Camera", self.camera),
            ("GPS", self.gps), 
            ("Processor", self.processor),
            ("Storage", self.storage)
        ]
        
        for name, component in components:
            try:
                if hasattr(component, 'shutdown'):
                    await component.shutdown()
                    self.logger.info(f"✅ {name} shutdown complete")
            except Exception as e:
                self.logger.error(f"❌ {name} shutdown error: {e}")
        
        # Log final statistics
        if self.stats['start_time']:
            total_time = (datetime.now() - self.stats['start_time']).total_seconds()
            avg_fps = self.stats['images_captured'] / total_time if total_time > 0 else 0
            
            self.logger.info(
                f"📈 Session complete: {self.stats['images_captured']} images "
                f"in {total_time:.1f}s (avg {avg_fps:.1f} FPS), "
                f"{self.stats['errors']} errors"
            )
        
        self.logger.info("✅ Shutdown complete")
    
    async def run(self):
        """Main run method."""
        self.running = True
        
        try:
            if await self.initialize():
                await self.start_capture()
            else:
                self.logger.error("❌ System initialization failed")
                return False
        
        except KeyboardInterrupt:
            self.logger.info("⚠️  Interrupted by user")
        
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
            self.logger.error(f"Unexpected error traceback: {traceback.format_exc()}")
        
        finally:
            await self.shutdown()
        
        return True


async def main():
    """Main entry point."""
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
    
    # Set up basic logging first
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Create and run the imager
    try:
        imager = BathyCatImager(args.config)
        success = await imager.run()
        return 0 if success else 1
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
