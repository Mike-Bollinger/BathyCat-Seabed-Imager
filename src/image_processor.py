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
                     timestamp: Optional[datetime] = None) -> bytes:
        """
        Process camera frame and add metadata.
        
        Args:
            frame: Camera frame as numpy array (BGR format from OpenCV)
            gps_fix: GPS fix data for geotagging
            timestamp: Image timestamp (uses current time if None)
            
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
                image = self._add_metadata(image, gps_fix, timestamp)
            
            # Convert to bytes
            image_bytes = self._convert_to_bytes(image)
            
            self.logger.debug(f"Processed image: {len(image_bytes)} bytes, format: {self.image_format}")
            return image_bytes
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            raise ImageProcessingError(f"Frame processing failed: {e}")
    
    def _add_metadata(self, image: Image.Image, gps_fix: Optional[GPSFix], 
                     timestamp: datetime) -> Image.Image:
        """
        Add EXIF metadata to image.
        
        Args:
            image: PIL Image object
            gps_fix: GPS fix data
            timestamp: Image timestamp
            
        Returns:
            Image.Image: Image with metadata
        """
        try:
            # Get existing EXIF data or create new
            exif_dict = piexif.load(image.info.get('exif', b''))
            
            # Add timestamp
            self._add_timestamp_metadata(exif_dict, timestamp)
            
            # Add GPS data if available
            if gps_fix and gps_fix.is_valid:
                self._add_gps_metadata(exif_dict, gps_fix)
            
            # Add camera/software information
            self._add_software_metadata(exif_dict)
            
            # Convert EXIF dict to bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Create new image with EXIF data
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='JPEG', exif=exif_bytes)
            img_bytes.seek(0)
            
            return Image.open(img_bytes)
            
        except Exception as e:
            self.logger.warning(f"Could not add metadata: {e}")
            return image
    
    def _add_timestamp_metadata(self, exif_dict: Dict, timestamp: datetime) -> None:
        """Add timestamp to EXIF metadata."""
        # Format timestamp for EXIF
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
    
    def _add_software_metadata(self, exif_dict: Dict) -> None:
        """Add software/camera information to EXIF metadata."""
        try:
            # Software information
            exif_dict['0th'][piexif.ImageIFD.Software] = "BathyCat Seabed Imager v1.0"
            exif_dict['0th'][piexif.ImageIFD.Artist] = "BathyCat Project"
            
            # Camera information (if not already present)
            if piexif.ImageIFD.Make not in exif_dict['0th']:
                exif_dict['0th'][piexif.ImageIFD.Make] = "BathyCat"
            if piexif.ImageIFD.Model not in exif_dict['0th']:
                exif_dict['0th'][piexif.ImageIFD.Model] = "Seabed Imager"
            
            # Image description
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = "Autonomous seabed imagery"
            
        except Exception as e:
            self.logger.debug(f"Could not add software metadata: {e}")
    
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
        Convert PIL Image to bytes.
        
        Args:
            image: PIL Image object
            
        Returns:
            bytes: Image data
        """
        img_bytes = io.BytesIO()
        
        if self.image_format == 'JPEG':
            image.save(img_bytes, format='JPEG', quality=self.jpeg_quality, optimize=True)
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