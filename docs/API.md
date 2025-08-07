# BathyCat Seabed Imager - API Documentation

This document provides detailed API documentation for the BathyCat Seabed Imager system components.

## Table of Contents

1. [Configuration API](#configuration-api)
2. [Camera Controller API](#camera-controller-api)
3. [GPS Controller API](#gps-controller-api)
4. [Image Processor API](#image-processor-api)
5. [Storage Manager API](#storage-manager-api)
6. [Main Application API](#main-application-api)

---

## Configuration API

### Class: `Config`

Manages system configuration loading, validation, and access.

#### Constructor

```python
Config(config_path: Optional[str] = None)
```

**Parameters:**
- `config_path`: Path to configuration JSON file (optional)

**Example:**
```python
from config import Config

# Load default configuration
config = Config()

# Load from specific file
config = Config('/path/to/config.json')
```

#### Methods

##### `update_config(updates: Dict[str, Any])`

Update configuration with new values.

**Parameters:**
- `updates`: Dictionary of configuration updates

**Raises:**
- `ValueError`: If validation fails

**Example:**
```python
config.update_config({
    'capture_fps': 2.0,
    'jpeg_quality': 90
})
```

##### `save_config(path: Optional[str] = None)`

Save current configuration to file.

**Parameters:**
- `path`: Save path (optional, uses current path if None)

##### `get_config_summary() -> str`

Get formatted configuration summary.

**Returns:**
- String containing formatted configuration summary

#### Properties

All configuration values are accessible as properties:

```python
config.capture_fps          # Capture frame rate
config.camera_width         # Camera resolution width
config.camera_height        # Camera resolution height
config.storage_base_path    # Storage base directory
config.gps_port            # GPS serial port
```

---

## Camera Controller API

### Class: `CameraController`

Controls USB camera operations for high-frequency image capture.

#### Constructor

```python
CameraController(config: Config)
```

**Parameters:**
- `config`: Configuration object

#### Methods

##### `async initialize() -> bool`

Initialize camera connection and configuration.

**Returns:**
- `True` if successful, `False` otherwise

**Example:**
```python
camera = CameraController(config)
success = await camera.initialize()
if success:
    print("Camera ready")
```

##### `async capture_image() -> Optional[np.ndarray]`

Capture a single image from the camera.

**Returns:**
- NumPy array containing image data, or `None` if failed

**Example:**
```python
image = await camera.capture_image()
if image is not None:
    height, width, channels = image.shape
    print(f"Captured {width}x{height} image")
```

##### `async capture_burst(count: int) -> List[np.ndarray]`

Capture multiple images in rapid succession.

**Parameters:**
- `count`: Number of images to capture

**Returns:**
- List of captured images

##### `get_camera_info() -> Dict[str, Any]`

Get camera information and current settings.

**Returns:**
- Dictionary containing camera information

**Example:**
```python
info = camera.get_camera_info()
print(f"Resolution: {info['width']}x{info['height']}")
print(f"Captures: {info['capture_count']}")
```

##### `get_performance_stats() -> Dict[str, float]`

Get camera performance statistics.

**Returns:**
- Dictionary containing performance metrics

##### `async reset_camera() -> bool`

Reset the camera connection.

**Returns:**
- `True` if successful, `False` otherwise

##### `async shutdown()`

Shutdown the camera gracefully.

---

## GPS Controller API

### Class: `GPSController`

Handles GPS communication, time synchronization, and position tracking.

#### Constructor

```python
GPSController(config: Config)
```

#### Methods

##### `async initialize() -> bool`

Initialize GPS connection and configuration.

**Returns:**
- `True` if successful, `False` otherwise

##### `async update() -> bool`

Update GPS data by reading NMEA sentences.

**Returns:**
- `True` if new data received, `False` otherwise

**Example:**
```python
gps = GPSController(config)
await gps.initialize()

while True:
    if await gps.update():
        if gps.has_fix():
            pos = gps.get_current_position()
            print(f"Position: {pos['latitude']}, {pos['longitude']}")
    await asyncio.sleep(1.0)
```

##### `async wait_for_fix(timeout: float = 300.0) -> bool`

Wait for GPS fix with timeout.

**Parameters:**
- `timeout`: Maximum wait time in seconds

**Returns:**
- `True` if fix acquired, `False` if timeout

##### `has_fix() -> bool`

Check if GPS has a valid fix.

**Returns:**
- `True` if valid fix available

##### `get_current_position() -> Dict[str, Any]`

Get current GPS position data.

**Returns:**
- Dictionary containing position information:
  ```python
  {
      'latitude': float,      # Decimal degrees
      'longitude': float,     # Decimal degrees
      'altitude': float,      # Meters above sea level
      'timestamp': datetime,  # UTC timestamp
      'quality': int,         # Fix quality (0-9)
      'satellites': int,      # Number of satellites
      'hdop': float,         # Horizontal dilution of precision
      'speed': float,        # Speed over ground (knots)
      'course': float        # Course over ground (degrees)
  }
  ```

##### `get_position_string() -> str`

Get formatted position string.

**Returns:**
- Human-readable position string

##### `get_gps_stats() -> Dict[str, Any]`

Get GPS statistics and status.

**Returns:**
- Dictionary containing GPS statistics

##### `async shutdown()`

Shutdown GPS controller.

---

## Image Processor API

### Class: `ImageProcessor`

Processes and manages captured images with metadata embedding.

#### Constructor

```python
ImageProcessor(config: Config)
```

#### Methods

##### `async process_image(image_data: np.ndarray, gps_data: Dict[str, Any], capture_time: float) -> Optional[str]`

Process and save an image with metadata.

**Parameters:**
- `image_data`: Image as NumPy array
- `gps_data`: GPS position data
- `capture_time`: Capture timestamp (Unix time)

**Returns:**
- Path to saved image file, or `None` if failed

**Example:**
```python
processor = ImageProcessor(config)
gps_data = gps.get_current_position()
capture_time = time.time()

image_path = await processor.process_image(
    image_data, gps_data, capture_time
)
if image_path:
    print(f"Image saved: {image_path}")
```

##### `get_processing_stats() -> Dict[str, Any]`

Get image processing statistics.

**Returns:**
- Dictionary containing processing metrics

##### `async cleanup_old_files(days_to_keep: int = 7)`

Clean up old image files to free space.

**Parameters:**
- `days_to_keep`: Number of days to retain

##### `async shutdown()`

Shutdown image processor.

---

## Storage Manager API

### Class: `StorageManager`

Manages storage operations, disk space monitoring, and data organization.

#### Constructor

```python
StorageManager(config: Config)
```

#### Methods

##### `async initialize() -> bool`

Initialize storage system.

**Returns:**
- `True` if successful, `False` otherwise

##### `get_free_space_gb() -> float`

Get free space in GB.

**Returns:**
- Free space in gigabytes

##### `get_total_space_gb() -> float`

Get total space in GB.

**Returns:**
- Total space in gigabytes

##### `get_used_space_gb() -> float`

Get used space in GB.

**Returns:**
- Used space in gigabytes

##### `async check_storage_health() -> Dict[str, Any]`

Check storage health and return status.

**Returns:**
- Dictionary containing storage health information:
  ```python
  {
      'status': str,           # 'healthy', 'warning', 'critical', 'error'
      'free_space_gb': float,  # Available space
      'used_space_gb': float,  # Used space
      'total_space_gb': float, # Total space
      'used_percentage': float, # Usage percentage
      'warnings': List[str],   # Warning messages
      'images_stored': int,    # Number of images
      'last_check': str        # ISO timestamp
  }
  ```

##### `async auto_cleanup_if_needed() -> bool`

Perform automatic cleanup if storage is low.

**Returns:**
- `True` if cleanup performed, `False` otherwise

##### `async cleanup_old_data(days_override: Optional[int] = None) -> Tuple[int, int]`

Clean up old data files.

**Parameters:**
- `days_override`: Override default retention days

**Returns:**
- Tuple of (files_cleaned, bytes_freed)

##### `get_session_directories() -> List[Dict[str, Any]]`

Get list of session directories with information.

**Returns:**
- List of session directory information

##### `get_storage_stats() -> Dict[str, Any]`

Get comprehensive storage statistics.

**Returns:**
- Dictionary containing storage statistics

##### `async export_session_data(session_name: str, export_path: Optional[Path] = None) -> Optional[Path]`

Export a session's data to a compressed archive.

**Parameters:**
- `session_name`: Name of session to export
- `export_path`: Export destination (optional)

**Returns:**
- Path to exported archive, or `None` if failed

##### `async shutdown()`

Shutdown storage manager.

---

## Main Application API

### Class: `BathyCatImager`

Main application class coordinating all system components.

#### Constructor

```python
BathyCatImager(config_path: Optional[str] = None)
```

**Parameters:**
- `config_path`: Path to configuration file (optional)

#### Methods

##### `async initialize() -> bool`

Initialize all system components.

**Returns:**
- `True` if successful, `False` otherwise

##### `async start_capture()`

Start the image capture process.

This method runs the main capture loops:
- Image capture at specified FPS
- GPS data updates
- Status monitoring

##### `async run() -> bool`

Main run method that handles the complete application lifecycle.

**Returns:**
- `True` if successful, `False` otherwise

**Example:**
```python
async def main():
    imager = BathyCatImager('/etc/bathycat/config.json')
    success = await imager.run()
    return success

if __name__ == '__main__':
    asyncio.run(main())
```

##### `async shutdown()`

Shutdown the system gracefully.

---

## Usage Examples

### Basic System Setup

```python
import asyncio
from bathycat_imager import BathyCatImager

async def main():
    # Create and run the imager
    imager = BathyCatImager()
    await imager.run()

if __name__ == '__main__':
    asyncio.run(main())
```

### Custom Configuration

```python
from config import Config

# Create custom configuration
config = Config()
config.update_config({
    'capture_fps': 2.0,
    'camera_width': 1280,
    'camera_height': 720,
    'jpeg_quality': 95,
    'storage_base_path': '/custom/storage/path'
})

# Save configuration
config.save_config('/etc/bathycat/custom_config.json')
```

### Manual Component Control

```python
import asyncio
from camera_controller import CameraController
from gps_controller import GPSController
from config import Config

async def capture_with_gps():
    config = Config()
    
    # Initialize components
    camera = CameraController(config)
    gps = GPSController(config)
    
    await camera.initialize()
    await gps.initialize()
    
    # Wait for GPS fix
    if await gps.wait_for_fix(timeout=60):
        print("GPS fix acquired")
        
        # Capture image with GPS data
        image = await camera.capture_image()
        if image is not None:
            position = gps.get_current_position()
            print(f"Image captured at: {position['latitude']}, {position['longitude']}")
    
    # Cleanup
    await camera.shutdown()
    await gps.shutdown()

asyncio.run(capture_with_gps())
```

### Storage Management

```python
import asyncio
from storage_manager import StorageManager
from config import Config

async def manage_storage():
    config = Config()
    storage = StorageManager(config)
    
    await storage.initialize()
    
    # Check storage health
    health = await storage.check_storage_health()
    print(f"Storage status: {health['status']}")
    print(f"Free space: {health['free_space_gb']:.1f}GB")
    
    # Get session information
    sessions = storage.get_session_directories()
    for session in sessions[-5:]:  # Last 5 sessions
        print(f"Session: {session['name']}, Images: {session['file_count']}")
    
    # Cleanup if needed
    if health['status'] == 'warning':
        cleaned_files, freed_bytes = await storage.cleanup_old_data(days_override=7)
        print(f"Cleaned {cleaned_files} files, freed {freed_bytes/(1024**3):.1f}GB")

asyncio.run(manage_storage())
```

---

## Error Handling

All async methods may raise exceptions. Implement proper error handling:

```python
try:
    success = await camera.initialize()
    if not success:
        print("Camera initialization failed")
except Exception as e:
    print(f"Camera error: {e}")
```

Common exceptions:
- `CameraError`: Camera-related issues
- `GPSError`: GPS communication problems
- `StorageError`: Storage system issues
- `ValueError`: Configuration validation errors
- `IOError`: File system access problems

---

## Configuration Reference

### Complete Configuration Schema

```json
{
  "capture_fps": 4.0,
  "require_gps_fix": true,
  "gps_fix_timeout": 300.0,
  
  "camera_device_id": 0,
  "camera_width": 1920,
  "camera_height": 1080,
  "camera_fps": 30,
  "camera_format": "MJPG",
  "camera_auto_exposure": true,
  "camera_auto_white_balance": true,
  "camera_contrast": 50,
  "camera_saturation": 60,
  "camera_exposure": -6,
  "camera_white_balance": 4000,
  
  "gps_port": "/dev/serial0",
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true,
  
  "image_format": "JPEG",
  "jpeg_quality": 85,
  "enable_metadata": true,
  "enable_preview": true,
  "preview_width": 320,
  
  "storage_base_path": "/media/usb-storage/bathycat",
  "min_free_space_gb": 5.0,
  "auto_cleanup_enabled": true,
  "cleanup_threshold_gb": 10.0,
  "days_to_keep": 30,
  
  "log_level": "INFO",
  "log_to_file": true,
  "log_file_path": "/var/log/bathycat/bathycat.log",
  "log_max_size_mb": 100,
  "log_backup_count": 5,
  
  "auto_start": true,
  "watchdog_enabled": true,
  "status_report_interval": 30
}
```

---

For additional examples and advanced usage, see the `tests/` directory and example scripts in the project repository.
