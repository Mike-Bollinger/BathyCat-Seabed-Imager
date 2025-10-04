#!/usr/bin/env python3
"""
Storage Manager for BathyCat Seabed Imager
=========================================

Manages storage operations, disk space monitoring, and data organization
for the underwater imaging system.

Author: Mike Bollinger
Date: August 2025
"""

import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import psutil
from usb_manager import USBManager


class StorageManager:
    """Manages storage operations and disk space."""
    
    def __init__(self, config):
        """Initialize storage manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize USB manager for automatic mounting
        self.usb_manager = USBManager(config)
        
        # Storage settings - will be updated after USB mount
        self._base_path_configured = False
        self.min_free_space_gb = config.min_free_space_gb
        self.auto_cleanup_enabled = config.auto_cleanup_enabled
        self.cleanup_threshold_gb = config.cleanup_threshold_gb
        self.days_to_keep = config.days_to_keep
        
        # Monitoring
        self.last_space_check = 0
        self.space_check_interval = 60  # Check every minute
        self.total_images_stored = 0
        self.total_space_used = 0
        
        # Directory structure - will be set after USB mount verification
        self.directories = {}
        self.base_path = None
        
        self.logger.info("💾 Storage Manager initialized with USB auto-mounting")
    
    def _ensure_usb_mounted_and_configured(self) -> bool:
        """Ensure USB is mounted and configure storage paths."""
        if self._base_path_configured and self.base_path and self.base_path.exists():
            return True
        
        self.logger.info("🔍 Ensuring USB storage is mounted and configured...")
        
        # Ensure USB is mounted
        if not self.usb_manager.ensure_mounted():
            self.logger.error("❌ Failed to mount USB storage")
            return False
        
        # Get BathyCat path on USB
        bathycat_path = self.usb_manager.get_bathycat_path()
        if not bathycat_path:
            self.logger.error("❌ Could not get BathyCat path on USB storage")
            return False
        
        # Configure storage paths
        self.base_path = bathycat_path
        self.directories = {
            'images': self.base_path / 'images',
            'metadata': self.base_path / 'metadata',
            'previews': self.base_path / 'previews',
            'logs': self.base_path / 'logs',
            'exports': self.base_path / 'exports'
        }
        
        self._base_path_configured = True
        self.logger.info(f"✅ Storage configured at {self.base_path}")
        return True
    
    async def initialize(self) -> bool:
        """Initialize storage system."""
        try:
            # First ensure USB is mounted and paths are configured
            if not self._ensure_usb_mounted_and_configured():
                return False
            
            self.logger.info(f"Initializing storage at {self.base_path}")
            
            # Create directory structure
            self._create_directory_structure()
            
            # Check storage availability
            if not self._check_storage_availability():
                return False
            
            # Verify write permissions
            if not await self._test_write_permissions():
                return False
            
            # Calculate current usage
            await self._calculate_current_usage()
            
            # Log storage information
            self._log_storage_info()
            
            self.logger.info("Storage initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Storage initialization failed: {e}")
            return False
    
    def _create_directory_structure(self):
        """Create necessary directory structure."""
        try:
            for name, path in self.directories.items():
                path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created directory: {path}")
            
            # Create additional subdirectories
            (self.directories['logs'] / 'archive').mkdir(exist_ok=True)
            (self.directories['exports'] / 'processed').mkdir(exist_ok=True)
            
        except Exception as e:
            self.logger.error(f"Failed to create directory structure: {e}")
            raise
    
    def _check_storage_availability(self) -> bool:
        """Check if storage device is available and has sufficient space."""
        try:
            if not self.base_path.exists():
                self.logger.error(f"Storage path does not exist: {self.base_path}")
                
                # Try to detect and suggest USB storage paths
                usb_paths = self._detect_usb_storage_paths()
                if usb_paths:
                    self.logger.info(f"Detected USB storage at: {usb_paths}")
                    self.logger.info(f"Consider updating storage_base_path to one of: {usb_paths}")
                else:
                    self.logger.warning("No USB storage detected. Is the USB drive connected and mounted?")
                
                return False
                
            # Check available space
            free_space_gb = self.get_free_space_gb()
            
            if free_space_gb < self.min_free_space_gb:
                self.logger.error(
                    f"Insufficient storage space: {free_space_gb:.1f}GB available, "
                    f"{self.min_free_space_gb}GB required"
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Storage availability check failed: {e}")
            return False
    
    def _detect_usb_storage_paths(self) -> List[str]:
        """Detect potential USB storage mount points."""
        potential_paths = []
        
        # Common USB mount points
        common_mounts = [
            '/media/usb-storage',
            '/media/bathyimager', 
            '/media/pi',
            '/mnt/usb',
            '/mnt/bathycat'
        ]
        
        for mount_point in common_mounts:
            if Path(mount_point).exists():
                potential_paths.append(mount_point)
        
        # Check /media for any mounted devices
        try:
            media_path = Path('/media')
            if media_path.exists():
                for user_dir in media_path.iterdir():
                    if user_dir.is_dir():
                        for device_dir in user_dir.iterdir():
                            if device_dir.is_dir():
                                potential_paths.append(str(device_dir))
        except Exception:
            pass
        
        # Check mounted filesystems for USB devices
        try:
            import subprocess
            result = subprocess.run(['df', '-h'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if '/dev/sd' in line and '/media' in line:
                    parts = line.split()
                    if len(parts) > 5:
                        mount_point = parts[-1]
                        if mount_point not in potential_paths:
                            potential_paths.append(mount_point)
        except Exception:
            pass
        
        return potential_paths
    
    async def _test_write_permissions(self) -> bool:
        """Test write permissions to storage locations."""
        try:
            test_file = self.base_path / '.write_test'
            
            # Write test file
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Read test file
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Clean up
            test_file.unlink()
            
            if content != 'test':
                self.logger.error("Write permission test failed: content mismatch")
                return False
            
            self.logger.debug("Write permissions verified")
            return True
            
        except Exception as e:
            self.logger.error(f"Write permission test failed: {e}")
            return False
    
    async def _calculate_current_usage(self):
        """Calculate current storage usage."""
        try:
            self.total_space_used = 0
            self.total_images_stored = 0
            
            for directory in self.directories.values():
                if directory.exists():
                    for file_path in directory.rglob('*'):
                        if file_path.is_file():
                            self.total_space_used += file_path.stat().st_size
                            
                            # Count image files
                            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                                self.total_images_stored += 1
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate storage usage: {e}")
    
    def _log_storage_info(self):
        """Log current storage information."""
        try:
            free_space = self.get_free_space_gb()
            total_space = self.get_total_space_gb()
            used_space = self.total_space_used / (1024**3)
            
            self.logger.info(
                f"Storage info: {used_space:.1f}GB used, "
                f"{free_space:.1f}GB free, {total_space:.1f}GB total"
            )
            
            if self.total_images_stored > 0:
                self.logger.info(f"Current images stored: {self.total_images_stored}")
                
        except Exception as e:
            self.logger.warning(f"Failed to log storage info: {e}")
    
    def get_free_space_gb(self) -> float:
        """Get free space in GB."""
        try:
            # Ensure USB is mounted before checking space
            if not self._ensure_usb_mounted_and_configured():
                self.logger.warning("USB not mounted, returning 0 free space")
                return 0.0
                
            statvfs = shutil.disk_usage(self.base_path)
            return statvfs.free / (1024**3)
        except Exception as e:
            self.logger.error(f"Failed to get free space: {e}")
            return 0.0
    
    def get_total_space_gb(self) -> float:
        """Get total space in GB."""
        try:
            statvfs = shutil.disk_usage(self.base_path)
            return statvfs.total / (1024**3)
        except Exception as e:
            self.logger.error(f"Failed to get total space: {e}")
            return 0.0
    
    def get_used_space_gb(self) -> float:
        """Get used space in GB."""
        try:
            statvfs = shutil.disk_usage(self.base_path)
            return (statvfs.total - statvfs.free) / (1024**3)
        except Exception as e:
            self.logger.error(f"Failed to get used space: {e}")
            return 0.0
    
    async def check_storage_health(self) -> Dict[str, Any]:
        """Check storage health and return status."""
        try:
            # Ensure USB is mounted before checking health
            if not self._ensure_usb_mounted_and_configured():
                return {
                    'status': 'error',
                    'free_space_gb': 0.0,
                    'total_space_gb': 0.0,
                    'used_space_gb': 0.0,
                    'percentage_used': 100.0,
                    'warning_level': 'critical',
                    'message': 'USB storage not mounted'
                }
            
            current_time = asyncio.get_event_loop().time()
            
            # Only check if enough time has passed
            if current_time - self.last_space_check < self.space_check_interval:
                return self._get_cached_health_status()
            
            self.last_space_check = current_time
            
            free_space = self.get_free_space_gb()
            total_space = self.get_total_space_gb()
            used_space = self.get_used_space_gb()
            
            # Calculate percentages
            used_percentage = (used_space / total_space * 100) if total_space > 0 else 0
            
            # Determine status
            status = "healthy"
            warnings = []
            
            if free_space < self.min_free_space_gb:
                status = "critical"
                warnings.append(f"Low disk space: {free_space:.1f}GB remaining")
            
            elif free_space < self.cleanup_threshold_gb:
                status = "warning"
                warnings.append(f"Disk space getting low: {free_space:.1f}GB remaining")
            
            # Check for auto-cleanup trigger
            if (self.auto_cleanup_enabled and 
                free_space < self.cleanup_threshold_gb):
                warnings.append("Auto-cleanup will be triggered")
            
            health_status = {
                'status': status,
                'free_space_gb': free_space,
                'used_space_gb': used_space,
                'total_space_gb': total_space,
                'used_percentage': used_percentage,
                'warnings': warnings,
                'images_stored': self.total_images_stored,
                'last_check': datetime.now().isoformat()
            }
            
            # Cache the status
            self._cached_health_status = health_status
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Storage health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def _get_cached_health_status(self) -> Dict[str, Any]:
        """Get cached health status."""
        return getattr(self, '_cached_health_status', {
            'status': 'unknown',
            'last_check': 'never'
        })
    
    async def auto_cleanup_if_needed(self) -> bool:
        """Perform automatic cleanup if storage is low."""
        if not self.auto_cleanup_enabled:
            return False
        
        try:
            free_space = self.get_free_space_gb()
            
            if free_space < self.cleanup_threshold_gb:
                self.logger.info(
                    f"Auto-cleanup triggered: {free_space:.1f}GB < {self.cleanup_threshold_gb:.1f}GB"
                )
                
                cleaned_files, freed_space = await self.cleanup_old_data()
                
                if cleaned_files > 0:
                    self.logger.info(
                        f"Auto-cleanup complete: {cleaned_files} files, "
                        f"{freed_space / (1024**3):.1f}GB freed"
                    )
                    return True
                
        except Exception as e:
            self.logger.error(f"Auto-cleanup failed: {e}")
        
        return False
    
    async def cleanup_old_data(self, days_override: Optional[int] = None) -> tuple[int, int]:
        """Clean up old data files."""
        days_to_keep = days_override or self.days_to_keep
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        cleaned_files = 0
        freed_space = 0
        
        try:
            self.logger.info(f"Cleaning up data older than {days_to_keep} days...")
            
            # Clean up session directories based on date
            for images_dir in self.directories['images'].iterdir():
                if images_dir.is_dir():
                    try:
                        # Parse directory name (YYYYMMDD_HH format)
                        dir_date_str = images_dir.name[:8]
                        dir_date = datetime.strptime(dir_date_str, "%Y%m%d")
                        
                        if dir_date < cutoff_date:
                            # Calculate size before deletion
                            dir_size = await self._calculate_directory_size(images_dir)
                            file_count = len(list(images_dir.rglob('*')))
                            
                            # Remove directory
                            shutil.rmtree(images_dir)
                            
                            # Clean up corresponding metadata and previews
                            metadata_dir = self.directories['metadata'] / images_dir.name
                            if metadata_dir.exists():
                                shutil.rmtree(metadata_dir)
                            
                            previews_dir = self.directories['previews'] / images_dir.name
                            if previews_dir.exists():
                                shutil.rmtree(previews_dir)
                            
                            cleaned_files += file_count
                            freed_space += dir_size
                            
                            self.logger.info(f"Cleaned up session: {images_dir.name}")
                            
                    except ValueError:
                        # Skip directories that don't match expected format
                        continue
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up {images_dir}: {e}")
            
            # Update usage statistics
            await self._calculate_current_usage()
            
            return cleaned_files, freed_space
            
        except Exception as e:
            self.logger.error(f"Cleanup operation failed: {e}")
            return 0, 0
    
    async def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of a directory."""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"Failed to calculate size for {directory}: {e}")
        
        return total_size
    
    def get_session_directories(self) -> List[Dict[str, Any]]:
        """Get list of session directories with information."""
        sessions = []
        
        try:
            for session_dir in self.directories['images'].iterdir():
                if session_dir.is_dir():
                    try:
                        # Parse session info
                        session_name = session_dir.name
                        date_str = session_name[:8]
                        session_date = datetime.strptime(date_str, "%Y%m%d")
                        
                        # Count files and calculate size
                        file_count = len(list(session_dir.rglob('*.jpg')))
                        dir_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                        
                        sessions.append({
                            'name': session_name,
                            'date': session_date.isoformat(),
                            'file_count': file_count,
                            'size_bytes': dir_size,
                            'size_mb': dir_size / (1024**2),
                            'path': str(session_dir)
                        })
                        
                    except ValueError:
                        # Skip invalid directory names
                        continue
            
            # Sort by date (newest first)
            sessions.sort(key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to get session directories: {e}")
        
        return sessions
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        try:
            sessions = self.get_session_directories()
            
            stats = {
                'base_path': str(self.base_path),
                'free_space_gb': self.get_free_space_gb(),
                'used_space_gb': self.get_used_space_gb(),
                'total_space_gb': self.get_total_space_gb(),
                'total_images': self.total_images_stored,
                'session_count': len(sessions),
                'oldest_session': sessions[-1]['date'] if sessions else None,
                'newest_session': sessions[0]['date'] if sessions else None,
                'auto_cleanup_enabled': self.auto_cleanup_enabled,
                'cleanup_threshold_gb': self.cleanup_threshold_gb,
                'min_free_space_gb': self.min_free_space_gb
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    async def export_session_data(self, session_name: str, export_path: Optional[Path] = None) -> Optional[Path]:
        """Export a session's data to a compressed archive."""
        try:
            session_dir = self.directories['images'] / session_name
            if not session_dir.exists():
                self.logger.error(f"Session not found: {session_name}")
                return None
            
            if export_path is None:
                export_path = self.directories['exports'] / f"{session_name}.tar.gz"
            
            self.logger.info(f"Exporting session {session_name} to {export_path}")
            
            # Create compressed archive
            import tarfile
            
            with tarfile.open(export_path, 'w:gz') as tar:
                # Add images
                tar.add(session_dir, arcname=f"{session_name}/images")
                
                # Add metadata if exists
                metadata_dir = self.directories['metadata'] / session_name
                if metadata_dir.exists():
                    tar.add(metadata_dir, arcname=f"{session_name}/metadata")
                
                # Add previews if exists
                previews_dir = self.directories['previews'] / session_name
                if previews_dir.exists():
                    tar.add(previews_dir, arcname=f"{session_name}/previews")
            
            self.logger.info(f"Export complete: {export_path}")
            return export_path
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return None
    
    async def shutdown(self):
        """Shutdown storage manager."""
        self.logger.info("Shutting down storage manager...")
        
        try:
            # Final storage report
            stats = self.get_storage_stats()
            self.logger.info(
                f"Final storage stats: {stats.get('total_images', 0)} images, "
                f"{stats.get('used_space_gb', 0):.1f}GB used, "
                f"{stats.get('free_space_gb', 0):.1f}GB free"
            )
            
            self.logger.info("Storage manager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Storage manager shutdown error: {e}")


class StorageError(Exception):
    """Custom exception for storage-related errors."""
    pass
