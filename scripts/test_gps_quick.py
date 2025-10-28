#!/usr/bin/env python3
"""
Quick GPS Time Sync Test
========================

Test the integrated GPS time sync functionality.
"""

import sys
import time
import logging
from datetime import datetime

# Add src directory to path
sys.path.insert(0, '/home/bathyimager/BathyCat-Seabed-Imager/src')

try:
    from gps import GPS
    from config import Config
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    print("🧪 GPS Time Sync Test Starting...")
    print(f"📅 Current system time: {datetime.now()}")
    
    # Load config
    config = Config('/home/bathyimager/BathyCat-Seabed-Imager/config/bathycat_config.json')
    
    # Create GPS instance
    logger.info("Creating GPS instance...")
    gps = GPS(config.get_config())
    
    # Connect to GPS
    logger.info("Connecting to GPS...")
    if not gps.connect():
        logger.error("❌ Failed to connect to GPS")
        sys.exit(1)
    
    logger.info("✅ GPS connected successfully")
    
    # Start GPS reading
    logger.info("Starting GPS reading...")
    if not gps.start_reading():
        logger.error("❌ Failed to start GPS reading")
        sys.exit(1)
    
    logger.info("✅ GPS reading started")
    
    # Wait for GPS fix and time sync
    logger.info("🛰️  Waiting for GPS fix and time sync...")
    logger.info("⏱️  This should complete in under 30 seconds...")
    
    start_time = time.time()
    timeout = 60  # 1 minute timeout
    
    while time.time() - start_time < timeout:
        current_fix = gps.get_current_fix()
        
        if current_fix and current_fix.is_valid:
            elapsed = time.time() - start_time
            
            logger.info(f"🛰️  GPS FIX: {current_fix.latitude:.6f}, {current_fix.longitude:.6f}")
            logger.info(f"📊 Quality: {current_fix.fix_quality}, Satellites: {current_fix.satellites}")
            logger.info(f"⏱️  Time to fix: {elapsed:.1f} seconds")
            
            if hasattr(gps, 'system_time_synced') and gps.system_time_synced:
                logger.info("🕐 GPS TIME SYNC: ✅ SUCCESS")
                logger.info(f"📅 New system time: {datetime.now()}")
                break
            else:
                logger.info("🕐 GPS TIME SYNC: ⏳ Waiting...")
        
        time.sleep(1)
    
    else:
        logger.warning("⏰ Timeout waiting for GPS fix")
    
    # Show final status
    logger.info("\n📋 FINAL STATUS:")
    logger.info(f"GPS Fix: {'✅ Valid' if current_fix and current_fix.is_valid else '❌ Invalid'}")
    logger.info(f"Time Sync: {'✅ Synced' if hasattr(gps, 'system_time_synced') and gps.system_time_synced else '❌ Not Synced'}")
    logger.info(f"System Time: {datetime.now()}")
    
    # Cleanup
    gps.stop_reading()
    gps.disconnect()
    
    logger.info("🧪 GPS Time Sync Test Complete")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("Make sure you're running this from the correct directory")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Test error: {e}")
    sys.exit(1)