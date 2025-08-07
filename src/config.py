#!/usr/bin/env python3
"""
Configuration Management for BathyCat Seabed Imager
==================================================

Handles configuration loading and validation for the imaging system.

Author: Mike Bollinger
Date: August 2025
"""

import json
import logging
import logging.config
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for BathyCat Imager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration."""
        self.config_path = config_path or self._get_default_config_path()
        self.config_data = {}
        
        # Load configuration
        self._load_config()
        self._validate_config()
        self._setup_derived_values()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Try multiple locations
        possible_paths = [
            "/etc/bathycat/config.json",
            "/opt/bathycat/config.json",
            str(Path.home() / ".bathycat" / "config.json"),
            str(Path(__file__).parent.parent / "config" / "bathycat_config.json")
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        # Return the project config path as default
        return possible_paths[-1]
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            config_path = Path(self.config_path)
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config_data = json.load(f)
                print(f"Configuration loaded from: {config_path}")
            else:
                print(f"Config file not found: {config_path}, using defaults")
                self.config_data = self._get_default_config()
                
                # Create config directory and save default config
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(self.config_data, f, indent=2)
                print(f"Default configuration saved to: {config_path}")
        
        except Exception as e:
            print(f"Failed to load config: {e}, using defaults")
            self.config_data = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            # Capture settings
            "capture_fps": 4.0,
            "require_gps_fix": True,
            "gps_fix_timeout": 300.0,
            
            # Camera settings
            "camera_device_id": 0,
            "camera_width": 1920,
            "camera_height": 1080,
            "camera_fps": 30,
            "camera_format": "MJPG",
            "camera_auto_exposure": True,
            "camera_auto_white_balance": True,
            "camera_contrast": 50,
            "camera_saturation": 60,
            
            # GPS settings
            "gps_port": "auto",  # Auto-detect USB GPS device
            "gps_baudrate": 9600,
            "gps_timeout": 1.0,
            "gps_time_sync": True,
            
            # Image processing
            "image_format": "JPEG",
            "jpeg_quality": 85,
            "enable_metadata": True,
            "enable_preview": True,
            "preview_width": 320,
            
            # Storage settings
            "storage_base_path": "/media/usb-storage/bathycat",
            "min_free_space_gb": 5.0,
            "auto_cleanup_enabled": True,
            "cleanup_threshold_gb": 10.0,
            "days_to_keep": 30,
            
            # Logging
            "log_level": "INFO",
            "log_to_file": True,
            "log_file_path": "/var/log/bathycat/bathycat.log",
            "log_max_size_mb": 100,
            "log_backup_count": 5,
            
            # System settings
            "auto_start": True,
            "watchdog_enabled": True,
            "status_report_interval": 30,
        }
    
    def _validate_config(self):
        """Validate configuration values."""
        try:
            # Validate capture settings
            if self.capture_fps <= 0 or self.capture_fps > 30:
                raise ValueError("capture_fps must be between 0 and 30")
            
            # Validate camera settings
            if self.camera_width <= 0 or self.camera_height <= 0:
                raise ValueError("Camera dimensions must be positive")
            
            if self.camera_fps <= 0:
                raise ValueError("Camera FPS must be positive")
            
            # Validate storage settings
            if self.min_free_space_gb < 0:
                raise ValueError("min_free_space_gb must be non-negative")
            
            if self.cleanup_threshold_gb < self.min_free_space_gb:
                raise ValueError("cleanup_threshold_gb must be >= min_free_space_gb")
            
            # Validate image settings
            if self.image_format.upper() not in ['JPEG', 'PNG']:
                raise ValueError("image_format must be JPEG or PNG")
            
            if self.jpeg_quality < 1 or self.jpeg_quality > 100:
                raise ValueError("jpeg_quality must be between 1 and 100")
            
            print("Configuration validation passed")
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            raise
    
    def _setup_derived_values(self):
        """Setup derived configuration values."""
        # Create storage paths
        self.storage_base_path = Path(self.storage_base_path)
        self.log_file_path = Path(self.log_file_path)
        
        # Setup logging configuration
        self.logging_config = self._create_logging_config()
    
    def _create_logging_config(self) -> Dict[str, Any]:
        """Create logging configuration."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': log_format,
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': self.log_level,
                    'formatter': 'standard',
                    'stream': 'ext://sys.stdout'
                }
            },
            'loggers': {
                '': {  # Root logger
                    'handlers': ['console'],
                    'level': self.log_level,
                    'propagate': False
                }
            }
        }
        
        # Add file handler if enabled
        if self.log_to_file:
            # Ensure log directory exists
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': self.log_level,
                'formatter': 'detailed',
                'filename': str(self.log_file_path),
                'maxBytes': self.log_max_size_mb * 1024 * 1024,
                'backupCount': self.log_backup_count
            }
            
            config['loggers']['']['handlers'].append('file')
        
        return config
    
    def save_config(self, path: Optional[str] = None):
        """Save current configuration to file."""
        save_path = path or self.config_path
        
        try:
            config_path = Path(save_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            
            print(f"Configuration saved to: {config_path}")
            
        except Exception as e:
            print(f"Failed to save configuration: {e}")
            raise
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        try:
            self.config_data.update(updates)
            self._validate_config()
            self._setup_derived_values()
            
            print("Configuration updated successfully")
            
        except Exception as e:
            print(f"Failed to update configuration: {e}")
            raise
    
    def get_config_summary(self) -> str:
        """Get a summary of current configuration."""
        summary = f"""
BathyCat Seabed Imager Configuration Summary
==========================================

Capture Settings:
  - Capture Rate: {self.capture_fps} FPS
  - Require GPS Fix: {self.require_gps_fix}
  - GPS Fix Timeout: {self.gps_fix_timeout}s

Camera Settings:
  - Device ID: {self.camera_device_id}
  - Resolution: {self.camera_width}x{self.camera_height}
  - Format: {self.camera_format}
  - Auto Exposure: {self.camera_auto_exposure}

GPS Settings:
  - Port: {self.gps_port}
  - Baudrate: {self.gps_baudrate}
  - Time Sync: {self.gps_time_sync}

Storage Settings:
  - Base Path: {self.storage_base_path}
  - Min Free Space: {self.min_free_space_gb}GB
  - Auto Cleanup: {self.auto_cleanup_enabled}
  - Keep Data: {self.days_to_keep} days

Image Settings:
  - Format: {self.image_format}
  - JPEG Quality: {self.jpeg_quality}
  - Metadata: {self.enable_metadata}
  - Previews: {self.enable_preview}

Logging:
  - Level: {self.log_level}
  - File Logging: {self.log_to_file}
  - Log Path: {self.log_file_path if self.log_to_file else 'Console only'}
        """
        
        return summary.strip()
    
    def __getattr__(self, name: str) -> Any:
        """Get configuration value by attribute access."""
        if name in self.config_data:
            return self.config_data[name]
        raise AttributeError(f"Configuration has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any):
        """Set configuration value by attribute access."""
        if name in ['config_path', 'config_data', 'logging_config']:
            # Allow setting internal attributes
            super().__setattr__(name, value)
        elif hasattr(self, 'config_data') and name in self.config_data:
            # Update configuration data
            self.config_data[name] = value
        else:
            # Set as regular attribute
            super().__setattr__(name, value)
