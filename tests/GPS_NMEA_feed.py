#!/usr/bin/env python3
"""
GPS NMEA Feed Reader
===================

Direct NMEA sentence reader for GPS diagnostics. This script connects directly
to the GPS serial port and displays raw NMEA sentences to verify GPS functionality.

Usage:
    python3 GPS_NMEA_feed.py [options]

Options:
    --port PORT     GPS serial port (default: /dev/serial0)
    --baudrate BAUD GPS baudrate (default: 9600)
    --timeout SEC   Read timeout in seconds (default: 5.0)
    --count NUM     Number of sentences to read (default: continuous)
    --parse         Parse and display sentence details
    --quiet         Only show parsed data, not raw sentences
    --help          Show this help message

Examples:
    python3 GPS_NMEA_feed.py                           # Basic continuous read
    python3 GPS_NMEA_feed.py --parse --count 50        # Parse 50 sentences
    python3 GPS_NMEA_feed.py --port /dev/ttyUSB0       # Use USB GPS
    python3 GPS_NMEA_feed.py --quiet --parse           # Only show parsed data
"""

import sys
import serial
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, Any


class NMEAReader:
    """NMEA sentence reader and parser."""
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 5.0):
        """
        Initialize NMEA reader.
        
        Args:
            port: Serial port path
            baudrate: Serial communication baudrate
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.sentence_count = 0
        self.valid_sentences = 0
        self.error_count = 0
        
    def connect(self) -> bool:
        """
        Connect to GPS serial port.
        
        Returns:
            bool: True if connection successful
        """
        try:
            print(f"🔌 Connecting to GPS on {self.port} at {self.baudrate} baud...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            if not self.serial_conn.is_open:
                raise Exception(f"Failed to open port {self.port}")
                
            print(f"✅ Connected successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from GPS serial port."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"🔌 Disconnected from {self.port}")
    
    def read_sentence(self) -> Optional[str]:
        """
        Read a single NMEA sentence.
        
        Returns:
            str: NMEA sentence or None if timeout/error
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
            
        try:
            # Read until we get a complete NMEA sentence (ending with \r\n)
            sentence = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
            
            if sentence:
                self.sentence_count += 1
                if sentence.startswith('$') and len(sentence) > 6:
                    self.valid_sentences += 1
                    return sentence
                else:
                    # Invalid sentence format
                    self.error_count += 1
                    return sentence
            
            return None
            
        except Exception as e:
            self.error_count += 1
            print(f"⚠️  Read error: {e}")
            return None
    
    def parse_sentence(self, sentence: str) -> Optional[Dict[str, Any]]:
        """
        Parse NMEA sentence into components.
        
        Args:
            sentence: Raw NMEA sentence
            
        Returns:
            dict: Parsed sentence data or None if invalid
        """
        if not sentence or not sentence.startswith('$'):
            return None
            
        try:
            # Remove $ and split on commas
            parts = sentence[1:].split(',')
            if len(parts) < 2:
                return None
                
            sentence_type = parts[0]
            
            # Parse common sentence types
            parsed = {
                'raw': sentence,
                'type': sentence_type,
                'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                'valid': True
            }
            
            if sentence_type == 'GPGGA':
                # Global Positioning System Fix Data
                if len(parts) >= 15:
                    parsed.update({
                        'time': parts[1],
                        'latitude': self._parse_coordinate(parts[2], parts[3]),
                        'longitude': self._parse_coordinate(parts[4], parts[5]),
                        'fix_quality': parts[6],
                        'satellites': parts[7],
                        'hdop': parts[8],
                        'altitude': parts[9],
                        'altitude_units': parts[10],
                        'description': 'GPS Fix Data'
                    })
                    
            elif sentence_type == 'GPRMC':
                # Recommended Minimum Course
                if len(parts) >= 12:
                    parsed.update({
                        'time': parts[1],
                        'status': parts[2],  # A=Active, V=Void
                        'latitude': self._parse_coordinate(parts[3], parts[4]),
                        'longitude': self._parse_coordinate(parts[5], parts[6]),
                        'speed': parts[7],
                        'course': parts[8],
                        'date': parts[9],
                        'description': 'Recommended Minimum Course'
                    })
                    
            elif sentence_type == 'GPGSV':
                # Satellites in View
                if len(parts) >= 4:
                    parsed.update({
                        'total_messages': parts[1],
                        'message_number': parts[2],
                        'satellites_in_view': parts[3],
                        'description': 'Satellites in View'
                    })
                    
            elif sentence_type == 'GPGSA':
                # GPS DOP and Active Satellites
                if len(parts) >= 18:
                    parsed.update({
                        'mode': parts[1],
                        'fix_type': parts[2],
                        'pdop': parts[15],
                        'hdop': parts[16],
                        'vdop': parts[17],
                        'description': 'GPS DOP and Active Satellites'
                    })
            
            return parsed
            
        except Exception as e:
            return {
                'raw': sentence,
                'type': 'UNKNOWN',
                'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                'valid': False,
                'error': str(e)
            }
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> Optional[float]:
        """Parse NMEA coordinate format to decimal degrees."""
        if not coord_str or not direction:
            return None
            
        try:
            # NMEA format: DDMM.MMMM or DDDMM.MMMM
            if len(coord_str) < 4:
                return None
                
            # Find decimal point
            dot_pos = coord_str.find('.')
            if dot_pos == -1:
                return None
                
            # Extract degrees and minutes
            if dot_pos == 4:  # Latitude: DDMM.MMMM
                degrees = int(coord_str[:2])
                minutes = float(coord_str[2:])
            elif dot_pos == 5:  # Longitude: DDDMM.MMMM
                degrees = int(coord_str[:3])
                minutes = float(coord_str[3:])
            else:
                return None
                
            # Convert to decimal degrees
            decimal = degrees + (minutes / 60.0)
            
            # Apply direction
            if direction in ['S', 'W']:
                decimal = -decimal
                
            return decimal
            
        except Exception:
            return None
    
    def print_statistics(self):
        """Print reading statistics."""
        print(f"\n📊 Statistics:")
        print(f"   Total sentences: {self.sentence_count}")
        print(f"   Valid sentences: {self.valid_sentences}")
        print(f"   Errors: {self.error_count}")
        if self.sentence_count > 0:
            success_rate = (self.valid_sentences / self.sentence_count) * 100
            print(f"   Success rate: {success_rate:.1f}%")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='GPS NMEA Feed Reader - Direct diagnostic tool for GPS connectivity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 GPS_NMEA_feed.py                           # Basic continuous read
  python3 GPS_NMEA_feed.py --parse --count 50        # Parse 50 sentences  
  python3 GPS_NMEA_feed.py --port /dev/ttyUSB0       # Use USB GPS
  python3 GPS_NMEA_feed.py --quiet --parse           # Only show parsed data
        """
    )
    
    parser.add_argument('--port', default='/dev/serial0',
                       help='GPS serial port (default: /dev/serial0)')
    parser.add_argument('--baudrate', type=int, default=9600,
                       help='GPS baudrate (default: 9600)')
    parser.add_argument('--timeout', type=float, default=5.0,
                       help='Read timeout in seconds (default: 5.0)')
    parser.add_argument('--count', type=int, default=0,
                       help='Number of sentences to read (default: continuous)')
    parser.add_argument('--parse', action='store_true',
                       help='Parse and display sentence details')
    parser.add_argument('--quiet', action='store_true',
                       help='Only show parsed data, not raw sentences')
    
    args = parser.parse_args()
    
    print("🛰️  GPS NMEA Feed Reader")
    print("=" * 50)
    
    # Create reader
    reader = NMEAReader(args.port, args.baudrate, args.timeout)
    
    # Connect to GPS
    if not reader.connect():
        return 1
    
    try:
        print(f"📡 Reading NMEA sentences from {args.port}...")
        if args.count > 0:
            print(f"   (Reading {args.count} sentences)")
        else:
            print("   (Press Ctrl+C to stop)")
        print()
        
        sentence_count = 0
        
        while True:
            sentence = reader.read_sentence()
            
            if sentence:
                sentence_count += 1
                
                if args.parse:
                    # Parse and display formatted data
                    parsed = reader.parse_sentence(sentence)
                    
                    if parsed and not args.quiet:
                        print(f"[{parsed['timestamp']}] {parsed['type']}: {parsed.get('description', 'Unknown')}")
                        
                        # Show key fields for important sentence types
                        if parsed['type'] == 'GPGGA' and parsed.get('fix_quality', '0') != '0':
                            lat = parsed.get('latitude')
                            lon = parsed.get('longitude')
                            alt = parsed.get('altitude')
                            sats = parsed.get('satellites')
                            if lat and lon:
                                print(f"   📍 Position: {lat:.6f}, {lon:.6f}")
                            if alt:
                                print(f"   ⬆️  Altitude: {alt}m")
                            if sats:
                                print(f"   🛰️  Satellites: {sats}")
                        
                        elif parsed['type'] == 'GPRMC' and parsed.get('status') == 'A':
                            lat = parsed.get('latitude')
                            lon = parsed.get('longitude')
                            speed = parsed.get('speed')
                            if lat and lon:
                                print(f"   📍 Position: {lat:.6f}, {lon:.6f}")
                            if speed:
                                print(f"   🏃 Speed: {speed} knots")
                    
                    elif parsed and args.quiet:
                        # Quiet mode - only show important parsed data
                        if parsed['type'] == 'GPGGA' and parsed.get('fix_quality', '0') != '0':
                            lat = parsed.get('latitude')
                            lon = parsed.get('longitude')
                            sats = parsed.get('satellites')
                            if lat and lon:
                                print(f"{parsed['timestamp']} GPS Fix: {lat:.6f}, {lon:.6f} ({sats} sats)")
                
                if not args.quiet and not args.parse:
                    # Raw sentence display
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    print(f"[{timestamp}] {sentence}")
                
                elif not args.quiet and args.parse:
                    # Show raw sentence too
                    print(f"   Raw: {sentence}")
                    print()
                
                # Check count limit
                if args.count > 0 and sentence_count >= args.count:
                    print(f"\n✅ Read {sentence_count} sentences as requested.")
                    break
                    
            else:
                print("⏳ No data received (timeout)...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Stopped by user after {sentence_count} sentences")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        reader.disconnect()
        reader.print_statistics()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())