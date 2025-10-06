#!/usr/bin/env python3
"""
Image Processor for BathyCat Seabed Imager
=========================================

Handles image processing, metadata embedding, and file operations
for captured seabed images.

Author: Mike Bollinger
Date: August 2025
"""

import asyncio
import cv2
import json
import logging
import numpy as np
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import piexif


class ImageProcessor:
    """Processes and manages captured images."""
    
    def __init__(self, config):
        """Initialize image processor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Processing settings
        self.output_format = config.image_format
        self.jpeg_quality = config.jpeg_quality
        self.enable_metadata = config.enable_metadata
        self.enable_preview = config.enable_preview
        
        # Storage paths
        self.base_path = Path(config.storage_base_path)
        self.images_path = self.base_path / "images"
        self.metadata_path = self.base_path / "metadata"
        
        # Statistics
        self.processed_count = 0
        self.processing_times = []
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories."""
        try:
            self.images_path.mkdir(parents=True, exist_ok=True)
            if self.enable_metadata:
                self.metadata_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Storage directories created at {self.base_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}")
            raise
    
    async def process_image(self, image_data: np.ndarray, gps_data: Dict[str, Any], 
                          capture_time: float) -> Optional[str]:
        """Process and save an image with metadata."""
        try:
            self.logger.debug(f"💾 IMG_PROC_1: Starting, image_shape={getattr(image_data, 'shape', 'NO_SHAPE')}")
            start_time = asyncio.get_event_loop().time()
            
            # Generate filename based on timestamp
            dt = datetime.fromtimestamp(capture_time, timezone.utc)
            filename_base = dt.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            
            # Create session directory if needed
            session_dir = dt.strftime("%Y%m%d_%H")
            session_images_path = self.images_path / session_dir
            session_images_path.mkdir(exist_ok=True)
            
            # Process and save main image
            image_path = await self._save_image(
                image_data, session_images_path, filename_base, gps_data, capture_time
            )
            
            if not image_path:
                return None
            
            # Save metadata if enabled
            if self.enable_metadata:
                session_metadata_path = self.metadata_path / session_dir
                session_metadata_path.mkdir(exist_ok=True)
                await self._save_metadata(
                    session_metadata_path, filename_base, gps_data, capture_time, image_path
                )
            
            # Preview generation disabled for performance
            
            # Update statistics
            processing_time = asyncio.get_event_loop().time() - start_time
            self.processing_times.append(processing_time)
            
            # Keep only last 100 measurements
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            
            self.processed_count += 1
            
            # Log performance occasionally
            if self.processed_count % 100 == 0:
                avg_time = sum(self.processing_times) / len(self.processing_times)
                self.logger.info(f"Processed {self.processed_count} images, avg {avg_time*1000:.1f}ms")
            
            return str(image_path)
            
        except Exception as e:
            self.logger.error(f"🚨 IMG_PROCESSING_ERROR: {e}")
            import traceback
            self.logger.error(f"🔍 IMG_PROC_TRACEBACK: {traceback.format_exc()}")
            return None
    
    async def _save_image(self, image_data: np.ndarray, output_path: Path, 
                         filename_base: str, gps_data: Dict[str, Any], 
                         capture_time: float) -> Optional[Path]:
        """Save the main image with embedded metadata."""
        try:
            # Determine file extension
            if self.output_format.upper() == 'JPEG':
                ext = '.jpg'
            elif self.output_format.upper() == 'PNG':
                ext = '.png'
            else:
                ext = '.jpg'  # Default to JPEG
            
            image_path = output_path / f"{filename_base}{ext}"
            
            if self.output_format.upper() == 'JPEG':
                # Save as JPEG with embedded EXIF
                await self._save_jpeg_with_exif(image_data, image_path, gps_data, capture_time)
            else:
                # Save as PNG
                cv2.imwrite(str(image_path), image_data)
            
            return image_path
            
        except Exception as e:
            self.logger.error(f"Failed to save image: {e}")
            return None
    
    async def _save_jpeg_with_exif(self, image_data: np.ndarray, image_path: Path,
                                 gps_data: Dict[str, Any], capture_time: float):
        """Save JPEG with embedded EXIF data including GPS coordinates."""
        try:
            # Convert BGR to RGB for PIL
            rgb_image = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # Create EXIF data
            exif_dict = self._create_exif_data(gps_data, capture_time, image_data.shape)
            exif_bytes = piexif.dump(exif_dict)
            
            # Save with EXIF
            pil_image.save(
                str(image_path),
                "JPEG",
                quality=self.jpeg_quality,
                exif=exif_bytes
            )
            
        except Exception as e:
            # Fallback to OpenCV save without EXIF
            self.logger.warning(f"EXIF embedding failed, saving without metadata: {e}")
            cv2.imwrite(str(image_path), image_data, 
                       [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
    
    def _create_exif_data(self, gps_data: Dict[str, Any], capture_time: float, 
                         image_shape: Tuple[int, int, int]) -> Dict:
        """Create EXIF data dictionary."""
        # Basic EXIF data
        dt = datetime.fromtimestamp(capture_time, timezone.utc)
        
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: "BathyCat Systems",
                piexif.ImageIFD.Model: "Seabed Imager v1.0",
                piexif.ImageIFD.Software: "BathyCat Imager",
                piexif.ImageIFD.DateTime: dt.strftime("%Y:%m:%d %H:%M:%S"),
                piexif.ImageIFD.ImageWidth: image_shape[1],
                piexif.ImageIFD.ImageLength: image_shape[0],
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: dt.strftime("%Y:%m:%d %H:%M:%S"),
                piexif.ExifIFD.DateTimeDigitized: dt.strftime("%Y:%m:%d %H:%M:%S"),
                piexif.ExifIFD.SubSecTime: str(int((capture_time % 1) * 1000)),
            },
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        
        # Add GPS data if available
        if (gps_data.get('latitude') is not None and 
            gps_data.get('longitude') is not None):
            
            lat = gps_data['latitude']
            lon = gps_data['longitude']
            
            # Convert decimal degrees to degrees, minutes, seconds
            lat_deg, lat_min, lat_sec = self._decimal_to_dms(abs(lat))
            lon_deg, lon_min, lon_sec = self._decimal_to_dms(abs(lon))
            
            exif_dict["GPS"] = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
                piexif.GPSIFD.GPSLatitude: [(lat_deg, 1), (lat_min, 1), (int(lat_sec * 1000), 1000)],
                piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
                piexif.GPSIFD.GPSLongitude: [(lon_deg, 1), (lon_min, 1), (int(lon_sec * 1000), 1000)],
                piexif.GPSIFD.GPSTimeStamp: [
                    (dt.hour, 1), (dt.minute, 1), (int(dt.second * 1000), 1000)
                ],
                piexif.GPSIFD.GPSDateStamp: dt.strftime("%Y:%m:%d"),
            }
            
            # Add altitude if available
            if gps_data.get('altitude') is not None:
                alt = gps_data['altitude']
                exif_dict["GPS"][piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 1000), 1000)
                exif_dict["GPS"][piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
        
        return exif_dict
    
    def _decimal_to_dms(self, decimal_degrees: float) -> Tuple[int, int, float]:
        """Convert decimal degrees to degrees, minutes, seconds."""
        degrees = int(decimal_degrees)
        minutes_float = (decimal_degrees - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        return degrees, minutes, seconds
    
    async def _save_metadata(self, output_path: Path, filename_base: str,
                           gps_data: Dict[str, Any], capture_time: float,
                           image_path: Path):
        """Save metadata as JSON file."""
        try:
            metadata = {
                'image_path': str(image_path),
                'capture_time': capture_time,
                'capture_time_iso': datetime.fromtimestamp(capture_time, timezone.utc).isoformat(),
                'gps_data': gps_data,
                'processing_info': {
                    'processed_count': self.processed_count,
                    'processor_version': '1.0',
                    'format': self.output_format,
                    'jpeg_quality': self.jpeg_quality if self.output_format.upper() == 'JPEG' else None
                }
            }
            
            metadata_path = output_path / f"{filename_base}.json"
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
    

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get image processing statistics."""
        stats = {
            'processed_count': self.processed_count,
            'base_path': str(self.base_path),
        }
        
        if self.processing_times:
            times = self.processing_times
            stats.update({
                'avg_processing_time_ms': sum(times) / len(times) * 1000,
                'min_processing_time_ms': min(times) * 1000,
                'max_processing_time_ms': max(times) * 1000,
            })
        
        return stats
    
    async def cleanup_old_files(self, days_to_keep: int = 7):
        """Clean up old image files to free space."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = 0
            freed_space = 0
            
            # Clean up images
            for session_dir in self.images_path.iterdir():
                if session_dir.is_dir():
                    try:
                        # Parse session directory name (YYYYMMDD_HH format)
                        session_date = datetime.strptime(session_dir.name[:8], "%Y%m%d")
                        
                        if session_date < cutoff_time:
                            # Calculate space before deletion
                            dir_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                            
                            # Remove directory
                            import shutil
                            shutil.rmtree(session_dir)
                            
                            deleted_count += len(list(session_dir.rglob('*.jpg')))
                            freed_space += dir_size
                            
                            self.logger.info(f"Cleaned up session {session_dir.name}")
                            
                    except ValueError:
                        # Skip directories that don't match expected format
                        continue
            
            if deleted_count > 0:
                self.logger.info(
                    f"Cleanup complete: {deleted_count} files, "
                    f"{freed_space / (1024*1024):.1f}MB freed"
                )
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    async def shutdown(self):
        """Shutdown image processor."""
        self.logger.info("Shutting down image processor...")
        
        try:
            # Log final statistics
            stats = self.get_processing_stats()
            self.logger.info(
                f"Image processor stats: {stats['processed_count']} images processed"
            )
            
            if 'avg_processing_time_ms' in stats:
                self.logger.info(
                    f"Average processing time: {stats['avg_processing_time_ms']:.1f}ms"
                )
            
            self.logger.info("Image processor shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Image processor shutdown error: {e}")


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass
