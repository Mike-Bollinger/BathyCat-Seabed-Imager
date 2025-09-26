#!/usr/bin/env python3
"""
GPS Controller for BathyCat Seabed Imager
========================================

Handles GPS communication, time synchronization, and position tracking
using the Adafruit Mini GPS PA1010D USB module.

Author: Mike Bollinger
Date: August 2025
"""

import asyncio
import logging
import serial
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import pynmea2


class GPSController:
    """Controls GPS operations and time synchronization."""
    
    def __init__(self, config):
        """Initialize GPS controller."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.serial_port = None
        self.is_initialized = False
        
        # GPS settings
        self.port = config.gps_port
        self.baudrate = config.gps_baudrate
        self.timeout = config.gps_timeout
        
        # Current GPS data
        self.current_position = {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'timestamp': None,
            'quality': 0,
            'satellites': 0,
            'hdop': None,
            'speed': None,
            'course': None
        }
        
        # Status tracking
        self.has_fix_flag = False
        self.last_update_time = 0
        self.message_count = 0
        self.error_count = 0
        
        # Time sync
        self.time_sync_enabled = config.gps_time_sync
        self.last_time_sync = 0
    
    async def initialize(self) -> bool:
        """Initialize GPS connection."""
        self.logger.info(f"Initializing USB GPS on {self.port} @ {self.baudrate}")
        
        try:
            # For USB GPS, we may need to detect the correct port
            if self.port == "auto" or not self.port:
                self.port = await self._detect_usb_gps_port()
                if not self.port:
                    self.logger.error("Could not detect USB GPS device")
                    return False
            
            # Open serial connection
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            if not self.serial_port.is_open:
                self.logger.error("Failed to open GPS serial port")
                return False
            
            # Wait for GPS data
            self.logger.info("Waiting for GPS data...")
            await asyncio.sleep(2.0)
            
            # Test GPS communication
            if not await self._test_gps_communication():
                self.logger.error("GPS communication test failed")
                return False
            
            # Configure GPS settings
            await self._configure_gps()
            
            self.is_initialized = True
            self.logger.info(f"USB GPS initialization complete on {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"GPS initialization failed: {e}")
            return False
    
    async def _detect_usb_gps_port(self) -> Optional[str]:
        """Detect USB GPS device port automatically."""
        try:
            import serial.tools.list_ports
            
            # Look for Adafruit GPS devices
            gps_ports = []
            
            for port in serial.tools.list_ports.comports():
                # Check for Adafruit VID/PID or common GPS device names
                if (port.vid == 0x239A or  # Adafruit VID
                    'GPS' in port.description.upper() or
                    'ADAFRUIT' in port.description.upper() or
                    'PA1010D' in port.description.upper()):
                    gps_ports.append(port.device)
                    self.logger.info(f"Found potential GPS device: {port.device} - {port.description}")
            
            # If no specific GPS devices found, look for generic USB-Serial devices
            if not gps_ports:
                for port in serial.tools.list_ports.comports():
                    if ('USB' in port.description.upper() and 
                        'SERIAL' in port.description.upper()):
                        gps_ports.append(port.device)
                        self.logger.info(f"Found USB-Serial device: {port.device} - {port.description}")
            
            if gps_ports:
                # Try the first detected port
                selected_port = gps_ports[0]
                self.logger.info(f"Auto-detected GPS port: {selected_port}")
                return selected_port
            
            self.logger.error("No USB GPS device detected")
            return None
            
        except ImportError:
            self.logger.warning("serial.tools.list_ports not available, cannot auto-detect GPS")
            return None
        except Exception as e:
            self.logger.error(f"GPS port detection error: {e}")
            return None
    
    async def _test_gps_communication(self) -> bool:
        """Test GPS communication by reading NMEA sentences."""
        try:
            for attempt in range(10):
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                    if line.startswith('$'):
                        self.logger.info(f"GPS communication confirmed: {line[:20]}...")
                        return True
                
                await asyncio.sleep(0.5)
            
            self.logger.error("No GPS data received")
            return False
            
        except Exception as e:
            self.logger.error(f"GPS communication test error: {e}")
            return False
    
    async def _configure_gps(self):
        """Configure GPS module settings."""
        self.logger.info("Configuring GPS settings...")
        
        try:
            # Commands to configure GPS for optimal performance
            commands = [
                # Set update rate to 10Hz for high-frequency positioning
                b'$PMTK220,100*2F\r\n',  # 10Hz update rate
                
                # Enable specific NMEA sentences
                # GGA (Global Positioning System Fix Data)
                # RMC (Recommended Minimum Navigation Information)
                # GSA (GPS DOP and active satellites)
                # GSV (GPS Satellites in view)
                b'$PMTK314,0,1,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0*29\r\n',
                
                # Enable SBAS (Satellite Based Augmentation System)
                b'$PMTK313,1*2E\r\n',
                
                # Set antenna
                b'$PGCMD,33,1*6C\r\n',
            ]
            
            for cmd in commands:
                self.serial_port.write(cmd)
                await asyncio.sleep(0.1)
            
            self.logger.info("GPS configuration complete")
            
        except Exception as e:
            self.logger.warning(f"GPS configuration failed: {e}")
    
    async def update(self) -> bool:
        """Update GPS data by reading NMEA sentences."""
        if not self.is_initialized:
            return False
        
        try:
            updated = False
            
            # Read all available data
            while self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith('$'):
                    if await self._process_nmea_sentence(line):
                        updated = True
                        self.last_update_time = time.time()
            
            return updated
            
        except Exception as e:
            self.logger.error(f"GPS update error: {e}")
            self.error_count += 1
            return False
    
    async def _process_nmea_sentence(self, sentence: str) -> bool:
        """Process a single NMEA sentence."""
        try:
            msg = pynmea2.parse(sentence)
            self.message_count += 1
            
            # Process different message types
            if isinstance(msg, pynmea2.types.talker.GGA):
                return await self._process_gga(msg)
            
            elif isinstance(msg, pynmea2.types.talker.RMC):
                return await self._process_rmc(msg)
            
            elif isinstance(msg, pynmea2.types.talker.GSA):
                return await self._process_gsa(msg)
            
            return False
            
        except pynmea2.ParseError:
            # Ignore parse errors, they're common with partial messages
            return False
        
        except Exception as e:
            self.logger.debug(f"NMEA processing error: {e}")
            return False
    
    async def _process_gga(self, msg) -> bool:
        """Process GGA (Global Positioning System Fix Data) message."""
        try:
            self.logger.debug(f"🛰️ GGA_PROCESS: lat={getattr(msg, 'latitude', 'NONE')}, lon={getattr(msg, 'longitude', 'NONE')}")
            if (msg.latitude is not None) and (msg.longitude is not None):
                self.current_position['latitude'] = float(msg.latitude)
                self.current_position['longitude'] = float(msg.longitude)
                self.current_position['altitude'] = float(msg.altitude) if msg.altitude else None
                self.current_position['quality'] = int(msg.gps_qual) if msg.gps_qual else 0
                self.current_position['satellites'] = int(msg.num_sats) if msg.num_sats else 0
                self.current_position['hdop'] = float(msg.horizontal_dil) if msg.horizontal_dil else None
                self.current_position['timestamp'] = datetime.now(timezone.utc)
                
                # Update fix status
                self.has_fix_flag = self.current_position['quality'] > 0
                
                return True
            
            return False
            
        except (ValueError, AttributeError) as e:
            self.logger.error(f"🚨 GGA_PROCESSING_ERROR: {e}")
            return False
    
    async def _process_rmc(self, msg) -> bool:
        """Process RMC (Recommended Minimum Navigation Information) message."""
        try:
            self.logger.debug(f"🛰️ RMC_PROCESS: lat={getattr(msg, 'latitude', 'NONE')}, lon={getattr(msg, 'longitude', 'NONE')}")
            if (msg.latitude is not None) and (msg.longitude is not None):
                # Update position if not already set by GGA
                if self.current_position['latitude'] is None:
                    self.current_position['latitude'] = float(msg.latitude)
                    self.current_position['longitude'] = float(msg.longitude)
                
                # Update speed and course
                self.current_position['speed'] = float(msg.spd_over_grnd) if msg.spd_over_grnd else None
                self.current_position['course'] = float(msg.true_course) if msg.true_course else None
                
                # Time synchronization
                if (self.time_sync_enabled and 
                    msg.timestamp is not None and 
                    msg.datestamp is not None):
                    await self._sync_system_time(msg.timestamp, msg.datestamp)
                
                return True
            
            return False
            
        except (ValueError, AttributeError) as e:
            self.logger.error(f"🚨 RMC_PROCESSING_ERROR: {e}")
            return False
    
    async def _process_gsa(self, msg) -> bool:
        """Process GSA (GPS DOP and active satellites) message."""
        try:
            # This provides additional quality information
            # Could be used for enhanced quality assessment
            return False  # Don't count as a position update
            
        except Exception as e:
            self.logger.debug(f"GSA processing error: {e}")
            return False
    
    async def _sync_system_time(self, gps_time, gps_date):
        """Synchronize system time with GPS time."""
        try:
            # Only sync once per minute to avoid excessive system calls
            current_time = time.time()
            if current_time - self.last_time_sync < 60:
                return
            
            # Parse GPS time and date
            gps_datetime = datetime.combine(gps_date, gps_time, timezone.utc)
            
            # Compare with system time
            system_time = datetime.now(timezone.utc)
            time_diff = abs((gps_datetime - system_time).total_seconds())
            
            # Only sync if difference is significant (>1 second)
            if time_diff > 1.0:
                self.logger.info(f"Time sync: GPS={gps_datetime}, System={system_time}, Diff={time_diff:.1f}s")
                
                # Note: Actual system time setting would require root privileges
                # This would typically be done via ntpd or chrony integration
                # For now, just log the difference
                
            self.last_time_sync = current_time
            
        except Exception as e:
            self.logger.debug(f"Time sync error: {e}")
    
    async def wait_for_fix(self, timeout: float = 300.0) -> bool:
        """Wait for GPS fix with timeout."""
        self.logger.info(f"Waiting for GPS fix (timeout: {timeout}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            await self.update()
            
            if self.has_fix():
                self.logger.info("GPS fix acquired")
                return True
            
            await asyncio.sleep(1.0)
        
        self.logger.warning("GPS fix timeout")
        return False
    
    def has_fix(self) -> bool:
        """Check if GPS has a valid fix."""
        return (
            self.has_fix_flag and
            self.current_position['latitude'] is not None and
            self.current_position['longitude'] is not None and
            time.time() - self.last_update_time < 10.0  # Data not older than 10 seconds
        )
    
    def get_current_position(self) -> Dict[str, Any]:
        """Get current GPS position data."""
        return self.current_position.copy()
    
    def get_position_string(self) -> str:
        """Get formatted position string."""
        if not self.has_fix():
            return "No GPS Fix"
        
        lat = self.current_position['latitude']
        lon = self.current_position['longitude']
        alt = self.current_position['altitude']
        sats = self.current_position['satellites']
        
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        
        pos_str = f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"
        
        if alt is not None:
            pos_str += f", {alt:.1f}m"
        
        pos_str += f" ({sats} sats)"
        
        return pos_str
    
    def get_gps_stats(self) -> Dict[str, Any]:
        """Get GPS statistics."""
        return {
            'has_fix': self.has_fix(),
            'message_count': self.message_count,
            'error_count': self.error_count,
            'last_update': self.last_update_time,
            'position': self.get_position_string()
        }
    
    async def shutdown(self):
        """Shutdown GPS controller."""
        self.logger.info("Shutting down GPS...")
        
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.is_initialized = False
            
            # Log final statistics
            stats = self.get_gps_stats()
            self.logger.info(
                f"GPS stats: {stats['message_count']} messages, "
                f"{stats['error_count']} errors, "
                f"Final position: {stats['position']}"
            )
            
            self.logger.info("GPS shutdown complete")
            
        except Exception as e:
            self.logger.error(f"GPS shutdown error: {e}")


class GPSError(Exception):
    """Custom exception for GPS-related errors."""
    pass
