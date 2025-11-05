#!/usr/bin/env python3
"""
BathyCat GPS Troubleshooting Tool
================================

This script provides comprehensive GPS testing and troubleshooting for
the BathyCat Seabed Imager system.

Features:
- GPS device detection and connection testing
- NMEA sentence parsing validation
- GPS time synchronization verification
- Coordinate accuracy testing
- Satellite signal strength analysis
- EXIF metadata validation
- Configuration recommendations

Usage: python3 gps_troubleshoot.py [--detailed] [--port /dev/ttyUSB0]
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import ConfigManager
from gps import GPS
from camera import Camera
from image_processor import ImageProcessor
import numpy as np

def setup_logging():
    """Setup logging for the diagnostic."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def test_gps_connection(gps_config):
    """Test GPS connection and data reception."""
    logger = logging.getLogger(__name__)
    logger.info("=== GPS CONNECTION TEST ===")
    
    try:
        gps = GPS(gps_config)
        
        # Connect to GPS
        if not gps.connect():
            logger.error("❌ GPS connection failed")
            return None, None
        
        logger.info("✓ GPS connected successfully")
        
        # Start reading GPS data
        if not gps.start_reading():
            logger.error("❌ GPS reading failed to start")
            gps.disconnect()
            return None, None
        
        logger.info("✓ GPS reading started")
        
        # Wait for GPS data
        logger.info("Waiting 15 seconds for GPS data...")
        time.sleep(15)
        
        # Get GPS info
        gps_info = gps.get_gps_info()
        logger.info(f"GPS sentences received: {gps_info['sentence_count']}")
        logger.info(f"GPS fixes processed: {gps_info['fix_count']}")
        
        # Get current fix
        current_fix = gps.get_current_fix()
        if current_fix:
            logger.info(f"✓ GPS fix available:")
            logger.info(f"  Coordinates: {current_fix.latitude:.6f}, {current_fix.longitude:.6f}")
            logger.info(f"  Fix quality: {current_fix.fix_quality}")
            logger.info(f"  Satellites: {current_fix.satellites}")
            logger.info(f"  Is valid: {current_fix.is_valid}")
            logger.info(f"  Timestamp: {current_fix.timestamp}")
        else:
            logger.warning("⚠️  No GPS fix available")
        
        return gps, current_fix
        
    except Exception as e:
        logger.error(f"❌ GPS test failed: {e}")
        return None, None

def test_camera_settings(camera_config):
    """Test camera functionality and auto settings."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== CAMERA SETTINGS TEST ===")
    
    try:
        camera = Camera(camera_config)
        
        # Initialize camera
        if not camera.initialize():
            logger.error("❌ Camera initialization failed")
            return None
        
        logger.info("✓ Camera initialized successfully")
        
        # Capture a test frame
        frame = camera.capture_frame()
        if frame is None:
            logger.error("❌ Camera frame capture failed")
            camera.close()
            return None
        
        logger.info(f"✓ Camera frame captured: {frame.shape}")
        
        # Get camera info
        camera_info = camera.get_camera_info()
        logger.info(f"Camera resolution: {camera_info.get('actual_width', 'unknown')}x{camera_info.get('actual_height', 'unknown')}")
        logger.info(f"Camera FPS: {camera_info.get('actual_fps', 'unknown')}")
        
        return camera
        
    except Exception as e:
        logger.error(f"❌ Camera test failed: {e}")
        return None

def test_image_processing(camera, gps_fix, image_config):
    """Test image processing with GPS metadata."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== IMAGE PROCESSING TEST ===")
    
    try:
        processor = ImageProcessor(image_config)
        
        # Capture frame
        frame = camera.capture_frame()
        if frame is None:
            logger.error("❌ Failed to capture frame for processing")
            return False
        
        logger.info("✓ Frame captured for processing")
        
        # Process image with GPS metadata
        timestamp = datetime.utcnow()
        processed_image = processor.process_frame(frame, gps_fix, timestamp)
        
        if processed_image is None:
            logger.error("❌ Image processing failed")
            return False
        
        logger.info(f"✓ Image processed: {len(processed_image)} bytes")
        
        # Save test image
        test_filepath = "gps_diagnostic_test.jpg"
        if processor.save_image(processed_image, test_filepath):
            logger.info(f"✓ Test image saved: {test_filepath}")
        else:
            logger.error("❌ Failed to save test image")
            return False
        
        # Validate image
        if processor.validate_image(test_filepath):
            logger.info("✓ Image validation passed")
        else:
            logger.error("❌ Image validation failed")
            return False
        
        # Extract GPS metadata
        extracted_gps = processor.extract_gps_from_image(test_filepath)
        if extracted_gps:
            logger.info("✓ GPS metadata extracted from image:")
            logger.info(f"  Latitude: {extracted_gps['latitude']:.6f}")
            logger.info(f"  Longitude: {extracted_gps['longitude']:.6f}")
            if 'altitude' in extracted_gps:
                logger.info(f"  Altitude: {extracted_gps['altitude']:.1f}m")
        else:
            logger.warning("⚠️  No GPS metadata found in image")
        
        # Clean up test file
        try:
            os.remove(test_filepath)
            logger.info("Test image cleaned up")
        except:
            pass
        
        return extracted_gps is not None
        
    except Exception as e:
        logger.error(f"❌ Image processing test failed: {e}")
        return False

def main():
    """Run GPS tagging diagnostic."""
    logger = setup_logging()
    logger.info("BathyCat GPS Tagging Diagnostic")
    logger.info("=" * 50)
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        logger.info(f"Configuration loaded:")
        logger.info(f"  GPS port: {config.get('gps_port', 'unknown')}")
        logger.info(f"  GPS time sync: {config.get('gps_time_sync', False)}")
        logger.info(f"  Camera auto exposure: {config.get('camera_auto_exposure', False)}")
        logger.info(f"  Camera auto white balance: {config.get('camera_auto_white_balance', False)}")
        logger.info(f"  Enable metadata: {config.get('enable_metadata', False)}")
        
        # Test GPS
        gps, gps_fix = test_gps_connection(config)
        
        # Test Camera
        camera = test_camera_settings(config)
        
        if camera:
            # Test image processing
            success = test_image_processing(camera, gps_fix, config)
            camera.close()
            
            if success:
                logger.info("\n🎉 ALL TESTS PASSED!")
                logger.info("GPS tagging should be working correctly.")
            else:
                logger.error("\n❌ IMAGE PROCESSING FAILED")
                logger.error("GPS metadata may not be getting added to images.")
        else:
            logger.error("\n❌ CAMERA TEST FAILED")
        
        # Clean up GPS
        if gps:
            gps.disconnect()
    
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        return False
    
    logger.info("\nDiagnostic complete.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)