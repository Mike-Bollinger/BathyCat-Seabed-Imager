"""
Enhanced Configuration System for BathyCat Seabed Imager
=======================================================

Advanced configuration management with validation, environment detection,
and runtime adjustments for production vs development environments.

Features:
- Configuration validation and type checking
- Environment-specific settings (development/production/testing)
- Runtime hardware detection and adjustment
- Configuration migration and versioning
- Secure credential management
- Hot configuration reloading
"""

import os
import sys
import json
import logging
import platform
import subprocess
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import threading


@dataclass
class CameraConfig:
    """Camera configuration settings."""
    device_index: int = 0
    width: int = 1920
    height: int = 1080
    fps: int = 30
    format: str = "MJPG"
    auto_focus: bool = False
    exposure: int = -1  # Auto exposure
    brightness: int = 128
    contrast: int = 32
    saturation: int = 32
    gain: int = 0
    white_balance: int = -1  # Auto white balance
    capture_timeout: float = 5.0
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class GPSConfig:
    """GPS configuration settings."""
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    timeout: float = 2.0
    fix_timeout: float = 30.0
    min_satellites: int = 4
    min_accuracy: float = 10.0  # meters
    retry_count: int = 3
    retry_delay: float = 2.0
    mock_enabled: bool = False
    mock_latitude: float = 40.7128
    mock_longitude: float = -74.0060


@dataclass
class StorageConfig:
    """Storage configuration settings."""
    base_path: str = "/media/usb"
    max_images_per_day: int = 10000
    cleanup_days: int = 30
    min_free_space_mb: int = 1000
    directory_structure: str = "%Y/%m/%d"
    filename_format: str = "bathycat_%Y%m%d_%H%M%S_{counter:04d}.jpg"
    jpeg_quality: int = 95
    auto_mount: bool = True
    mount_timeout: float = 10.0


@dataclass
class LEDConfig:
    """LED indicator configuration."""
    status_pin: int = 18
    error_pin: int = 19
    activity_pin: int = 20
    enabled: bool = True
    blink_rate: float = 0.5
    brightness: float = 0.8
    startup_test: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "/var/log/bathycat/bathycat.log"
    max_size_mb: int = 10
    backup_count: int = 5
    console_output: bool = True
    syslog_enabled: bool = False
    debug_modules: List[str] = None


@dataclass
class SystemConfig:
    """System-level configuration."""
    environment: str = "production"  # development, testing, production
    capture_interval: float = 1.0
    max_capture_errors: int = 10
    restart_on_error: bool = True
    health_check_interval: float = 60.0
    watchdog_timeout: float = 300.0
    graceful_shutdown_timeout: float = 30.0
    performance_monitoring: bool = False


@dataclass
class BathyCatConfig:
    """Complete BathyCat configuration."""
    version: str = "1.0"
    camera: CameraConfig = None
    gps: GPSConfig = None
    storage: StorageConfig = None
    leds: LEDConfig = None
    logging: LoggingConfig = None
    system: SystemConfig = None
    
    def __post_init__(self):
        """Initialize sub-configurations if not provided."""
        if self.camera is None:
            self.camera = CameraConfig()
        if self.gps is None:
            self.gps = GPSConfig()
        if self.storage is None:
            self.storage = StorageConfig()
        if self.leds is None:
            self.leds = LEDConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.system is None:
            self.system = SystemConfig()


class ConfigurationError(Exception):
    """Configuration-related error."""
    pass


