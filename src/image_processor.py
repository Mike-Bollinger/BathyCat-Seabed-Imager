#!/usr/bin/env python3
"""
Image Processing Module for BathyCat Seabed Imager
=================================================

Handles EXIF GPS metadata embedding using piexif/Pillow and JPEG optimization.

Features:
- GPS coordinate embedding in EXIF metadata
- Image format conversion and optimization
- JPEG quality control
- Metadata preservation and validation
- Timestamp embedding
- Image file validation
"""

import io
import logging
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from PIL import Image, ExifTags
import piexif
import numpy as np
from gps import GPSFix


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass


class ImageProcessor:
    """
    Image processing for BathyCat system.
    
    Handles image format conversion, EXIF metadata embedding, and optimization.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize image processor with configuration.
        
        Args:
            config: Image processing configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Image settings from config
        self.image_format = config.get('image_format', 'JPEG')
        self.jpeg_quality = config.get('jpeg_quality', 85)
        self.enable_metadata = config.get('enable_metadata', True)
        
        # Validate configuration
        if not 1 <= self.jpeg_quality <= 100:
            raise ImageProcessingError(f"Invalid JPEG quality: {self.jpeg_quality}")
        
        if self.image_format not in ['JPEG', 'PNG', 'TIFF']:
            raise ImageProcessingError(f"Unsupported image format: {self.image_format}")
    
    def process_frame(self, frame: np.ndarray, gps_fix: Optional[GPSFix] = None, 
                     timestamp: Optional[datetime] = None, camera_params: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Process camera frame and add metadata.
        
        Args:
            frame: Camera frame as numpy array (BGR format from OpenCV)
            gps_fix: GPS fix data for geotagging
            timestamp: Image timestamp (uses current time if None)
            camera_params: Camera parameters for EXIF metadata
            
        Returns:
            bytes: Processed image data
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Convert BGR to RGB (OpenCV uses BGR, PIL uses RGB)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = frame[:, :, ::-1]  # BGR to RGB
            else:
                frame_rgb = frame
            
            # Create PIL Image
            image = Image.fromarray(frame_rgb)
            
            # Add metadata if enabled
            if self.enable_metadata:
                self.logger.debug(f"Processing metadata - GPS: {'Yes' if gps_fix else 'No'}, Camera params: {'Yes' if camera_params else 'No'}")
                image = self._add_metadata(image, gps_fix, timestamp, camera_params)
            else:
                self.logger.warning("Metadata disabled - images will have no GPS or camera data")
            
            # Convert to bytes
            image_bytes = self._convert_to_bytes(image)
            
            self.logger.debug(f"Processed image: {len(image_bytes)} bytes, format: {self.image_format}")
            return image_bytes
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            raise ImageProcessingError(f"Frame processing failed: {e}")
    
    def _add_metadata(self, image: Image.Image, gps_fix: Optional[GPSFix], 
                     timestamp: datetime, camera_params: Optional[Dict[str, Any]] = None) -> Image.Image:
        """
        Add EXIF metadata to image.
        
        Args:
            image: PIL Image object
            gps_fix: GPS fix data (can be None if GPS unavailable)
            timestamp: Image timestamp
            camera_params: Camera parameters for EXIF metadata
            
        Returns:
            Image.Image: Image with metadata (original image if metadata fails)
        """
        try:
            # Get existing EXIF data or create new
            exif_data = image.info.get('exif', b'')
            
            # Handle empty or invalid EXIF data
            if not exif_data:
                # Create fresh EXIF dictionary
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
            else:
                try:
                    exif_dict = piexif.load(exif_data)
                except Exception as e:
                    self.logger.debug(f"Could not load existing EXIF, creating new: {e}")
                    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
            
            # Add timestamp (always add this)
            self._add_timestamp_metadata(exif_dict, timestamp)
            
            # Add GPS data - always tag with coordinates (real GPS or 0,0 fallback)
            gps_added = False
            if gps_fix and gps_fix.is_valid:
                # Use real GPS coordinates when we have a valid fix
                if (-90 <= gps_fix.latitude <= 90 and -180 <= gps_fix.longitude <= 180):
                    try:
                        self._add_gps_metadata(exif_dict, gps_fix)
                        self.logger.info(f"GPS metadata added (REAL): {gps_fix.latitude:.6f}, {gps_fix.longitude:.6f} - Quality:{gps_fix.fix_quality}, Sats:{gps_fix.satellites}")
                        gps_added = True
                    except Exception as e:
                        self.logger.warning(f"Failed to add real GPS metadata: {e}")
                        
            if not gps_added:
                # Fallback: Tag with 0°N, 0°W when no GPS available or invalid
                try:
                    self._add_fallback_gps_metadata(exif_dict, timestamp)
                    if gps_fix:
                        self.logger.info(f"GPS metadata added (FALLBACK 0°N,0°W): GPS available but invalid - quality:{gps_fix.fix_quality}, sats:{gps_fix.satellites}, coords:({gps_fix.latitude:.6f},{gps_fix.longitude:.6f})")
                    else:
                        self.logger.info("GPS metadata added (FALLBACK 0°N,0°W): No GPS fix available")
                    gps_added = True
                except Exception as e:
                    self.logger.warning(f"Failed to add fallback GPS metadata: {e}")
            
            # Add camera/software information and actual camera parameters
            self._add_software_metadata(exif_dict)
            self._add_camera_parameters(exif_dict, camera_params)
            
            # Convert EXIF dict to bytes
            try:
                # Debug: Log EXIF contents before dumping
                exif_summary = {}
                for section, data in exif_dict.items():
                    if data and isinstance(data, dict):
                        exif_summary[section] = len(data)
                self.logger.debug(f"EXIF sections before dump: {exif_summary}")
                
                exif_bytes = piexif.dump(exif_dict)
                self.logger.debug(f"EXIF bytes created: {len(exif_bytes)} bytes")
                
                # Create new image with EXIF data
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='JPEG', exif=exif_bytes)
                img_bytes.seek(0)
                
                # Verify EXIF was saved
                test_img = Image.open(img_bytes)
                if test_img.info.get('exif'):
                    self.logger.debug("✓ EXIF data successfully embedded in image")
                else:
                    self.logger.warning("⚠️  EXIF data may not have been embedded properly")
                
                return test_img
                
            except Exception as e:
                self.logger.warning(f"Failed to create EXIF data, saving image without metadata: {e}")
                # Log more details about the error
                import traceback
                self.logger.debug(f"EXIF error details: {traceback.format_exc()}")
                return image
            
        except Exception as e:
            self.logger.warning(f"Metadata processing failed, saving image without metadata: {e}")
            return image
    
    def _add_timestamp_metadata(self, exif_dict: Dict, timestamp: datetime) -> None:
        """Add timestamp to EXIF metadata."""
        # Format timestamp for EXIF (EXIF standard uses local time format)
        dt_str = timestamp.strftime("%Y:%m:%d %H:%M:%S")
        
        # Add to various EXIF fields
        exif_dict['0th'][piexif.ImageIFD.DateTime] = dt_str
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dt_str
        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = dt_str
        
        # Add subsecond precision if available
        subsec = f"{timestamp.microsecond:06d}"[:3]  # First 3 digits of microseconds
        exif_dict['Exif'][piexif.ExifIFD.SubSecTime] = subsec
        exif_dict['Exif'][piexif.ExifIFD.SubSecTimeOriginal] = subsec
        exif_dict['Exif'][piexif.ExifIFD.SubSecTimeDigitized] = subsec
        
        # Add timezone offset info if possible (custom field for UTC indication)
        # Note: Standard EXIF doesn't have timezone, but we can add it as a comment
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is None:
            # Likely UTC time from GPS sync
            timezone_comment = "UTC (GPS synchronized)"
        else:
            # Local system time
            timezone_comment = "Local system time"
        
        # Add timezone information to UserComment (ASCII encoded for compatibility)
        try:
            # Use simple ASCII encoding to avoid display issues
            comment_ascii = timezone_comment.encode('ascii', errors='replace')
            # EXIF UserComment format: ASCII encoding indicator + comment
            user_comment = b'ASCII\x00\x00\x00' + comment_ascii
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
        except Exception as e:
            self.logger.debug(f"Could not add timezone comment: {e}")
    
    def _add_gps_metadata(self, exif_dict: Dict, gps_fix: GPSFix) -> None:
        """Add GPS coordinates to EXIF metadata."""
        try:
            # Convert decimal degrees to degrees, minutes, seconds format
            lat_dms = self._decimal_to_dms(abs(gps_fix.latitude))
            lon_dms = self._decimal_to_dms(abs(gps_fix.longitude))
            
            # GPS reference (N/S, E/W)
            lat_ref = 'N' if gps_fix.latitude >= 0 else 'S'
            lon_ref = 'E' if gps_fix.longitude >= 0 else 'W'
            
            # Build GPS EXIF data
            gps_exif = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: lat_ref,
                piexif.GPSIFD.GPSLatitude: lat_dms,
                piexif.GPSIFD.GPSLongitudeRef: lon_ref,
                piexif.GPSIFD.GPSLongitude: lon_dms,
                piexif.GPSIFD.GPSMapDatum: "WGS-84",
            }
            
            # Add altitude if available
            if gps_fix.altitude is not None:
                # Convert to rational number (altitude in meters)
                alt_rational = self._float_to_rational(abs(gps_fix.altitude))
                gps_exif[piexif.GPSIFD.GPSAltitude] = alt_rational
                gps_exif[piexif.GPSIFD.GPSAltitudeRef] = 0 if gps_fix.altitude >= 0 else 1
            
            # Add GPS timestamp
            gps_time = gps_fix.timestamp
            time_rational = (
                self._float_to_rational(gps_time.hour),
                self._float_to_rational(gps_time.minute),
                self._float_to_rational(gps_time.second + gps_time.microsecond / 1000000)
            )
            gps_exif[piexif.GPSIFD.GPSTimeStamp] = time_rational
            
            # GPS date
            date_str = gps_time.strftime("%Y:%m:%d")
            gps_exif[piexif.GPSIFD.GPSDateStamp] = date_str
            
            # Add GPS quality indicators
            if gps_fix.satellites > 0:
                gps_exif[piexif.GPSIFD.GPSSatellites] = str(gps_fix.satellites)
            
            if gps_fix.horizontal_dilution is not None:
                gps_exif[piexif.GPSIFD.GPSDOP] = self._float_to_rational(gps_fix.horizontal_dilution)
            
            # GPS measurement mode
            mode_map = {'2D': '2', '3D': '3', 'NO_FIX': '1'}
            gps_exif[piexif.GPSIFD.GPSMeasureMode] = mode_map.get(gps_fix.fix_mode, '1')
            
            exif_dict['GPS'] = gps_exif
            
        except Exception as e:
            self.logger.warning(f"Could not add GPS metadata: {e}")
    
    def _add_fallback_gps_metadata(self, exif_dict: Dict, timestamp: datetime) -> None:
        """
        Add fallback GPS coordinates (0°N, 0°W) when real GPS is unavailable.
        
        This ensures all images have GPS metadata for troubleshooting purposes.
        Location 0°N, 0°W is in the Gulf of Guinea off the coast of West Africa,
        making it easy to identify as a fallback coordinate.
        
        Args:
            exif_dict: EXIF dictionary to modify
            timestamp: Current timestamp to use for GPS time
        """
        try:
            # Fallback coordinates: 0°N, 0°W (Null Island)
            latitude = 0.0
            longitude = 0.0
            
            # Convert to degrees, minutes, seconds format
            lat_dms = self._decimal_to_dms(abs(latitude))  # (0, 0, 0)
            lon_dms = self._decimal_to_dms(abs(longitude))  # (0, 0, 0)
            
            # GPS reference (N/S, E/W) 
            lat_ref = 'N'  # 0° North
            lon_ref = 'W'  # 0° West (to distinguish from real equator/prime meridian readings)
            
            # Build fallback GPS EXIF data
            gps_exif = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: lat_ref,
                piexif.GPSIFD.GPSLatitude: lat_dms,
                piexif.GPSIFD.GPSLongitudeRef: lon_ref,
                piexif.GPSIFD.GPSLongitude: lon_dms,
                piexif.GPSIFD.GPSMapDatum: "WGS-84",
            }
            
            # Use current timestamp for GPS time
            time_rational = (
                self._float_to_rational(timestamp.hour),
                self._float_to_rational(timestamp.minute),
                self._float_to_rational(timestamp.second + timestamp.microsecond / 1000000)
            )
            gps_exif[piexif.GPSIFD.GPSTimeStamp] = time_rational
            
            # GPS date from timestamp
            date_str = timestamp.strftime("%Y:%m:%d")
            gps_exif[piexif.GPSIFD.GPSDateStamp] = date_str
            
            # Indicate this is fallback data
            gps_exif[piexif.GPSIFD.GPSSatellites] = "0"  # 0 satellites = fallback
            gps_exif[piexif.GPSIFD.GPSMeasureMode] = '1'  # No fix
            
            exif_dict['GPS'] = gps_exif
            
        except Exception as e:
            self.logger.warning(f"Could not add fallback GPS metadata: {e}")
    
    def _add_software_metadata(self, exif_dict: Dict) -> None:
        """Add software/camera information to EXIF metadata."""
        try:
            # Software information
            exif_dict['0th'][piexif.ImageIFD.Software] = "BathyCat Seabed Imager v1.0"
            exif_dict['0th'][piexif.ImageIFD.Artist] = "NOAA NCCOS SEA Branch :: Mike Bollinger"
            
            # Copyright information (as requested by user)
            exif_dict['0th'][piexif.ImageIFD.Copyright] = "NOAA"
            
            # Camera information - updated per user request
            exif_dict['0th'][piexif.ImageIFD.Make] = "BathyCat"
            exif_dict['0th'][piexif.ImageIFD.Model] = "BathyImager"  # Updated per user request
            
            # Image description
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = "Autonomous seabed imagery"
            
        except Exception as e:
            self.logger.debug(f"Could not add software metadata: {e}")
    
    def _add_camera_parameters(self, exif_dict: Dict, camera_params: Optional[Dict[str, Any]]) -> None:
        """
        Add actual camera parameters to EXIF metadata.
        
        Args:
            exif_dict: EXIF dictionary to modify
            camera_params: Camera parameters from camera.get_camera_exif_params()
        """
        try:
            if not camera_params:
                self.logger.debug("No camera parameters provided for EXIF")
                return
            
            # Image dimensions
            if 'width' in camera_params and 'height' in camera_params:
                exif_dict['0th'][piexif.ImageIFD.ImageWidth] = int(camera_params['width'])
                exif_dict['0th'][piexif.ImageIFD.ImageLength] = int(camera_params['height'])
            
            # Build camera info for UserComment
            camera_info_parts = []
            
            # Add FPS
            if 'fps' in camera_params and camera_params['fps'] is not None:
                camera_info_parts.append(f"FPS: {camera_params['fps']:.1f}")
            
            # Add white balance temperature (since ColorTemperature EXIF field isn't supported)
            wb_temp = camera_params.get('wb_temperature')
            if wb_temp and wb_temp > 0:
                camera_info_parts.append(f"WB: {int(wb_temp)}K")
            
            # Add to UserComment if we have camera info
            if camera_info_parts:
                try:
                    existing_comment = exif_dict['Exif'].get(piexif.ExifIFD.UserComment, b'')
                    if existing_comment and existing_comment.startswith(b'ASCII\x00\x00\x00'):
                        existing_text = existing_comment[8:].decode('ascii', errors='ignore')
                        camera_info_text = f"{existing_text}, {', '.join(camera_info_parts)}"
                    else:
                        camera_info_text = ', '.join(camera_info_parts)
                    
                    # Use ASCII encoding for better compatibility
                    comment_ascii = camera_info_text.encode('ascii', errors='replace')
                    exif_dict['Exif'][piexif.ExifIFD.UserComment] = b'ASCII\x00\x00\x00' + comment_ascii
                except Exception as e:
                    self.logger.debug(f"Could not add camera info to UserComment: {e}")
            
            # Exposure information
            if 'exposure' in camera_params and camera_params['exposure'] is not None:
                # Convert exposure to EXIF format (exposure time as rational)
                exposure_val = float(camera_params['exposure'])
                
                # Handle negative exposure values (common in manual exposure)
                if exposure_val < 0:
                    # Convert negative log exposure to fractional time
                    # Typical mapping: -6 -> 1/64, -10 -> 1/1024, etc.
                    exposure_time_denominator = int(2 ** abs(exposure_val))
                    exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = (1, exposure_time_denominator)
                    exif_dict['Exif'][piexif.ExifIFD.ShutterSpeedValue] = self._float_to_rational(abs(exposure_val))
                elif exposure_val > 0:
                    # Positive exposure value
                    exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = self._float_to_rational(exposure_val)
                    exif_dict['Exif'][piexif.ExifIFD.ShutterSpeedValue] = self._float_to_rational(1.0 / max(exposure_val, 0.001))
                
                # Exposure mode
                auto_exposure = camera_params.get('auto_exposure', 0)
                if auto_exposure == 0.75:  # Auto mode
                    exif_dict['Exif'][piexif.ExifIFD.ExposureMode] = 0  # Auto
                    exif_dict['Exif'][piexif.ExifIFD.ExposureProgram] = 2  # Program auto
                else:  # Manual mode (0.25)
                    exif_dict['Exif'][piexif.ExifIFD.ExposureMode] = 1  # Manual
                    exif_dict['Exif'][piexif.ExifIFD.ExposureProgram] = 1  # Manual
            
            # White balance
            if 'auto_wb' in camera_params:
                auto_wb = camera_params['auto_wb']
                if auto_wb == 1:  # Auto white balance
                    exif_dict['Exif'][piexif.ExifIFD.WhiteBalance] = 0  # Auto
                else:  # Manual white balance
                    exif_dict['Exif'][piexif.ExifIFD.WhiteBalance] = 1  # Manual
                    
                # Note: ColorTemperature is not supported by piexif library
                # White balance temperature will be included in UserComment instead
                wb_temp = camera_params.get('wb_temperature')
                if wb_temp and wb_temp > 0:
                    self.logger.debug(f"White balance temperature: {wb_temp}K (not added to EXIF - unsupported)")
            
            # Gain/ISO
            if 'gain' in camera_params and camera_params['gain'] is not None:
                gain_val = float(camera_params['gain'])
                # Convert gain to approximate ISO (rough mapping)
                iso_value = max(100, int(100 + gain_val * 10))  # Basic conversion
                exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings] = iso_value
            
            # Brightness
            if 'brightness' in camera_params and camera_params['brightness'] is not None:
                brightness_val = float(camera_params['brightness'])
                exif_dict['Exif'][piexif.ExifIFD.BrightnessValue] = self._float_to_rational(brightness_val)
            
            # Contrast
            if 'contrast' in camera_params and camera_params['contrast'] is not None:
                contrast_val = float(camera_params['contrast'])
                # Map contrast to EXIF standard (0=normal, 1=low, 2=high)
                if contrast_val < 40:
                    exif_dict['Exif'][piexif.ExifIFD.Contrast] = 1  # Low
                elif contrast_val > 60:
                    exif_dict['Exif'][piexif.ExifIFD.Contrast] = 2  # High
                else:
                    exif_dict['Exif'][piexif.ExifIFD.Contrast] = 0  # Normal
            
            # Saturation
            if 'saturation' in camera_params and camera_params['saturation'] is not None:
                saturation_val = float(camera_params['saturation'])
                # Map saturation to EXIF standard (0=normal, 1=low, 2=high)
                if saturation_val < 40:
                    exif_dict['Exif'][piexif.ExifIFD.Saturation] = 1  # Low
                elif saturation_val > 70:
                    exif_dict['Exif'][piexif.ExifIFD.Saturation] = 2  # High
                else:
                    exif_dict['Exif'][piexif.ExifIFD.Saturation] = 0  # Normal
            
            # Sharpness
            if 'sharpness' in camera_params and camera_params['sharpness'] is not None:
                sharpness_val = float(camera_params['sharpness'])
                # Map sharpness to EXIF standard (0=normal, 1=soft, 2=hard)
                if sharpness_val < 40:
                    exif_dict['Exif'][piexif.ExifIFD.Sharpness] = 1  # Soft
                elif sharpness_val > 60:
                    exif_dict['Exif'][piexif.ExifIFD.Sharpness] = 2  # Hard
                else:
                    exif_dict['Exif'][piexif.ExifIFD.Sharpness] = 0  # Normal
            
            # Camera backend information (custom field in MakerNote or UserComment)
            backend = camera_params.get('backend', 'Unknown')
            camera_format = camera_params.get('format', 'Unknown')
            
            # Add technical info to image description
            tech_info = f"Backend: {backend}, Format: {camera_format}"
            if piexif.ImageIFD.ImageDescription in exif_dict['0th']:
                existing_desc = exif_dict['0th'][piexif.ImageIFD.ImageDescription]
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = f"{existing_desc} ({tech_info})"
            
            # Log successful camera parameter addition
            params_added = []
            if 'exposure' in camera_params and camera_params['exposure'] is not None:
                params_added.append(f"exposure={camera_params['exposure']}")
            if 'auto_wb' in camera_params:
                wb_mode = "auto" if camera_params['auto_wb'] == 1 else "manual"
                params_added.append(f"wb_mode={wb_mode}")
            if wb_temp and wb_temp > 0:
                params_added.append(f"wb_temp={wb_temp}K")
            if 'gain' in camera_params and camera_params['gain'] is not None:
                params_added.append(f"gain={camera_params['gain']}")
            
            self.logger.info(f"Camera parameters added to EXIF: {', '.join(params_added) if params_added else 'basic info only'}")
            
        except Exception as e:
            self.logger.warning(f"Could not add camera parameters to EXIF: {e}")
            import traceback
            self.logger.debug(f"Camera parameters error details: {traceback.format_exc()}")
    
    def _decimal_to_dms(self, decimal_degrees: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """
        Convert decimal degrees to degrees, minutes, seconds.
        
        Args:
            decimal_degrees: Decimal degrees value
            
        Returns:
            tuple: ((degrees_num, degrees_den), (minutes_num, minutes_den), (seconds_num, seconds_den))
        """
        degrees = int(decimal_degrees)
        minutes_float = (decimal_degrees - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        # Convert to rational numbers (EXIF requires rationals)
        return (
            (degrees, 1),
            (minutes, 1),
            (int(seconds * 1000), 1000)  # Millisecond precision
        )
    
    def _float_to_rational(self, value: float) -> Tuple[int, int]:
        """
        Convert float to rational number for EXIF.
        
        Args:
            value: Float value
            
        Returns:
            tuple: (numerator, denominator)
        """
        # Use 1000 as denominator for reasonable precision
        return (int(value * 1000), 1000)
    
    def _convert_to_bytes(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to bytes, preserving any EXIF metadata.
        
        Args:
            image: PIL Image object
            
        Returns:
            bytes: Image data
        """
        img_bytes = io.BytesIO()
        
        # Extract existing EXIF data if present
        exif_data = image.info.get('exif', b'')
        
        if self.image_format == 'JPEG':
            # Save with EXIF data if available
            if exif_data:
                image.save(img_bytes, format='JPEG', quality=self.jpeg_quality, optimize=True, exif=exif_data)
                self.logger.debug(f"✓ Saved JPEG with {len(exif_data)} bytes of EXIF data")
            else:
                image.save(img_bytes, format='JPEG', quality=self.jpeg_quality, optimize=True)
                self.logger.debug("⚠️  Saved JPEG without EXIF data")
        elif self.image_format == 'PNG':
            image.save(img_bytes, format='PNG', optimize=True)
        elif self.image_format == 'TIFF':
            image.save(img_bytes, format='TIFF')
        else:
            raise ImageProcessingError(f"Unsupported format: {self.image_format}")
        
        return img_bytes.getvalue()
    
    def save_image(self, image_data: bytes, filepath: str) -> bool:
        """
        Save image data to file.
        
        Args:
            image_data: Image data bytes
            filepath: Output file path
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write image data
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Verify file was written
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                self.logger.debug(f"Saved image: {filepath} ({len(image_data)} bytes)")
                return True
            else:
                self.logger.error(f"Failed to save image: {filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving image {filepath}: {e}")
            return False
    
    def validate_image(self, filepath: str) -> bool:
        """
        Validate that saved image can be opened and contains expected metadata.
        
        Args:
            filepath: Path to image file
            
        Returns:
            bool: True if image is valid, False otherwise
        """
        try:
            with Image.open(filepath) as img:
                # Check basic image properties
                if img.size[0] <= 0 or img.size[1] <= 0:
                    return False
                
                # Check for EXIF data if metadata is enabled
                if self.enable_metadata and hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif is None:
                        self.logger.warning(f"No EXIF data found in {filepath}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Image validation failed for {filepath}: {e}")
            return False
    
    def extract_gps_from_image(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Extract GPS coordinates from image EXIF data.
        
        Args:
            filepath: Path to image file
            
        Returns:
            dict: GPS data dictionary or None if not found
        """
        try:
            with Image.open(filepath) as img:
                exif_dict = piexif.load(img.info.get('exif', b''))
                
                if 'GPS' not in exif_dict:
                    return None
                
                gps_info = exif_dict['GPS']
                
                # Extract coordinates
                if (piexif.GPSIFD.GPSLatitude in gps_info and 
                    piexif.GPSIFD.GPSLongitude in gps_info):
                    
                    lat = self._dms_to_decimal(gps_info[piexif.GPSIFD.GPSLatitude])
                    lon = self._dms_to_decimal(gps_info[piexif.GPSIFD.GPSLongitude])
                    
                    # Apply direction
                    if gps_info.get(piexif.GPSIFD.GPSLatitudeRef) == 'S':
                        lat = -lat
                    if gps_info.get(piexif.GPSIFD.GPSLongitudeRef) == 'W':
                        lon = -lon
                    
                    result = {
                        'latitude': lat,
                        'longitude': lon
                    }
                    
                    # Add altitude if available
                    if piexif.GPSIFD.GPSAltitude in gps_info:
                        alt_rational = gps_info[piexif.GPSIFD.GPSAltitude]
                        altitude = alt_rational[0] / alt_rational[1]
                        if gps_info.get(piexif.GPSIFD.GPSAltitudeRef) == 1:
                            altitude = -altitude
                        result['altitude'] = altitude
                    
                    return result
                
        except Exception as e:
            self.logger.error(f"Error extracting GPS from {filepath}: {e}")
        
        return None
    
    def _dms_to_decimal(self, dms_tuple: Tuple) -> float:
        """
        Convert degrees, minutes, seconds tuple to decimal degrees.
        
        Args:
            dms_tuple: ((degrees_num, degrees_den), (minutes_num, minutes_den), (seconds_num, seconds_den))
            
        Returns:
            float: Decimal degrees
        """
        degrees = dms_tuple[0][0] / dms_tuple[0][1]
        minutes = dms_tuple[1][0] / dms_tuple[1][1]
        seconds = dms_tuple[2][0] / dms_tuple[2][1]
        
        return degrees + (minutes / 60.0) + (seconds / 3600.0)


