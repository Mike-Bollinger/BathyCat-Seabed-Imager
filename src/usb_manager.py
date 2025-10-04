#!/usr/bin/env python3
"""
USB Manager for BathyCat Seabed Imager
======================================

Handles automatic USB drive detection, mounting, and permission management
for the BathyCat underwater imaging system.

Author: Mike Bollinger  
Date: October 2025
"""

import subprocess
import logging
import time
import os
import stat
from pathlib import Path
from typing import Optional, Dict, Any, List
import psutil


class USBManager:
    """Manages USB drive operations for BathyCat system."""
    
    def __init__(self, config):
        """Initialize USB manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # USB configuration
        self.target_uuid = getattr(config, 'usb_uuid', 'FCDF-E63E')
        self.target_label = getattr(config, 'usb_label', 'BATHYCAT')
        self.mount_point = getattr(config, 'usb_mount_point', '/media/usb-storage')
        self.bathycat_user = getattr(config, 'system_user', 'bathyimager')
        
        # Mount options
        self.mount_options = [
            'uid=1000',  # Will be updated with actual UID
            'gid=1000',  # Will be updated with actual GID
            'umask=0022',
            'rw',
            'exec'
        ]
        
        # Status tracking
        self.is_mounted = False
        self.mount_verified = False
        self.last_mount_check = 0
        self.mount_check_interval = 30  # Check every 30 seconds
        
        self.logger.info(f"🔧 USB Manager initialized for {self.target_label} (UUID: {self.target_uuid})")
    
    def get_user_ids(self) -> tuple:
        """Get UID and GID for the bathycat user."""
        try:
            import pwd
            user_info = pwd.getpwnam(self.bathycat_user)
            return user_info.pw_uid, user_info.pw_gid
        except KeyError:
            self.logger.error(f"❌ User '{self.bathycat_user}' not found")
            return 1000, 1000  # Default fallback
        except ImportError:
            # Windows fallback
            return 1000, 1000
    
    def run_command(self, cmd: List[str], timeout: int = 30) -> tuple:
        """Run a system command safely."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Command timed out: {' '.join(cmd)}")
            return -1, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"❌ Command failed: {e}")
            return -1, "", str(e)
    
    def find_usb_device(self) -> Optional[str]:
        """Find the USB device by UUID or label."""
        self.logger.debug("🔍 Searching for BathyCat USB device...")
        
        # Try to find by UUID first
        returncode, stdout, stderr = self.run_command(['blkid'])
        if returncode == 0:
            for line in stdout.split('\n'):
                if self.target_uuid in line:
                    # Extract device path (e.g., /dev/sda1)
                    device = line.split(':')[0]
                    self.logger.info(f"✅ Found USB device by UUID: {device}")
                    return device
        
        # Try to find by label as fallback
        returncode, stdout, stderr = self.run_command(['findfs', f'LABEL={self.target_label}'])
        if returncode == 0:
            device = stdout.strip()
            if device:
                self.logger.info(f"✅ Found USB device by label: {device}")
                return device
        
        # List available devices for debugging
        self.logger.debug("📋 Available block devices:")
        returncode, stdout, stderr = self.run_command(['lsblk', '-o', 'NAME,SIZE,FSTYPE,LABEL,UUID'])
        if returncode == 0:
            for line in stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    self.logger.debug(f"   {line}")
        
        return None
    
    def is_device_mounted(self, device: str) -> bool:
        """Check if a device is currently mounted."""
        try:
            with open('/proc/mounts', 'r') as f:
                mounts = f.read()
                return device in mounts or self.mount_point in mounts
        except Exception as e:
            self.logger.error(f"❌ Error checking mount status: {e}")
            return False
    
    def create_mount_point(self) -> bool:
        """Create the mount point directory if it doesn't exist."""
        try:
            Path(self.mount_point).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"📁 Mount point ready: {self.mount_point}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to create mount point {self.mount_point}: {e}")
            return False
    
    def unmount_device(self) -> bool:
        """Safely unmount the USB device."""
        if not os.path.ismount(self.mount_point):
            return True
            
        self.logger.info(f"📤 Unmounting {self.mount_point}...")
        
        # Try graceful unmount first
        returncode, stdout, stderr = self.run_command(['umount', self.mount_point])
        if returncode == 0:
            self.logger.info("✅ Device unmounted successfully")
            self.is_mounted = False
            self.mount_verified = False
            return True
        
        # Try lazy unmount if graceful fails
        self.logger.warning("⚠️ Graceful unmount failed, trying lazy unmount...")
        returncode, stdout, stderr = self.run_command(['umount', '-l', self.mount_point])
        if returncode == 0:
            self.logger.info("✅ Device unmounted (lazy)")
            self.is_mounted = False
            self.mount_verified = False
            return True
        
        self.logger.error(f"❌ Failed to unmount device: {stderr}")
        return False
    
    def mount_device(self, device: str) -> bool:
        """Mount the USB device with proper permissions."""
        if not self.create_mount_point():
            return False
        
        # Get user IDs
        uid, gid = self.get_user_ids()
        mount_opts = [
            f'uid={uid}',
            f'gid={gid}',
            'umask=0022',
            'rw',
            'exec'
        ]
        
        self.logger.info(f"📥 Mounting {device} to {self.mount_point}...")
        
        # Try mounting with exfat first
        cmd = ['mount', '-t', 'exfat', '-o', ','.join(mount_opts), device, self.mount_point]
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode == 0:
            self.logger.info("✅ Successfully mounted with exfat")
            self.is_mounted = True
            return True
        
        # Try auto filesystem detection
        self.logger.debug("🔄 Trying auto filesystem detection...")
        cmd = ['mount', '-o', ','.join(mount_opts), device, self.mount_point]
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode == 0:
            self.logger.info("✅ Successfully mounted with auto-detection")
            self.is_mounted = True
            return True
        
        self.logger.error(f"❌ Failed to mount device: {stderr}")
        return False
    
    def verify_mount_permissions(self) -> bool:
        """Verify mount has proper permissions and directory structure."""
        if not os.path.ismount(self.mount_point):
            self.logger.error(f"❌ {self.mount_point} is not mounted")
            return False
        
        bathycat_dir = Path(self.mount_point) / 'bathycat'
        
        try:
            # Create BathyCat directory structure if needed
            if not bathycat_dir.exists():
                self.logger.info("📁 Creating BathyCat directory structure...")
                bathycat_dir.mkdir(exist_ok=True)
                
                # Create subdirectories
                for subdir in ['images', 'metadata', 'previews', 'logs', 'exports', 'test_images']:
                    (bathycat_dir / subdir).mkdir(exist_ok=True)
                
                self.logger.info("✅ Directory structure created")
            
            # Test write permissions
            test_file = bathycat_dir / f'mount_test_{int(time.time())}'
            try:
                test_file.write_text("BathyCat mount test")
                test_file.unlink()  # Delete test file
                self.logger.info(f"✅ Write permissions verified for {self.bathycat_user}")
                self.mount_verified = True
                return True
                
            except Exception as e:
                self.logger.error(f"❌ Write permission test failed: {e}")
                
                # Try to fix permissions
                try:
                    uid, gid = self.get_user_ids()
                    os.chown(str(bathycat_dir), uid, gid)
                    # Try write test again
                    test_file.write_text("BathyCat mount test")
                    test_file.unlink()
                    self.logger.info("✅ Permissions fixed and verified")
                    self.mount_verified = True
                    return True
                except Exception as fix_error:
                    self.logger.error(f"❌ Could not fix permissions: {fix_error}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Mount verification failed: {e}")
            return False
    
    def get_mount_info(self) -> Dict[str, Any]:
        """Get detailed information about the current mount."""
        info = {
            'mounted': self.is_mounted,
            'verified': self.mount_verified,
            'mount_point': self.mount_point,
            'device': None,
            'filesystem': None,
            'free_space_gb': 0,
            'total_space_gb': 0,
            'usage_percent': 0
        }
        
        try:
            if os.path.ismount(self.mount_point):
                # Get filesystem info
                statvfs = os.statvfs(self.mount_point)
                total_space = statvfs.f_frsize * statvfs.f_blocks
                free_space = statvfs.f_frsize * statvfs.f_available
                
                info.update({
                    'mounted': True,
                    'free_space_gb': free_space / (1024**3),
                    'total_space_gb': total_space / (1024**3),
                    'usage_percent': ((total_space - free_space) / total_space) * 100 if total_space > 0 else 0
                })
                
                # Get mount details from /proc/mounts
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        if self.mount_point in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                info['device'] = parts[0]
                                info['filesystem'] = parts[2]
                            break
                            
        except Exception as e:
            self.logger.debug(f"Could not get mount info: {e}")
        
        return info
    
    def ensure_mounted(self) -> bool:
        """Ensure the USB drive is properly mounted and accessible."""
        current_time = time.time()
        
        # Rate limit mount checks
        if current_time - self.last_mount_check < self.mount_check_interval:
            return self.is_mounted and self.mount_verified
        
        self.last_mount_check = current_time
        
        # Check if already properly mounted and verified
        if self.is_mounted and self.mount_verified and os.path.ismount(self.mount_point):
            return True
        
        self.logger.info("🔍 Checking USB storage status...")
        
        # Find USB device
        device = self.find_usb_device()
        if not device:
            self.logger.error(f"❌ BathyCat USB drive not found (UUID: {self.target_uuid})")
            self.is_mounted = False
            self.mount_verified = False
            return False
        
        # Check if device is already mounted elsewhere
        if self.is_device_mounted(device) and not os.path.ismount(self.mount_point):
            self.logger.warning("⚠️ Device mounted elsewhere, unmounting...")
            if not self.unmount_device():
                return False
        
        # Mount if not mounted
        if not os.path.ismount(self.mount_point):
            if not self.mount_device(device):
                return False
        else:
            self.is_mounted = True
        
        # Verify permissions and structure
        if not self.verify_mount_permissions():
            return False
        
        # Log success
        mount_info = self.get_mount_info()
        self.logger.info(
            f"🎉 USB storage ready: {mount_info['free_space_gb']:.1f}GB free "
            f"({mount_info['usage_percent']:.1f}% used)"
        )
        
        return True
    
    def get_bathycat_path(self) -> Optional[Path]:
        """Get the path to the BathyCat directory on USB storage."""
        if not self.ensure_mounted():
            return None
        return Path(self.mount_point) / 'bathycat'
    
    def is_ready(self) -> bool:
        """Check if USB storage is ready for use."""
        return self.ensure_mounted()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive USB storage status."""
        mount_info = self.get_mount_info()
        bathycat_path = self.get_bathycat_path()
        
        status = {
            'usb_ready': self.is_ready(),
            'mount_info': mount_info,
            'bathycat_path': str(bathycat_path) if bathycat_path else None,
            'target_uuid': self.target_uuid,
            'target_label': self.target_label,
            'mount_point': self.mount_point,
            'last_check': self.last_mount_check
        }
        
        return status