class ConfigValidator:
    """Configuration validation utilities."""
    
    @staticmethod
    def validate_camera_config(config: CameraConfig) -> List[str]:
        """Validate camera configuration."""
        errors = []
        
        if config.device_index < 0:
            errors.append("Camera device_index must be >= 0")
        
        if config.width <= 0 or config.height <= 0:
            errors.append("Camera resolution must be positive")
        
        if config.fps <= 0 or config.fps > 120:
            errors.append("Camera FPS must be between 1 and 120")
        
        if config.capture_timeout <= 0:
            errors.append("Camera capture timeout must be positive")
        
        return errors
    
    @staticmethod
    def validate_gps_config(config: GPSConfig) -> List[str]:
        """Validate GPS configuration."""
        errors = []
        
        if not config.port:
            errors.append("GPS port must be specified")
        
        if config.baudrate not in [4800, 9600, 19200, 38400, 57600, 115200]:
            errors.append("GPS baudrate must be a standard value")
        
        if config.timeout <= 0:
            errors.append("GPS timeout must be positive")
        
        if config.min_satellites < 3:
            errors.append("Minimum satellites must be >= 3 for valid fix")
        
        if config.min_accuracy <= 0:
            errors.append("Minimum accuracy must be positive")
        
        if config.mock_enabled:
            if abs(config.mock_latitude) > 90:
                errors.append("Mock latitude must be between -90 and 90")
            if abs(config.mock_longitude) > 180:
                errors.append("Mock longitude must be between -180 and 180")
        
        return errors
    
    @staticmethod
    def validate_storage_config(config: StorageConfig) -> List[str]:
        """Validate storage configuration."""
        errors = []
        
        if not config.base_path:
            errors.append("Storage base path must be specified")
        
        if config.max_images_per_day <= 0:
            errors.append("Max images per day must be positive")
        
        if config.cleanup_days < 0:
            errors.append("Cleanup days must be non-negative")
        
        if config.min_free_space_mb < 0:
            errors.append("Min free space must be non-negative")
        
        if config.jpeg_quality < 1 or config.jpeg_quality > 100:
            errors.append("JPEG quality must be between 1 and 100")
        
        return errors
    
    @staticmethod
    def validate_led_config(config: LEDConfig) -> List[str]:
        """Validate LED configuration."""
        errors = []
        
        # GPIO pin validation (BCM numbering)
        valid_pins = list(range(2, 28))
        
        if config.status_pin not in valid_pins:
            errors.append(f"Invalid status LED pin: {config.status_pin}")
        
        if config.error_pin not in valid_pins:
            errors.append(f"Invalid error LED pin: {config.error_pin}")
        
        if config.activity_pin not in valid_pins:
            errors.append(f"Invalid activity LED pin: {config.activity_pin}")
        
        # Check for pin conflicts
        pins = [config.status_pin, config.error_pin, config.activity_pin]
        if len(pins) != len(set(pins)):
            errors.append("LED pins must be unique")
        
        if config.blink_rate <= 0:
            errors.append("LED blink rate must be positive")
        
        if config.brightness < 0 or config.brightness > 1:
            errors.append("LED brightness must be between 0 and 1")
        
        return errors
    
    @staticmethod
    def validate_system_config(config: SystemConfig) -> List[str]:
        """Validate system configuration."""
        errors = []
        
        if config.environment not in ["development", "testing", "production"]:
            errors.append("Environment must be development, testing, or production")
        
        if config.capture_interval <= 0:
            errors.append("Capture interval must be positive")
        
        if config.max_capture_errors < 1:
            errors.append("Max capture errors must be >= 1")
        
        if config.health_check_interval <= 0:
            errors.append("Health check interval must be positive")
        
        if config.watchdog_timeout <= 0:
            errors.append("Watchdog timeout must be positive")
        
        return errors