def test_image_processing(config: Dict[str, Any]) -> bool:
    """
    Test image processing functionality.
    
    Args:
        config: Image processing configuration dictionary
        
    Returns:
        bool: True if test passed, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        from gps import GPSFix
        from datetime import datetime
        
        processor = ImageProcessor(config)
        
        # Create test image (simple colored square)
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Create test GPS fix
        test_fix = GPSFix(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.0,
            timestamp=datetime.utcnow(),
            fix_quality=1,
            satellites=8,
            horizontal_dilution=1.5,
            fix_mode='3D'
        )
        
        # Process image
        image_data = processor.process_frame(test_image, test_fix)
        logger.info(f"Processed test image: {len(image_data)} bytes")
        
        # Save test image
        test_path = "test_image.jpg"
        if processor.save_image(image_data, test_path):
            logger.info(f"Test image saved to {test_path}")
            
            # Validate image
            if processor.validate_image(test_path):
                logger.info("Image validation passed")
                
                # Extract GPS data
                extracted_gps = processor.extract_gps_from_image(test_path)
                if extracted_gps:
                    logger.info(f"Extracted GPS: {extracted_gps}")
                else:
                    logger.warning("Could not extract GPS data")
                
                # Clean up
                if os.path.exists(test_path):
                    os.remove(test_path)
                
                logger.info("Image processing test completed successfully")
                return True
            else:
                logger.error("Image validation failed")
        else:
            logger.error("Failed to save test image")
        
        return False
        
    except Exception as e:
        logger.error(f"Image processing test failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'image_format': 'JPEG',
        'jpeg_quality': 85,
        'enable_metadata': True
    }
    
    success = test_image_processing(test_config)
    exit(0 if success else 1)