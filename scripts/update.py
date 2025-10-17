#!/usr/bin/env python3
"""
Update System for BathyCat Seabed Imager
=======================================

Handles automatic updates from GitHub repository including version checking,
dependency management, configuration updates, and service restart.

Features:
- GitHub repository integration
- Version comparison and management
- Safe update process with rollback
- Configuration file preservation
- Service lifecycle management
- Dependency update handling
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import logging
import argparse
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path


class UpdateError(Exception):
    """Custom exception for update-related errors."""
    pass


class BathyImagerUpdater:
    """
    Update manager for BathyImager system.
    
    Handles safe updates from GitHub with rollback capability.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize updater with configuration.
        
        Args:
            config: Update configuration dictionary
        """
        self.config = config
        self.logger = self._setup_logging()
        
        # Update settings
        self.github_repo = config.get('github_repo', 'Mike-Bollinger/BathyImager-Seabed-Imager')
        self.github_branch = config.get('github_branch', 'main')
        self.install_dir = config.get('install_dir', '/opt/bathyimager')
        self.config_dir = config.get('config_dir', '/etc/bathyimager')
        self.backup_dir = config.get('backup_dir', '/opt/bathyimager/backups')
        self.service_name = config.get('service_name', 'bathyimager')
        self.python_env = config.get('python_env', '/opt/bathyimager/venv')
        
        # Version information
        self.current_version = None
        self.latest_version = None
        
        # Paths
        self.version_file = os.path.join(self.install_dir, 'VERSION')
        self.update_lock = os.path.join(self.install_dir, '.update_lock')
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for updater."""
        logger = logging.getLogger('bathyimager_updater')
        logger.setLevel(logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def check_prerequisites(self) -> bool:
        """
        Check system prerequisites for update.
        
        Returns:
            bool: True if prerequisites met, False otherwise
        """
        try:
            # Check if running as root/sudo
            if os.geteuid() != 0:
                self.logger.error("Update must be run with sudo privileges")
                return False
            
            # Check for git
            if not shutil.which('git'):
                self.logger.error("Git is not installed")
                return False
            
            # Check internet connectivity
            if not self._check_internet():
                self.logger.error("No internet connection available")
                return False
            
            # Check if update already in progress
            if os.path.exists(self.update_lock):
                self.logger.error("Update already in progress")
                return False
            
            # Check disk space (need at least 100MB)
            if not self._check_disk_space():
                self.logger.error("Insufficient disk space for update")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Prerequisites check failed: {e}")
            return False
    
    def _check_internet(self) -> bool:
        """Check internet connectivity."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            stat = shutil.disk_usage(self.install_dir)
            free_mb = stat.free / (1024 * 1024)
            return free_mb > 100  # Need at least 100MB
        except Exception:
            return False
    
    def get_current_version(self) -> Optional[str]:
        """
        Get currently installed version.
        
        Returns:
            str: Current version or None if not found
        """
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    version = f.read().strip()
                    self.logger.info(f"Current version: {version}")
                    return version
            else:
                self.logger.warning("Version file not found")
                return None
        except Exception as e:
            self.logger.error(f"Error reading version file: {e}")
            return None
    
    def get_latest_version(self) -> Optional[str]:
        """
        Get latest version from GitHub.
        
        Returns:
            str: Latest version or None if error
        """
        try:
            # Get latest release tag from GitHub API
            cmd = [
                'curl', '-s', '--connect-timeout', '10',
                f'https://api.github.com/repos/{self.github_repo}/releases/latest'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    release_data = json.loads(result.stdout)
                    version = release_data.get('tag_name', '').replace('v', '')
                    if version:
                        self.logger.info(f"Latest version: {version}")
                        return version
                except json.JSONDecodeError:
                    pass
            
            # Fallback: check commit hash
            cmd = [
                'git', 'ls-remote', 
                f'https://github.com/{self.github_repo}.git',
                f'refs/heads/{self.github_branch}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                commit_hash = result.stdout.strip().split()[0][:8]
                version = f"git-{commit_hash}"
                self.logger.info(f"Latest commit: {version}")
                return version
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest version: {e}")
            return None
    
    def is_update_available(self) -> bool:
        """
        Check if update is available.
        
        Returns:
            bool: True if update available, False otherwise
        """
        self.current_version = self.get_current_version()
        self.latest_version = self.get_latest_version()
        
        if not self.latest_version:
            self.logger.error("Cannot determine latest version")
            return False
        
        if not self.current_version:
            self.logger.info("No current version found - update available")
            return True
        
        # Compare versions
        if self.current_version != self.latest_version:
            self.logger.info(f"Update available: {self.current_version} -> {self.latest_version}")
            return True
        else:
            self.logger.info("System is up to date")
            return False
    
    def create_backup(self) -> str:
        """
        Create backup of current installation.
        
        Returns:
            str: Backup directory path
        """
        try:
            # Create backup directory with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            
            self.logger.info(f"Creating backup at {backup_path}")
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup source code
            if os.path.exists(os.path.join(self.install_dir, 'src')):
                shutil.copytree(
                    os.path.join(self.install_dir, 'src'),
                    os.path.join(backup_path, 'src')
                )
            
            # Backup version file
            if os.path.exists(self.version_file):
                shutil.copy2(self.version_file, backup_path)
            
            # Backup configuration (as reference)
            if os.path.exists(os.path.join(self.config_dir, 'config.json')):
                shutil.copy2(
                    os.path.join(self.config_dir, 'config.json'),
                    os.path.join(backup_path, 'config.json.backup')
                )
            
            self.logger.info("Backup created successfully")
            return backup_path
            
        except Exception as e:
            raise UpdateError(f"Backup creation failed: {e}")
    
    def download_update(self) -> str:
        """
        Download update from GitHub.
        
        Returns:
            str: Path to downloaded update
        """
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix='bathyimager_update_')
            
            self.logger.info(f"Downloading update to {temp_dir}")
            
            # Clone repository
            cmd = [
                'git', 'clone', '--depth', '1',
                '--branch', self.github_branch,
                f'https://github.com/{self.github_repo}.git',
                temp_dir
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise UpdateError(f"Git clone failed: {result.stderr}")
            
            # Verify download
            src_dir = os.path.join(temp_dir, 'src')
            if not os.path.exists(src_dir):
                raise UpdateError("Downloaded update does not contain expected source code")
            
            self.logger.info("Update downloaded successfully")
            return temp_dir
            
        except subprocess.TimeoutExpired:
            raise UpdateError("Download timeout")
        except Exception as e:
            raise UpdateError(f"Download failed: {e}")
    
    def stop_service(self) -> bool:
        """
        Stop BathyImager imaging service.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            self.logger.info(f"Stopping {self.service_name} service")
            
            result = subprocess.run(
                ['systemctl', 'stop', self.service_name],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("Service stopped successfully")
                return True
            else:
                self.logger.error(f"Failed to stop service: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            return False
    
    def start_service(self) -> bool:
        """
        Start BathyImager imaging service.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            self.logger.info(f"Starting {self.service_name} service")
            
            result = subprocess.run(
                ['systemctl', 'start', self.service_name],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("Service started successfully")
                return True
            else:
                self.logger.error(f"Failed to start service: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            return False
    
    def install_update(self, update_path: str) -> bool:
        """
        Install downloaded update.
        
        Args:
            update_path: Path to downloaded update
            
        Returns:
            bool: True if installation successful, False otherwise
        """
        try:
            self.logger.info("Installing update")
            
            # Remove old source code
            old_src = os.path.join(self.install_dir, 'src')
            if os.path.exists(old_src):
                shutil.rmtree(old_src)
            
            # Copy new source code
            new_src = os.path.join(update_path, 'src')
            shutil.copytree(new_src, old_src)
            
            # Update permissions
            subprocess.run(['chown', '-R', 'pi:pi', self.install_dir], check=True)
            
            # Update version file
            with open(self.version_file, 'w') as f:
                f.write(self.latest_version)
            
            # Update Python dependencies
            self._update_dependencies(update_path)
            
            self.logger.info("Update installation complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Update installation failed: {e}")
            return False
    
    def _update_dependencies(self, update_path: str) -> None:
        """Update Python dependencies if requirements changed."""
        try:
            requirements_file = os.path.join(update_path, 'requirements.txt')
            if os.path.exists(requirements_file):
                self.logger.info("Updating Python dependencies")
                
                cmd = [
                    os.path.join(self.python_env, 'bin', 'pip'),
                    'install', '-r', requirements_file
                ]
                
                subprocess.run(cmd, check=True, timeout=300)
                self.logger.info("Dependencies updated")
            
        except Exception as e:
            self.logger.warning(f"Dependency update failed: {e}")
    
    def verify_update(self) -> bool:
        """
        Verify that update was successful.
        
        Returns:
            bool: True if update verified, False otherwise
        """
        try:
            self.logger.info("Verifying update")
            
            # Check version file
            if not os.path.exists(self.version_file):
                return False
            
            with open(self.version_file, 'r') as f:
                installed_version = f.read().strip()
            
            if installed_version != self.latest_version:
                self.logger.error(f"Version mismatch: expected {self.latest_version}, got {installed_version}")
                return False
            
            # Test import
            cmd = [
                os.path.join(self.python_env, 'bin', 'python'),
                '-c', f'import sys; sys.path.append("{self.install_dir}/src"); import main; print("Import successful")'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"Import test failed: {result.stderr.decode()}")
                return False
            
            self.logger.info("Update verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Update verification failed: {e}")
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """
        Rollback to backup version.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            bool: True if rollback successful, False otherwise
        """
        try:
            self.logger.warning(f"Rolling back to backup: {backup_path}")
            
            # Stop service
            self.stop_service()
            
            # Remove current installation
            current_src = os.path.join(self.install_dir, 'src')
            if os.path.exists(current_src):
                shutil.rmtree(current_src)
            
            # Restore backup
            backup_src = os.path.join(backup_path, 'src')
            if os.path.exists(backup_src):
                shutil.copytree(backup_src, current_src)
            
            # Restore version file
            backup_version = os.path.join(backup_path, 'VERSION')
            if os.path.exists(backup_version):
                shutil.copy2(backup_version, self.version_file)
            
            # Update permissions
            subprocess.run(['chown', '-R', 'pi:pi', self.install_dir])
            
            # Start service
            self.start_service()
            
            self.logger.info("Rollback completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def update(self, force: bool = False) -> bool:
        """
        Perform complete update process.
        
        Args:
            force: Force update even if no update available
            
        Returns:
            bool: True if update successful, False otherwise
        """
        update_path = None
        backup_path = None
        
        try:
            # Create update lock
            with open(self.update_lock, 'w') as f:
                f.write(str(os.getpid()))
            
            # Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Check for available update
            if not force and not self.is_update_available():
                self.logger.info("No update available")
                return True
            
            # Create backup
            backup_path = self.create_backup()
            
            # Download update
            update_path = self.download_update()
            
            # Stop service
            if not self.stop_service():
                raise UpdateError("Failed to stop service")
            
            # Install update
            if not self.install_update(update_path):
                raise UpdateError("Update installation failed")
            
            # Verify update
            if not self.verify_update():
                raise UpdateError("Update verification failed")
            
            # Start service
            if not self.start_service():
                self.logger.warning("Service failed to start after update")
            
            self.logger.info("Update completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            
            # Attempt rollback
            if backup_path:
                self.logger.info("Attempting rollback")
                self.rollback(backup_path)
            
            return False
            
        finally:
            # Cleanup
            if update_path and os.path.exists(update_path):
                shutil.rmtree(update_path)
            
            if os.path.exists(self.update_lock):
                os.remove(self.update_lock)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load updater configuration."""
    default_config = {
        'github_repo': 'Mike-Bollinger/BathyImager-Seabed-Imager',
        'github_branch': 'main',
        'install_dir': '/opt/bathyimager',
        'config_dir': '/etc/bathyimager',
        'backup_dir': '/opt/bathyimager/backups',
        'service_name': 'bathyimager',
        'python_env': '/opt/bathyimager/venv'
    }
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    return default_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='BathyImager Update System')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--force', '-f', action='store_true', help='Force update')
    parser.add_argument('--check', action='store_true', help='Check for updates only')
    parser.add_argument('--version', '-v', action='store_true', help='Show version info')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        updater = BathyImagerUpdater(config)
        
        if args.version:
            current = updater.get_current_version()
            latest = updater.get_latest_version()
            print(f"Current version: {current or 'Unknown'}")
            print(f"Latest version: {latest or 'Unknown'}")
            return 0
        
        if args.check:
            available = updater.is_update_available()
            if available:
                print("Update available")
                return 0
            else:
                print("No update available")
                return 0
        
        # Perform update
        success = updater.update(force=args.force)
        return 0 if success else 1
        
    except Exception as e:
        print(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())