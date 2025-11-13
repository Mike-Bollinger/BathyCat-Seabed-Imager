#!/usr/bin/env python3
"""
Storage Management Module for BathyCat Seabed Imager
===================================================

Handles USB drive management, directory organization, cleanup, and space monitoring.

Features:
- USB storage device detection and mounting
- Directory structure creation and management
- Free space monitoring and alerts
- Automatic cleanup of old files
- File organization by date/time
- Storage health monitoring
"""

import os
import shutil
import logging
import time
import glob
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path


class StorageError(Exception):
    """Custom exception for storage-related errors."""
    pass


class StorageManager:
    """
    Storage management for BathyCat system.
    
    Handles USB drive operations, file organization, and cleanup.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize storage manager with configuration.
        
        Args:
            config: Storage configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Storage settings from config
        self.base_path = config.get('storage_base_path', '/media/usb/bathyimager')
        self.filename_prefix = config.get('filename_prefix', 'bathyimager')
        self.min_free_space_gb = config.get('min_free_space_gb', 5.0)
        self.auto_cleanup_enabled = config.get('auto_cleanup_enabled', True)
        self.cleanup_threshold_gb = config.get('cleanup_threshold_gb', 10.0)
        self.days_to_keep = config.get('days_to_keep', 30)
        
        # Filename generation settings
        self.use_sequence_counter = config.get('use_sequence_counter', False)
        self.filename_format = config.get('filename_format', 'timestamp')  # 'timestamp' or 'counter'
        
        # Debug sequence counter configuration
        raw_config_value = config.get('use_sequence_counter')
        self.logger.info(f"🔢 Storage initialized:")
        self.logger.info(f"   Raw config value: {raw_config_value} (type: {type(raw_config_value)})")
        self.logger.info(f"   Final use_sequence_counter: {self.use_sequence_counter} (type: {type(self.use_sequence_counter)})")
        self.logger.info(f"   Boolean evaluation: {bool(self.use_sequence_counter)}")
        
        # Define structured paths
        self.images_path = os.path.join(self.base_path, 'images')
        
        # Storage state
        self.is_available = False
        self.total_space = 0
        self.free_space = 0
        self.used_space = 0
        self.image_count = 0
        
        # Statistics
        self.files_written = 0
        self.bytes_written = 0
        self.cleanup_count = 0
        
    def initialize(self) -> bool:
        """
        Initialize storage system and check availability.
        
        Returns:
            bool: True if storage is ready, False otherwise
        """
        try:
            self.logger.info(f"Initializing storage at {self.base_path}")
            
            # Check if base path exists or create it
            if not self._ensure_base_path():
                return False
            
            # Update storage statistics
            self._update_storage_stats()
            
            # Check minimum free space
            if not self._check_free_space():
                return False
            
            # Create directory structure (always ensure it exists)
            self._create_directory_structure()
            
            # Verify directory structure integrity
            self._verify_directory_structure()
            
            # Perform cleanup if needed
            if self.auto_cleanup_enabled:
                self._cleanup_old_files()
            
            self.is_available = True
            self.logger.info("Storage initialization successful")
            self.logger.info(f"Free space: {self.free_space / (1024**3):.1f} GB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Storage initialization failed: {e}")
            return False
    
    def _ensure_base_path(self) -> bool:
        """Ensure base storage path exists and is writable."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.base_path, exist_ok=True)
            
            # Check if path is a directory
            if not os.path.isdir(self.base_path):
                raise StorageError(f"Storage path is not a directory: {self.base_path}")
            
            # Check write permissions
            test_file = os.path.join(self.base_path, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception:
                raise StorageError(f"No write permissions for: {self.base_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Base path setup failed: {e}")
            return False
    
    def _update_storage_stats(self) -> None:
        """Update storage space statistics."""
        try:
            stat = shutil.disk_usage(self.base_path)
            self.total_space = stat.total
            self.free_space = stat.free
            self.used_space = stat.used
            
            # Count existing images
            self.image_count = self._count_images()
            
        except Exception as e:
            self.logger.warning(f"Could not update storage stats: {e}")
    
    def _check_free_space(self) -> bool:
        """Check if there's enough free space."""
        min_bytes = self.min_free_space_gb * (1024**3)
        
        if self.free_space < min_bytes:
            self.logger.error(f"Insufficient free space: {self.free_space / (1024**3):.1f} GB < {self.min_free_space_gb} GB")
            return False
        
        return True
    
    def _create_directory_structure(self) -> None:
        """Create organized directory structure: bathyimager/images/YYYYMMDD/."""
        try:
            # Create main bathyimager directory
            os.makedirs(self.base_path, exist_ok=True)
            
            # Create images directory
            os.makedirs(self.images_path, exist_ok=True)
            
            # Create today's date directory
            today = datetime.now()
            today_dir = f"{today.year:04d}{today.month:02d}{today.day:02d}"
            today_path = os.path.join(self.images_path, today_dir)
            os.makedirs(today_path, exist_ok=True)
            
            # Create logs directory (separate from images)
            logs_path = os.path.join(self.base_path, 'logs')
            os.makedirs(logs_path, exist_ok=True)
            
            self.logger.debug(f"Directory structure created: {today_path}")
            
        except Exception as e:
            self.logger.warning(f"Could not create directory structure: {e}")
    
    def _verify_directory_structure(self) -> None:
        """Verify and log the directory structure to confirm it's correct."""
        try:
            if os.path.exists(self.base_path):
                self.logger.info(f"Storage base directory: {self.base_path}")
                
                if os.path.exists(self.images_path):
                    self.logger.info(f"Images directory: {self.images_path}")
                    
                    # List date directories
                    date_dirs = []
                    try:
                        for item in os.listdir(self.images_path):
                            if os.path.isdir(os.path.join(self.images_path, item)) and len(item) == 8 and item.isdigit():
                                date_dirs.append(item)
                    except Exception:
                        pass
                    
                    if date_dirs:
                        date_dirs.sort(reverse=True)  # Newest first
                        self.logger.info(f"Date directories found: {len(date_dirs)} (newest: {date_dirs[0] if date_dirs else 'none'})")
                    else:
                        self.logger.info("No date directories found (will be created as needed)")
                else:
                    self.logger.warning(f"Images directory missing: {self.images_path}")
            else:
                self.logger.warning(f"Storage base directory missing: {self.base_path}")
                
        except Exception as e:
            self.logger.debug(f"Error verifying directory structure: {e}")
    
    def get_image_path(self, timestamp: Optional[datetime] = None, sequence_counter: Optional[int] = None) -> str:
        """
        Generate organized file path for image with improved timestamp accuracy.
        
        Supports two filename formats:
        1. Timestamp format: {prefix}_YYYYMMDD_HHMMSS_mmm.jpg (milliseconds)
        2. Counter format: {prefix}_YYYYMMDD_HHMMSS_NNN.jpg (sequence counter)
        
        Args:
            timestamp: Image timestamp (uses current time if None)
            sequence_counter: Optional sequence counter for unique naming
            
        Returns:
            str: Full path for image file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create date directory: YYYYMMDD format
        date_dir = f"{timestamp.year:04d}{timestamp.month:02d}{timestamp.day:02d}"
        dir_path = os.path.join(self.images_path, date_dir)
        os.makedirs(dir_path, exist_ok=True)
        
        # Generate base filename with new dash-separated format
        # Format: prefix_YYYYMMDD-HHMMSS-mmm_NNNNN.jpg
        date_part = timestamp.strftime('%Y%m%d')
        time_part = timestamp.strftime('%H%M%S')
        milliseconds = int(timestamp.microsecond / 1000)  # Convert microseconds to milliseconds
        
        # Always use the sequence counter from main.py when provided
        if sequence_counter is not None and sequence_counter > 0:
            # Use the sequence counter from the main application (simple enumeration)
            filename = f"{self.filename_prefix}_{date_part}-{time_part}-{milliseconds:03d}_{sequence_counter:05d}.jpg"
            self.logger.debug(f"✅ Using sequence counter {sequence_counter} → {filename}")
        else:
            # Fallback: Generate auto-incrementing counter (shouldn't happen in normal operation)
            counter = self._get_next_file_counter(dir_path, date_part, time_part, milliseconds)
            filename = f"{self.filename_prefix}_{date_part}-{time_part}-{milliseconds:03d}_{counter:05d}.jpg"
            self.logger.warning(f"🔄 Using auto counter {counter} (sequence_counter was {sequence_counter}) → {filename}")
        
        return os.path.join(dir_path, filename)
    
    def _get_next_file_counter(self, dir_path: str, date_part: str, time_part: str, milliseconds: int) -> int:
        """
        Get next available counter for files with same timestamp prefix.
        
        Args:
            dir_path: Directory path
            date_part: Date part (YYYYMMDD)
            time_part: Time part (HHMMSS)  
            milliseconds: Millisecond part
            
        Returns:
            int: Next available counter
        """
        try:
            if not os.path.exists(dir_path):
                return 1
                
            # Pattern: prefix_YYYYMMDD-HHMMSS-mmm_NNNNN.jpg
            pattern = f"{self.filename_prefix}_{date_part}-{time_part}-{milliseconds:03d}_"
            
            max_counter = 0
            for filename in os.listdir(dir_path):
                if filename.startswith(pattern) and filename.endswith('.jpg'):
                    try:
                        # Extract counter: bathyimgtest_20251105-174300-082_00123.jpg
                        counter_part = filename[len(pattern):-4]  # Remove .jpg
                        counter = int(counter_part)
                        max_counter = max(max_counter, counter)
                    except (ValueError, IndexError):
                        continue
                        
            return max_counter + 1
            
        except Exception as e:
            self.logger.debug(f"Error getting next counter: {e}")
            return 1
    
    def save_image(self, image_data: bytes, timestamp: Optional[datetime] = None, sequence_counter: Optional[int] = None) -> Optional[str]:
        """
        Save image to storage with organized naming.
        
        Args:
            image_data: Image data bytes
            timestamp: Image timestamp
            sequence_counter: Optional sequence counter for unique naming
            
        Returns:
            str: Saved file path, or None if save failed
        """
        if not self.is_available:
            self.logger.error("Storage not available")
            return None
        
        try:
            # Check free space before saving
            if not self._check_free_space():
                if self.auto_cleanup_enabled:
                    self._cleanup_old_files()
                    if not self._check_free_space():
                        self.logger.error("Still insufficient space after cleanup")
                        return None
                else:
                    self.logger.error("Insufficient space and cleanup disabled")
                    return None
            
            # Get image path
            filepath = self.get_image_path(timestamp, sequence_counter)
            
            # Write image data
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Verify file was written
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                # Update statistics
                self.files_written += 1
                self.bytes_written += len(image_data)
                self.image_count += 1
                
                self.logger.debug(f"Saved image: {filepath} ({len(image_data)} bytes)")
                return filepath
            else:
                self.logger.error(f"Failed to save image: {filepath}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return None
    
    def _count_images(self) -> int:
        """Count total number of images in storage."""
        try:
            pattern = os.path.join(self.images_path, "**", "*.jpg")
            return len(glob.glob(pattern, recursive=True))
        except Exception:
            return 0
    
    def _cleanup_old_files(self) -> None:
        """Remove old files to free up space."""
        try:
            self.logger.info("Starting cleanup of old files")
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.days_to_keep)
            cleanup_bytes = 0
            cleanup_files = 0
            
            # Walk through image files only (not logs or other files)
            if os.path.exists(self.images_path):
                for root, dirs, files in os.walk(self.images_path):
                    for file in files:
                        if file.endswith('.jpg'):  # Only process image files
                            filepath = os.path.join(root, file)
                            
                            try:
                                # Check file age
                                file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                                
                                if file_time < cutoff_date:
                                    file_size = os.path.getsize(filepath)
                                    os.remove(filepath)
                                    
                                    cleanup_bytes += file_size
                                    cleanup_files += 1
                                    
                                    self.logger.debug(f"Deleted old file: {filepath}")
                                    
                            except Exception as e:
                                self.logger.debug(f"Could not process file {filepath}: {e}")
            
            # Remove empty date directories (but preserve images directory)
            self._remove_empty_dirs()
            
            # Update statistics
            self.cleanup_count += 1
            self._update_storage_stats()
            
            if cleanup_files > 0:
                self.logger.info(f"Cleanup complete: {cleanup_files} files, {cleanup_bytes / (1024**2):.1f} MB freed")
            else:
                self.logger.info("No old files found for cleanup")
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def _remove_empty_dirs(self) -> None:
        """Remove empty date directories but preserve main structure."""
        try:
            if os.path.exists(self.images_path):
                for root, dirs, files in os.walk(self.images_path, topdown=False):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            # Only remove if it's a date directory (YYYYMMDD format) and empty
                            if (len(dir_name) == 8 and dir_name.isdigit() and 
                                not os.listdir(dir_path)):
                                os.rmdir(dir_path)
                                self.logger.debug(f"Removed empty date directory: {dir_path}")
                        except Exception:
                            pass  # Directory not empty or other error
        except Exception as e:
            self.logger.debug(f"Error removing empty directories: {e}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information and statistics.
        
        Returns:
            dict: Storage information dictionary
        """
        self._update_storage_stats()
        
        return {
            'base_path': self.base_path,
            'is_available': self.is_available,
            'total_space_gb': self.total_space / (1024**3),
            'free_space_gb': self.free_space / (1024**3),
            'used_space_gb': self.used_space / (1024**3),
            'free_space_percent': (self.free_space / self.total_space * 100) if self.total_space > 0 else 0,
            'min_free_space_gb': self.min_free_space_gb,
            'image_count': self.image_count,
            'files_written': self.files_written,
            'bytes_written': self.bytes_written,
            'cleanup_count': self.cleanup_count,
            'auto_cleanup_enabled': self.auto_cleanup_enabled,
            'days_to_keep': self.days_to_keep
        }
    
    def is_healthy(self) -> bool:
        """
        Check storage health status.
        
        Returns:
            bool: True if storage is healthy, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            # Update statistics
            self._update_storage_stats()
            
            # Check free space
            if not self._check_free_space():
                return False
            
            # Check if we can write
            test_file = os.path.join(self.base_path, '.health_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('health_test')
                os.remove(test_file)
            except Exception:
                return False
            
            return True
            
        except Exception:
            return False
    
    def force_cleanup(self) -> bool:
        """
        Force cleanup regardless of settings.
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            old_setting = self.auto_cleanup_enabled
            self.auto_cleanup_enabled = True
            
            self._cleanup_old_files()
            
            self.auto_cleanup_enabled = old_setting
            return True
            
        except Exception as e:
            self.logger.error(f"Force cleanup failed: {e}")
            return False
    
    def get_recent_images(self, count: int = 10) -> List[str]:
        """
        Get list of most recent images.
        
        Args:
            count: Number of recent images to return
            
        Returns:
            list: List of image file paths
        """
        try:
            pattern = os.path.join(self.images_path, "**", "*.jpg")
            all_images = glob.glob(pattern, recursive=True)
            
            # Sort by modification time (newest first)
            all_images.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            return all_images[:count]
            
        except Exception as e:
            self.logger.error(f"Error getting recent images: {e}")
            return []
    
    def validate_storage(self) -> Dict[str, bool]:
        """
        Perform comprehensive storage validation.
        
        Returns:
            dict: Validation results
        """
        results = {
            'path_exists': False,
            'path_writable': False,
            'sufficient_space': False,
            'images_accessible': False
        }
        
        try:
            # Check if path exists
            results['path_exists'] = os.path.exists(self.base_path) and os.path.isdir(self.base_path)
            
            # Check write permissions
            if results['path_exists']:
                test_file = os.path.join(self.base_path, '.validation_test')
                try:
                    with open(test_file, 'w') as f:
                        f.write('validation_test')
                    os.remove(test_file)
                    results['path_writable'] = True
                except Exception:
                    pass
            
            # Check free space
            self._update_storage_stats()
            results['sufficient_space'] = self._check_free_space()
            
            # Check if we can access existing images
            try:
                recent_images = self.get_recent_images(1)
                results['images_accessible'] = True
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"Storage validation error: {e}")
        
        return results


