#!/usr/bin/env python3
"""
GPS Time Synchronization Service for BathyCat Seabed Imager
===========================================================

This service synchronizes the Raspberry Pi system clock with GPS time.
It can be run at boot or periodically to prevent clock drift.

Features:
- Automatic GPS device detection
- NMEA sentence parsing for time extraction
- Always sets system to UTC time
- Quick sync without boot delay
- Robust error handling and logging
- Can run as one-shot or periodic service

Usage:
  python3 gps_time_sync.py --boot     # One-time boot sync
  python3 gps_time_sync.py --periodic # Periodic sync (called by timer)
"""

import sys
import json
import time
import serial
import logging
import argparse
import subprocess
import pynmea2
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


class GPSTimeSync:
    """GPS Time Synchronization Service"""
    
    def __init__(self, config_path: str = "/home/bathyimager/BathyCat-Seabed-Imager/config/bathycat_config.json"):
        """Initialize GPS time sync service"""
        self.config_path = config_path
        self.logger = self._setup_logging()
        self.config = self._load_config()
        
        # GPS connection settings
        self.gps_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyAMA0']
        self.baudrate = self.config.get('gps_baudrate', 9600)
        self.timeout = 2.0
        self.max_wait_time = 120  # 2 minutes maximum wait for GPS fix (reduced from 5 minutes)
        
        # State tracking
        self.serial_conn: Optional[serial.Serial] = None
        self.time_synced = False
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        # Create logger
        logger = logging.getLogger('gps_time_sync')
        logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler for systemd journal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler for persistent logs
        try:
            log_file = Path('/var/log/bathyimager/gps_time_sync.log')
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create log file: {e}")
        
        return logger
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def _detect_gps_port(self) -> Optional[str]:
        """Detect GPS device port by trying common ports"""
        self.logger.debug("Detecting GPS device...")
        
        for port in self.gps_ports:
            try:
                self.logger.debug(f"Trying GPS port: {port}")
                
                # Check if port exists
                if not Path(port).exists():
                    continue
                
                # Try to open and read from port
                with serial.Serial(port, self.baudrate, timeout=self.timeout) as ser:
                    # Read a few lines to see if we get NMEA data
                    for _ in range(3):  # Reduced attempts for faster detection
                        line = ser.readline().decode('ascii', errors='ignore').strip()
                        if line and line.startswith('$'):
                            self.logger.info(f"GPS device detected on {port}")
                            return port
                        
            except Exception as e:
                self.logger.debug(f"Could not access {port}: {e}")
                continue
        
        self.logger.warning("No GPS device detected on any port")
        return None
    
    def _connect_gps(self) -> bool:
        """Connect to GPS device"""
        port = self._detect_gps_port()
        if not port:
            return False
        
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            self.logger.info(f"Connected to GPS on {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to GPS: {e}")
            return False
    
    def _ensure_utc_timezone(self) -> bool:
        """Ensure system timezone is set to UTC"""
        try:
            # Use timedatectl to set timezone to UTC
            result = subprocess.run(
                ['timedatectl', 'set-timezone', 'UTC'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("System timezone confirmed as UTC")
                return True
            else:
                self.logger.warning(f"Could not set UTC timezone: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Timezone setting command timed out")
            return False
        except Exception as e:
            self.logger.warning(f"Error setting UTC timezone: {e}")
            return False
    
    def _set_system_time(self, gps_datetime: datetime) -> bool:
        """Set system time from GPS datetime"""
        try:
            # Format time for timedatectl (YYYY-MM-DD HH:MM:SS format)
            time_str = gps_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            # Use timedatectl to set time (more reliable than date command)
            result = subprocess.run(
                ['timedatectl', 'set-time', time_str],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info(f"System time set to GPS time: {time_str} UTC")
                self.time_synced = True
                return True
            else:
                self.logger.error(f"Failed to set system time: {result.stderr}")
                
                # Fallback to date command
                return self._set_system_time_fallback(gps_datetime)
                
        except subprocess.TimeoutExpired:
            self.logger.error("Time setting command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error setting system time: {e}")
            return False
    
    def _set_system_time_fallback(self, gps_datetime: datetime) -> bool:
        """Fallback method to set system time using date command"""
        try:
            # Format for date command: MMDDhhmmYYYY.ss
            date_str = gps_datetime.strftime("%m%d%H%M%Y.%S")
            
            result = subprocess.run(
                ['date', date_str],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info(f"System time set via date command: {gps_datetime} UTC")
                self.time_synced = True
                return True
            else:
                self.logger.error(f"Date command failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Fallback time setting failed: {e}")
            return False
    
    def _wait_for_gps_fix(self, quick_mode: bool = False) -> Optional[Tuple[datetime, float, float]]:
        """Wait for GPS fix and return time and coordinates"""
        if not self.serial_conn:
            return None
        
        max_wait = 30 if quick_mode else self.max_wait_time  # Quick mode for periodic sync
        self.logger.info(f"Waiting for GPS fix (max {max_wait}s)...")
        
        start_time = time.time()
        sentence_count = 0
        last_log_time = 0
        
        gps_time = None
        latitude = None
        longitude = None
        
        while time.time() - start_time < max_wait:
            try:
                # Read NMEA sentence
                line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                
                if not line:
                    continue
                
                sentence_count += 1
                
                # Log progress every 15 seconds (reduced from 30)
                current_time = time.time()
                if current_time - last_log_time > 15:
                    elapsed = current_time - start_time
                    self.logger.info(f"GPS search: {elapsed:.1f}s elapsed, {sentence_count} sentences processed")
                    last_log_time = current_time
                
                # Try to parse NMEA sentence
                try:
                    parsed = pynmea2.parse(line)
                except Exception:
                    continue
                
                # Process RMC sentences for time and basic position
                if isinstance(parsed, pynmea2.RMC) and parsed.status == 'A':
                    # Extract time and date
                    if parsed.timestamp and parsed.datestamp:
                        # Combine date and time
                        gps_datetime = datetime.combine(parsed.datestamp, parsed.timestamp)
                        gps_time = gps_datetime.replace(tzinfo=timezone.utc)
                        
                        # Extract position
                        if parsed.latitude and parsed.longitude:
                            latitude = float(parsed.latitude)
                            longitude = float(parsed.longitude)
                            
                            # Apply direction indicators
                            if parsed.lat_dir == 'S':
                                latitude = -latitude
                            if parsed.lon_dir == 'W':
                                longitude = -longitude
                
                # Also check GGA for position quality
                elif isinstance(parsed, pynmea2.GGA) and parsed.gps_qual and int(parsed.gps_qual) > 0:
                    # Extract position from GGA if available
                    if parsed.latitude and parsed.longitude:
                        latitude = float(parsed.latitude)
                        longitude = float(parsed.longitude)
                        
                        # Apply direction indicators
                        if parsed.lat_dir == 'S':
                            latitude = -latitude
                        if parsed.lon_dir == 'W':
                            longitude = -longitude
                
                # Check if we have both time and position
                if gps_time and latitude is not None and longitude is not None:
                    elapsed = time.time() - start_time
                    self.logger.info(f"GPS fix acquired in {elapsed:.1f}s: {gps_time} at {latitude:.6f}, {longitude:.6f}")
                    return gps_time, latitude, longitude
                
            except Exception as e:
                self.logger.debug(f"Error processing GPS data: {e}")
                continue
        
        elapsed = time.time() - start_time
        self.logger.warning(f"GPS fix timeout after {elapsed:.1f} seconds ({sentence_count} sentences processed)")
        return None
    
    def sync_time(self, mode: str = "boot") -> bool:
        """Main method to synchronize system time with GPS"""
        is_boot_sync = mode == "boot"
        sync_type = "boot" if is_boot_sync else "periodic"
        
        self.logger.info(f"Starting GPS {sync_type} time synchronization...")
        
        # Check if we're in boot mode and already synced (avoid multiple runs)
        if is_boot_sync:
            sync_marker = Path('/var/run/gps_time_synced')
            if sync_marker.exists():
                self.logger.info("GPS time already synchronized this boot cycle")
                return True
        
        try:
            # Ensure UTC timezone (always do this)
            self._ensure_utc_timezone()
            
            # Connect to GPS
            if not self._connect_gps():
                self.logger.warning(f"GPS connection failed for {sync_type} sync")
                return False
            
            # Wait for GPS fix (use quick mode for periodic sync)
            quick_mode = not is_boot_sync
            gps_data = self._wait_for_gps_fix(quick_mode=quick_mode)
            if not gps_data:
                self.logger.warning(f"GPS fix not acquired for {sync_type} sync")
                return False
            
            gps_time, latitude, longitude = gps_data
            
            # Set system time
            if self._set_system_time(gps_time):
                # Create sync marker for boot sync to prevent multiple runs
                if is_boot_sync:
                    try:
                        sync_marker = Path('/var/run/gps_time_synced')
                        sync_marker.write_text(f"GPS time synced at {datetime.now().isoformat()}\n")
                        self.logger.info(f"GPS {sync_type} time synchronization completed successfully")
                    except Exception as e:
                        self.logger.warning(f"Could not create sync marker: {e}")
                else:
                    self.logger.info(f"GPS {sync_type} time synchronization completed successfully")
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"GPS {sync_type} time synchronization failed: {e}")
            return False
            
        finally:
            # Clean up connection
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
    
    def cleanup(self):
        """Clean up resources"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass


def main():
    """Main entry point for GPS time sync service"""
    parser = argparse.ArgumentParser(description='GPS Time Synchronization Service')
    parser.add_argument('--boot', action='store_true', 
                       help='Run boot-time synchronization (one-time per boot)')
    parser.add_argument('--periodic', action='store_true',
                       help='Run periodic synchronization')
    parser.add_argument('--config', type=str,
                       default='/home/bathyimager/BathyCat-Seabed-Imager/config/bathycat_config.json',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.boot and args.periodic:
        print("Error: Cannot specify both --boot and --periodic")
        sys.exit(1)
    elif args.boot:
        mode = "boot"
    elif args.periodic:
        mode = "periodic"
    else:
        # Default to boot mode if no mode specified
        mode = "boot"
    
    # Set up basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logger = logging.getLogger('gps_time_sync')
    logger.info(f"GPS Time Synchronization Service starting in {mode} mode...")
    
    try:
        # Create and run GPS sync service
        gps_sync = GPSTimeSync(config_path=args.config)
        success = gps_sync.sync_time(mode=mode)
        
        if success:
            logger.info(f"GPS {mode} time synchronization service completed successfully")
            sys.exit(0)
        else:
            logger.warning(f"GPS {mode} time synchronization service completed with warnings")
            sys.exit(0)  # Don't fail the service for periodic syncs without GPS
            
    except KeyboardInterrupt:
        logger.info("GPS time synchronization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in GPS sync service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()