class EnvironmentDetector:
    """Detect runtime environment and hardware capabilities."""
    
    @staticmethod
    def detect_platform() -> Dict[str, Any]:
        """Detect platform information."""
        return {
            'system': platform.system(),
            'machine': platform.machine(),
            'platform': platform.platform(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
        }
    
    @staticmethod
    def is_raspberry_pi() -> bool:
        """Check if running on Raspberry Pi."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo and 'ARM' in cpuinfo
        except Exception:
            return False
    
    @staticmethod
    def detect_cameras() -> List[int]:
        """Detect available camera devices."""
        available_cameras = []
        
        # Check /dev/video* devices
        for i in range(10):
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                available_cameras.append(i)
        
        return available_cameras
    
    @staticmethod
    def detect_gps_devices() -> List[str]:
        """Detect available GPS/serial devices."""
        gps_devices = []
        
        # Common GPS device paths
        common_paths = [
            "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2",
            "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2",
            "/dev/serial0", "/dev/ttyAMA0"
        ]
        
        for device_path in common_paths:
            if os.path.exists(device_path):
                gps_devices.append(device_path)
        
        return gps_devices
    
    @staticmethod
    def detect_usb_storage() -> List[str]:
        """Detect USB storage devices."""
        usb_devices = []
        
        try:
            # Look for mounted USB devices
            result = subprocess.run(
                ['lsblk', '-no', 'MOUNTPOINT,FSTYPE'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line and '/media/' in line:
                    mountpoint = line.split()[0]
                    if mountpoint.startswith('/media/'):
                        usb_devices.append(mountpoint)
        
        except Exception:
            # Fallback to common mount points
            common_mounts = ["/media/usb", "/media/pi", "/mnt/usb"]
            for mount in common_mounts:
                if os.path.exists(mount) and os.path.ismount(mount):
                    usb_devices.append(mount)
        
        return usb_devices


class ConfigManager:
    """Advanced configuration management system."""
    
    def __init__(self, config_path: str = "/etc/bathycat/config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Optional[BathyCatConfig] = None
        self.validator = ConfigValidator()
        self.detector = EnvironmentDetector()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Environment-specific defaults
        self.environment_defaults = {
            'development': {
                'system': {'capture_interval': 5.0, 'performance_monitoring': True},
                'logging': {'level': 'DEBUG', 'console_output': True},
                'gps': {'mock_enabled': True}
            },
            'testing': {
                'system': {'capture_interval': 2.0, 'performance_monitoring': True},
                'logging': {'level': 'DEBUG', 'console_output': True},
                'gps': {'mock_enabled': True}
            },
            'production': {
                'system': {'capture_interval': 1.0, 'performance_monitoring': False},
                'logging': {'level': 'INFO', 'console_output': False},
                'gps': {'mock_enabled': False}
            }
        }
    
    def load_config(self) -> BathyCatConfig:
        """
        Load configuration from file with validation and environment adjustment.
        
        Returns:
            BathyCatConfig: Loaded and validated configuration
        """
        with self._lock:
            try:
                # Start with default configuration
                config = BathyCatConfig()
                
                # Load from file if exists
                if self.config_path.exists():
                    self.logger.info(f"Loading configuration from {self.config_path}")
                    
                    with open(self.config_path, 'r') as f:
                        config_data = json.load(f)
                    
                    config = self._dict_to_config(config_data)
                else:
                    self.logger.info("Configuration file not found, using defaults")
                
                # Apply environment-specific settings
                config = self._apply_environment_settings(config)
                
                # Auto-detect and adjust hardware settings
                config = self._auto_detect_hardware(config)
                
                # Validate configuration
                self._validate_config(config)
                
                self.config = config
                self.logger.info("Configuration loaded successfully")
                
                return config
                
            except Exception as e:
                raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: BathyCatConfig) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
        """
        with self._lock:
            try:
                # Validate before saving
                self._validate_config(config)
                
                # Ensure directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to dict and save
                config_data = self._config_to_dict(config)
                
                with open(self.config_path, 'w') as f:
                    json.dump(config_data, f, indent=2, default=str)
                
                self.config = config
                self.logger.info(f"Configuration saved to {self.config_path}")
                
            except Exception as e:
                raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BathyCatConfig:
        """Convert dictionary to configuration object."""
        config = BathyCatConfig()
        
        # Update version
        config.version = data.get('version', config.version)
        
        # Update sub-configurations
        if 'camera' in data:
            config.camera = CameraConfig(**data['camera'])
        
        if 'gps' in data:
            config.gps = GPSConfig(**data['gps'])
        
        if 'storage' in data:
            config.storage = StorageConfig(**data['storage'])
        
        if 'leds' in data:
            config.leds = LEDConfig(**data['leds'])
        
        if 'logging' in data:
            logging_data = data['logging']
            if 'debug_modules' not in logging_data:
                logging_data['debug_modules'] = []
            config.logging = LoggingConfig(**logging_data)
        
        if 'system' in data:
            config.system = SystemConfig(**data['system'])
        
        return config
    
    def _config_to_dict(self, config: BathyCatConfig) -> Dict[str, Any]:
        """Convert configuration object to dictionary."""
        return {
            'version': config.version,
            'camera': asdict(config.camera),
            'gps': asdict(config.gps),
            'storage': asdict(config.storage),
            'leds': asdict(config.leds),
            'logging': asdict(config.logging),
            'system': asdict(config.system)
        }
    
    def _apply_environment_settings(self, config: BathyCatConfig) -> BathyCatConfig:
        """Apply environment-specific settings."""
        env = config.system.environment
        
        if env in self.environment_defaults:
            env_settings = self.environment_defaults[env]
            
            # Apply system settings
            if 'system' in env_settings:
                for key, value in env_settings['system'].items():
                    setattr(config.system, key, value)
            
            # Apply logging settings
            if 'logging' in env_settings:
                for key, value in env_settings['logging'].items():
                    setattr(config.logging, key, value)
            
            # Apply GPS settings
            if 'gps' in env_settings:
                for key, value in env_settings['gps'].items():
                    setattr(config.gps, key, value)
        
        return config
    
    def _auto_detect_hardware(self, config: BathyCatConfig) -> BathyCatConfig:
        """Auto-detect and adjust hardware settings."""
        try:
            # Detect cameras
            cameras = self.detector.detect_cameras()
            if cameras and config.camera.device_index not in cameras:
                self.logger.warning(f"Camera {config.camera.device_index} not found, using {cameras[0]}")
                config.camera.device_index = cameras[0]
            
            # Detect GPS devices
            gps_devices = self.detector.detect_gps_devices()
            if gps_devices and config.gps.port not in gps_devices:
                self.logger.warning(f"GPS port {config.gps.port} not found, using {gps_devices[0]}")
                config.gps.port = gps_devices[0]
            
            # Detect USB storage
            usb_devices = self.detector.detect_usb_storage()
            if usb_devices and not os.path.exists(config.storage.base_path):
                self.logger.warning(f"Storage path {config.storage.base_path} not found, using {usb_devices[0]}")
                config.storage.base_path = usb_devices[0]
            
            # Adjust settings for non-Pi platforms
            if not self.detector.is_raspberry_pi():
                self.logger.info("Non-Pi platform detected, adjusting settings")
                config.leds.enabled = False
                config.gps.mock_enabled = True
        
        except Exception as e:
            self.logger.warning(f"Hardware detection failed: {e}")
        
        return config
    
    def _validate_config(self, config: BathyCatConfig) -> None:
        """Validate complete configuration."""
        all_errors = []
        
        # Validate each component
        all_errors.extend(self.validator.validate_camera_config(config.camera))
        all_errors.extend(self.validator.validate_gps_config(config.gps))
        all_errors.extend(self.validator.validate_storage_config(config.storage))
        all_errors.extend(self.validator.validate_led_config(config.leds))
        all_errors.extend(self.validator.validate_system_config(config.system))
        
        if all_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in all_errors)
            raise ConfigurationError(error_msg)
    
    def get_config(self) -> BathyCatConfig:
        """
        Get current configuration.
        
        Returns:
            BathyCatConfig: Current configuration
        """
        if self.config is None:
            return self.load_config()
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
        """
        with self._lock:
            if self.config is None:
                self.load_config()
            
            # Apply updates
            config_dict = self._config_to_dict(self.config)
            
            def deep_update(base_dict, update_dict):
                for key, value in update_dict.items():
                    if isinstance(value, dict) and key in base_dict:
                        deep_update(base_dict[key], value)
                    else:
                        base_dict[key] = value
            
            deep_update(config_dict, updates)
            
            # Convert back to config object
            updated_config = self._dict_to_config(config_dict)
            
            # Save updated configuration
            self.save_config(updated_config)
    
    def create_default_config(self) -> None:
        """Create default configuration file."""
        config = BathyCatConfig()
        config = self._apply_environment_settings(config)
        config = self._auto_detect_hardware(config)
        self.save_config(config)
        
        self.logger.info("Default configuration created")


# Convenience functions
def load_config(config_path: str = None) -> BathyCatConfig:
    """Load configuration using default manager."""
    if config_path is None:
        config_path = "/etc/bathycat/config.json"
    
    manager = ConfigManager(config_path)
    return manager.load_config()


def create_default_config(config_path: str = None) -> None:
    """Create default configuration file."""
    if config_path is None:
        config_path = "/etc/bathycat/config.json"
    
    manager = ConfigManager(config_path)
    manager.create_default_config()


if __name__ == "__main__":
    # Configuration testing and utilities
    import argparse
    
    parser = argparse.ArgumentParser(description='BathyCat Configuration Manager')
    parser.add_argument('--create-default', action='store_true', help='Create default configuration')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--show-hardware', action='store_true', help='Show detected hardware')
    parser.add_argument('--config', '-c', help='Configuration file path')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    config_path = args.config or "/etc/bathycat/config.json"
    
    try:
        if args.create_default:
            create_default_config(config_path)
            print(f"Default configuration created at {config_path}")
        
        elif args.validate:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            print("Configuration is valid")
        
        elif args.show_hardware:
            detector = EnvironmentDetector()
            print("Platform:", detector.detect_platform())
            print("Is Raspberry Pi:", detector.is_raspberry_pi())
            print("Cameras:", detector.detect_cameras())
            print("GPS Devices:", detector.detect_gps_devices())
            print("USB Storage:", detector.detect_usb_storage())
        
        else:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            print("Configuration loaded successfully")
            print(f"Environment: {config.system.environment}")
            print(f"Camera: /dev/video{config.camera.device_index}")
            print(f"GPS: {config.gps.port}")
            print(f"Storage: {config.storage.base_path}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)