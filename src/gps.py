#!/usr/bin/env python3
"""
GPS Module for BathyCat Seabed Imager
====================================

Handles NMEA GPS parsing using pynmea2 with serial communication,
fix validation, and time synchronization.

Features:
- Serial GPS connection management
- NMEA sentence parsing and validation
- GPS fix quality monitoring
- Time synchronization capability
- Location coordinate validation
- GPS health monitoring
"""

import serial
import pynmea2
import logging
import time
import threading
from typing import Optional, Dict, Any, Tuple, NamedTuple
from datetime import datetime
from dataclasses import dataclass


class GPSError(Exception):
    """Custom exception for GPS-related errors."""
    pass


@dataclass
class GPSFix:
    """GPS fix data structure."""
    latitude: float
    longitude: float
    altitude: Optional[float]
    timestamp: datetime
    fix_quality: int
    satellites: int
    horizontal_dilution: Optional[float]
    fix_mode: str
    
    @property
    def is_valid(self) -> bool:
        """Check if GPS fix is valid."""
        return (
            self.fix_quality > 0 and
            self.satellites >= 3 and
            -90 <= self.latitude <= 90 and
            -180 <= self.longitude <= 180
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'timestamp': self.timestamp.isoformat(),
            'fix_quality': self.fix_quality,
            'satellites': self.satellites,
            'horizontal_dilution': self.horizontal_dilution,
            'fix_mode': self.fix_mode,
            'is_valid': self.is_valid
        }