def test_storage(config: Dict[str, Any]) -> bool:
    """
    Test storage functionality with given configuration.
    
    Args:
        config: Storage configuration dictionary
        
    Returns:
        bool: True if storage test passed, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        storage = StorageManager(config)
        
        if not storage.initialize():
            logger.error("Storage initialization failed")
            return False
        
        # Test saving a file
        test_data = b"Test image data for BathyCat"
        test_path = storage.save_image(test_data)
        
        if test_path:
            logger.info(f"Test file saved to: {test_path}")
            
            # Verify file exists and has correct size
            if os.path.exists(test_path) and os.path.getsize(test_path) == len(test_data):
                logger.info("File verification passed")
                
                # Clean up test file
                os.remove(test_path)
            else:
                logger.error("File verification failed")
                return False
        else:
            logger.error("Failed to save test file")
            return False
        
        # Get storage info
        info = storage.get_storage_info()
        logger.info(f"Storage info: {info}")
        
        # Test health check
        health = storage.is_healthy()
        logger.info(f"Storage health: {health}")
        
        # Test validation
        validation = storage.validate_storage()
        logger.info(f"Storage validation: {validation}")
        
        logger.info("Storage test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Storage test failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'storage_base_path': '/tmp/bathycat_test',  # Use /tmp for testing
        'min_free_space_gb': 1.0,  # Lower requirement for testing
        'auto_cleanup_enabled': True,
        'cleanup_threshold_gb': 2.0,
        'days_to_keep': 7
    }
    
    success = test_storage(test_config)
    exit(0 if success else 1)