class GPS:
    """
    GPS interface for BathyCat system.
    
    Provides reliable GPS connection with NMEA parsing and fix validation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GPS with configuration.
        
        Args:
            config: GPS configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_running = False
        
        # GPS settings from config
        self.port = config.get('gps_port', '/dev/ttyUSB0')
        self.baudrate = config.get('gps_baudrate', 9600)
        self.timeout = config.get('gps_timeout', 1.0)
        self.time_sync = config.get('gps_time_sync', True)
        self.require_fix = config.get('require_gps_fix', False)
        self.fix_timeout = config.get('gps_fix_timeout', 300.0)
        
        # GPS state
        self.current_fix: Optional[GPSFix] = None
        self.last_fix_time = 0
        self.fix_count = 0
        self.sentence_count = 0
        
        # Time synchronization state
        self.last_time_sync = 0
        self.time_sync_interval = 1800  # Sync every 30 minutes after first sync
        self.first_fix_received = False
        self.system_time_synced = False
        
        # Threading for continuous GPS reading
        self.read_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def connect(self) -> bool:
        """
        Connect to GPS device.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to GPS on {self.port} at {self.baudrate} baud")
            
            # Open serial connection
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            if not self.serial_conn.is_open:
                raise GPSError(f"Failed to open GPS port {self.port}")
            
            self.is_connected = True
            self.logger.info("GPS connection established")
            return True
            
        except Exception as e:
            self.logger.error(f"GPS connection failed: {e}")
            self._cleanup()
            return False
    
    def start_reading(self) -> bool:
        """
        Start continuous GPS reading in background thread.
        
        Returns:
            bool: True if reading started successfully, False otherwise
        """
        if not self.is_connected:
            self.logger.error("GPS not connected")
            return False
        
        if self.is_running:
            self.logger.warning("GPS reading already running")
            return True
        
        try:
            self.stop_event.clear()
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            self.is_running = True
            
            self.logger.info("GPS reading started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start GPS reading: {e}")
            return False
    
    def stop_reading(self) -> None:
        """Stop continuous GPS reading."""
        if self.is_running:
            self.logger.info("Stopping GPS reading")
            self.stop_event.set()
            
            if self.read_thread:
                self.read_thread.join(timeout=5.0)
                
            self.is_running = False
            self.logger.info("GPS reading stopped")
    
    def _read_loop(self) -> None:
        """Main GPS reading loop (runs in background thread)."""
        self.logger.info("GPS reading loop started")
        
        while not self.stop_event.is_set():
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    break
                
                # Read line from GPS
                line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                
                if line:
                    self._process_nmea_sentence(line)
                    
            except Exception as e:
                self.logger.error(f"Error in GPS reading loop: {e}")
                time.sleep(1.0)  # Brief pause on error
        
        self.logger.info("GPS reading loop ended")
    
    def _process_nmea_sentence(self, sentence: str) -> None:
        """
        Process a single NMEA sentence.
        
        Args:
            sentence: NMEA sentence string
        """
        try:
            # Parse NMEA sentence
            parsed = pynmea2.parse(sentence)
            self.sentence_count += 1
            
            # Log raw sentence for debugging (every 100th sentence)
            if self.sentence_count % 100 == 0:
                self.logger.debug(f"Processed {self.sentence_count} NMEA sentences")
            
            # Process different sentence types
            if isinstance(parsed, pynmea2.GGA):
                # Global Positioning System Fix Data
                self._process_gga(parsed)
            elif isinstance(parsed, pynmea2.RMC):
                # Recommended Minimum Course
                self._process_rmc(parsed)
            elif isinstance(parsed, pynmea2.GSA):
                # GPS DOP and active satellites
                self._process_gsa(parsed)
                
        except Exception as e:
            # Don't log every parse error as it's common with incomplete sentences
            if self.sentence_count % 1000 == 0:
                self.logger.debug(f"NMEA parse error (showing every 1000th): {e}")
    
    def _process_gga(self, gga: pynmea2.GGA) -> None:
        """Process GGA (Fix Data) sentence."""
        if gga.latitude and gga.longitude and gga.gps_qual:
            try:
                # Convert to decimal degrees
                lat = float(gga.latitude)
                lon = float(gga.longitude)
                
                if gga.lat_dir == 'S':
                    lat = -lat
                if gga.lon_dir == 'W':
                    lon = -lon
                
                # Create GPS fix
                fix = GPSFix(
                    latitude=lat,
                    longitude=lon,
                    altitude=float(gga.altitude) if gga.altitude else None,
                    timestamp=datetime.utcnow(),
                    fix_quality=int(gga.gps_qual),
                    satellites=int(gga.num_sats) if gga.num_sats else 0,
                    horizontal_dilution=float(gga.horizontal_dil) if gga.horizontal_dil else None,
                    fix_mode='3D' if gga.gps_qual in [1, 2] else 'NO_FIX'
                )
                
                # Always store GPS data if we have coordinates, even if not strictly "valid"
                # This allows for GPS tagging even with partial fixes
                if lat != 0 or lon != 0:  # Have some coordinate data
                    self.current_fix = fix
                    self.last_fix_time = time.time()
                    self.fix_count += 1
                    
                    # Log GPS status with more detail
                    if fix.is_valid:
                        self.logger.info(f"🛰️  GPS FIX ACQUIRED: {lat:.6f}, {lon:.6f}, quality:{fix.fix_quality}, sats:{fix.satellites}")
                        
                        # Trigger time sync on first valid fix
                        if not self.first_fix_received and self.time_sync:
                            self.logger.info("🕐 First GPS fix acquired - triggering time synchronization")
                    else:
                        self.logger.debug(f"GPS fix PARTIAL: {lat:.6f}, {lon:.6f}, quality:{fix.fix_quality}, sats:{fix.satellites} (will still geotag images)")
                else:
                    self.logger.debug(f"GPS fix with zero coordinates - quality:{fix.fix_quality}, sats:{fix.satellites or 0}")
                
            except (ValueError, TypeError) as e:
                self.logger.debug(f"Error processing GGA data: {e}")
    
    def _process_rmc(self, rmc: pynmea2.RMC) -> None:
        """Process RMC (Recommended Minimum Course) sentence."""
        # RMC also contains position data and can be used for time sync
        if self.time_sync and rmc.datestamp and rmc.timestamp:
            try:
                gps_datetime = datetime.combine(rmc.datestamp, rmc.timestamp)
                self.logger.debug(f"GPS time: {gps_datetime}")
                
                # Perform system time synchronization if needed
                self._sync_system_time(gps_datetime)
                
            except Exception as e:
                self.logger.debug(f"Error processing RMC time: {e}")
    
    def _process_gsa(self, gsa: pynmea2.GSA) -> None:
        """Process GSA (GPS DOP and active satellites) sentence."""
        # GSA provides additional fix quality information
        if hasattr(gsa, 'mode_fix_type') and self.current_fix:
            mode_map = {'1': 'NO_FIX', '2': '2D', '3': '3D'}
            fix_mode = mode_map.get(str(gsa.mode_fix_type), 'UNKNOWN')
            self.current_fix.fix_mode = fix_mode
    
    def _ensure_utc_timezone(self) -> None:
        """Ensure system timezone is set to UTC."""
        try:
            import subprocess
            result = subprocess.run(['timedatectl', 'set-timezone', 'UTC'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.debug("System timezone confirmed as UTC")
            else:
                self.logger.warning(f"Could not set UTC timezone: {result.stderr}")
        except Exception as e:
            self.logger.debug(f"Timezone setting unavailable: {e}")
    
    def _sync_system_time(self, gps_datetime: datetime) -> None:
        """
        Synchronize system time with GPS time.
        
        Args:
            gps_datetime: GPS datetime (UTC)
        """
        try:
            current_time = time.time()
            
            # Ensure UTC timezone
            self._ensure_utc_timezone()
            
            # Always sync on first GPS fix, then respect interval
            should_sync = (
                not self.first_fix_received or  # First fix - always sync
                (current_time - self.last_time_sync) >= self.time_sync_interval  # Periodic sync
            )
            
            if not should_sync:
                return
            
            # Convert GPS time to UTC timestamp
            gps_utc = gps_datetime.replace(tzinfo=None)  # GPS time is already UTC
            gps_timestamp = gps_utc.timestamp()
            
            # Get current system time
            system_timestamp = time.time()
            time_diff = abs(gps_timestamp - system_timestamp)
            
            # Sync if first fix OR significant difference (> 1 second)
            should_set_time = not self.first_fix_received or time_diff > 1.0
            
            if should_set_time:
                try:
                    # Import subprocess only when needed
                    import subprocess
                    import os
                    
                    # Use helper script for time setting (requires sudo)
                    time_str = gps_utc.strftime("%Y-%m-%d %H:%M:%S")
                    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'gps_set_time.sh')
                    
                    if os.path.exists(script_path):
                        result = subprocess.run(['sudo', script_path, time_str], 
                                              capture_output=True, text=True, timeout=15)
                        
                        if result.returncode == 0:
                            self.logger.info(f"🕐 GPS TIME SYNC SUCCESS: System time set to {gps_utc} UTC (diff: {time_diff:.1f}s)")
                            self.system_time_synced = True
                            self.first_fix_received = True
                        else:
                            self.logger.error(f"🕐 GPS TIME SYNC FAILED: {result.stderr}")
                    else:
                        self.logger.warning(f"GPS time sync helper script not found: {script_path}")
                        
                except subprocess.TimeoutExpired:
                    self.logger.warning("GPS time sync command timed out")
                except FileNotFoundError:
                    self.logger.warning("GPS time sync helper script not available")
                except Exception as e:
                    self.logger.warning(f"Could not sync system time: {e}")
                else:
                    self.logger.info(f"🕐 GPS TIME CHECK: System time already accurate (diff: {time_diff:.1f}s)")
                    if not self.first_fix_received:
                        self.system_time_synced = True
                        self.first_fix_received = True            
                        self.last_time_sync = current_time
            
        except Exception as e:
            self.logger.warning(f"Error in time synchronization: {e}")
    
    def get_current_fix(self) -> Optional[GPSFix]:
        """
        Get current GPS fix.
        
        Returns:
            GPSFix: Current GPS fix, or None if no fix available
        """
        return self.current_fix
    
    def wait_for_fix(self, timeout: Optional[float] = None) -> Optional[GPSFix]:
        """
        Wait for a valid GPS fix.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            GPSFix: Valid GPS fix, or None if timeout reached
        """
        if timeout is None:
            timeout = self.fix_timeout
        
        self.logger.info(f"Waiting for GPS fix (timeout: {timeout}s)")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            fix = self.get_current_fix()
            if fix and fix.is_valid:
                self.logger.info(f"GPS fix acquired in {time.time() - start_time:.1f}s")
                return fix
            
            time.sleep(0.5)
        
        self.logger.warning(f"GPS fix timeout after {timeout}s")
        return None
    
    def get_gps_info(self) -> Dict[str, Any]:
        """
        Get GPS information and status.
        
        Returns:
            dict: GPS information dictionary
        """
        info = {
            'port': self.port,
            'baudrate': self.baudrate,
            'connected': self.is_connected,
            'reading': self.is_running,
            'sentence_count': self.sentence_count,
            'fix_count': self.fix_count,
            'last_fix_time': self.last_fix_time,
            'require_fix': self.require_fix,
            'time_sync_enabled': self.time_sync,
            'system_time_synced': self.system_time_synced,
            'last_time_sync': self.last_time_sync,
            'current_fix': self.current_fix.to_dict() if self.current_fix else None
        }
        
        return info
    
    def is_healthy(self) -> bool:
        """
        Check GPS health status.
        
        Returns:
            bool: True if GPS is healthy, False otherwise
        """
        if not self.is_connected or not self.is_running:
            return False
        
        # Check if we've received data recently
        if time.time() - self.last_fix_time > 30.0:  # No data for 30 seconds
            return False
        
        # If we require fix, check fix validity
        if self.require_fix:
            return self.current_fix is not None and self.current_fix.is_valid
        
        return True
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect GPS.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        self.logger.info("Attempting GPS reconnection")
        self.disconnect()
        
        if self.connect():
            return self.start_reading()
        return False
    
    def _cleanup(self) -> None:
        """Clean up GPS resources."""
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
        self.is_connected = False
    
    def disconnect(self) -> None:
        """Disconnect from GPS and clean up resources."""
        self.logger.info("Disconnecting GPS")
        self.stop_reading()
        self._cleanup()


def test_gps(config: Dict[str, Any]) -> bool:
    """
    Test GPS functionality with given configuration.
    
    Args:
        config: GPS configuration dictionary
        
    Returns:
        bool: True if GPS test passed, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        gps = GPS(config)
        
        if not gps.connect():
            logger.error("GPS connection failed")
            return False
        
        if not gps.start_reading():
            logger.error("GPS reading failed to start")
            return False
        
        # Wait for some GPS data
        logger.info("Reading GPS data for 10 seconds...")
        time.sleep(10)
        
        # Get GPS info
        info = gps.get_gps_info()
        logger.info(f"GPS info: {info}")
        
        # Test health check
        health = gps.is_healthy()
        logger.info(f"GPS health: {health}")
        
        # Test fix acquisition (short timeout for testing)
        fix = gps.wait_for_fix(timeout=5.0)
        if fix:
            logger.info(f"GPS fix: {fix.to_dict()}")
        else:
            logger.info("No GPS fix acquired (normal indoors)")
        
        gps.disconnect()
        logger.info("GPS test completed")
        return True
        
    except Exception as e:
        logger.error(f"GPS test failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'gps_port': '/dev/ttyUSB0',
        'gps_baudrate': 9600,
        'gps_timeout': 1.0,
        'gps_time_sync': True,
        'require_gps_fix': False,
        'gps_fix_timeout': 30.0
    }
    
    success = test_gps(test_config)
    exit(0 if success else 1)