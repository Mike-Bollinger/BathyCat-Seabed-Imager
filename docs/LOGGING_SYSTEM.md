# BathyCat Date-Stamped Logging System

Complete documentation for the BathyCat Seabed Imager's advanced date-stamped logging system with USB storage and automated rotation.

## Overview

The BathyCat system implements a sophisticated logging architecture that provides:
- **📅 Date-stamped organization** matching image directory structure
- **💾 USB storage integration** reducing SD card wear
- **🔄 Automatic daily rotation** without service interruption  
- **📊 Performance monitoring** with timing precision analysis
- **🔍 Comprehensive diagnostics** for troubleshooting and analysis

## Directory Structure Evolution

### Traditional Approach (Replaced)
```
/var/log/bathyimager/
└── bathyimager.log                    # All logs in one file, SD card storage
```

### Current Date-Stamped System
```
/media/usb/bathyimager/logs/
├── 20251104/
│   └── bathyimager.log               # November 4, 2025 deployment
├── 20251105/
│   ├── bathyimager.log               # November 5, 2025 deployment  
│   └── performance_metrics.log       # Performance data (optional)
├── 20251106/
│   └── bathyimager.log               # November 6, 2025 deployment
└── archive/
    └── 2025/
        └── 10/                       # Archived logs by month
            ├── 20251001/
            └── 20251002/
```

## Key Features

### 1. **📅 Intelligent Date-Stamped Organization**
- **Daily Directories**: Each deployment day gets its own `YYYYMMDD` directory
- **Consistent Structure**: Mirrors image directory organization exactly
- **Cross-System Consistency**: Logs and images use identical date-based organization
- **Timezone Awareness**: Uses system timezone for accurate daily boundaries

### 2. **🔄 Seamless Automatic Rotation**
- **Zero-Downtime Rotation**: New log files created without service interruption
- **Append Mode**: Multiple service restarts on same day append to existing log
- **Chronological Preservation**: Maintains precise temporal order of all log entries
- **Intelligent Detection**: Automatically detects date changes during long operations

### 3. **💾 USB Storage Optimization**
- **SD Card Protection**: Logs written to USB storage to reduce SD card wear
- **Unified Storage**: Logs and images stored on same USB device for easy backup
- **Performance Optimized**: Direct USB writing with minimal system overhead
- **Reliability**: Graceful handling of USB device removal and reattachment

### 4. **📊 Advanced Logging Capabilities**
- **Performance Metrics**: Integrated timing and performance data logging
- **Structured Logging**: JSON and structured formats for automated analysis
- **Log Level Management**: Dynamic log level adjustment without restart
- **Compression**: Automatic compression of older log files
- **Cleanup**: Configurable automatic cleanup of old logs

### 5. **🔍 Diagnostic Integration**
- **Real-time Analysis**: Logs automatically analyzed by diagnostic tools
- **Error Detection**: Automatic identification and flagging of critical issues
- **Performance Monitoring**: Continuous analysis of timing and performance metrics
- **Alert Generation**: Proactive alerts for potential issues

## Configuration

The logging system is configured in `config/bathyimager_config.json`:

```json
{
  "logging": {
    "log_to_file": true,
    "log_file_path": "/media/usb/bathyimager/logs",
    "log_level": "INFO", 
    "log_max_size_mb": 100,
    "log_backup_count": 5,
    "performance_logging": true,
    "structured_logging": true,
    "compress_old_logs": true,
    "cleanup_enabled": true,
    "cleanup_days": 30,
    "date_format": "%Y%m%d",
    "timezone": "UTC"
  }
}
```

### Configuration Parameters

#### Core Logging Settings
- **`log_file_path`**: Base directory for date-stamped logs (date subdirectory added automatically)
- **`log_to_file`**: Enable/disable file logging (console logging always available)
- **`log_level`**: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **`log_max_size_mb`**: Maximum size per log file before rotation (per day)
- **`log_backup_count`**: Number of rotated backup files to keep per day

#### Advanced Features  
- **`performance_logging`**: Enable detailed timing and performance metrics logging
- **`structured_logging`**: Use JSON format for machine-readable logs
- **`compress_old_logs`**: Automatically compress logs older than 7 days
- **`cleanup_enabled`**: Enable automatic cleanup of old log directories
- **`cleanup_days`**: Days to retain logs (older logs automatically removed)
- **`date_format`**: Date format for directory names (default: YYYYMMDD)
- **`timezone`**: Timezone for log timestamps and daily boundaries

### Environment-Specific Configurations

#### Development/Testing Environment
```json
{
  "logging": {
    "log_level": "DEBUG",
    "performance_logging": true,
    "structured_logging": true,
    "cleanup_days": 7,
    "console_output": true
  }
}
```

#### Production Deployment  
```json
{
  "logging": {
    "log_level": "INFO",
    "performance_logging": false,
    "structured_logging": false,
    "cleanup_days": 30,
    "compress_old_logs": true,
    "console_output": false
  }
}
```

#### High-Performance Mode
```json
{
  "logging": {
    "log_level": "WARNING",
    "performance_logging": true,
    "log_max_size_mb": 50,
    "cleanup_days": 14,
    "compress_old_logs": true
  }
}
```

## Implementation Details

### Core Architecture

#### Date-Stamped Path Generation
```python
def _get_dated_log_path(self, base_log_path: str, timestamp: Optional[datetime] = None) -> str:
    """Generate date-stamped log path matching image directory structure."""
    if timestamp is None:
        timestamp = datetime.now()
    
    date_str = timestamp.strftime("%Y%m%d")
    log_dir = os.path.join(os.path.dirname(base_log_path), date_str)
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = os.path.basename(base_log_path)
    return os.path.join(log_dir, log_filename)
```

**Path Transformation Examples:**
- Base: `/media/usb/bathyimager/logs/bathyimager.log`
- Result: `/media/usb/bathyimager/logs/20251105/bathyimager.log`

#### Seamless Daily Rotation
```python
def _rotate_log_if_needed(self) -> None:
    """Check for date change and rotate log file without service interruption."""
    current_date = datetime.now().strftime("%Y%m%d")
    
    if current_date != self._current_log_date:
        self._close_current_log()
        self._current_log_date = current_date
        self._initialize_dated_log()
        self.logger.info(f"Log rotated to new date: {current_date}")
```

#### Performance Integration
Log rotation is checked every capture cycle with minimal overhead (<1ms):
```python
# In main capture loop
if self._should_check_log_rotation():
    self._rotate_log_if_needed()
```

### Storage Optimization
- **USB Direct Write**: Logs written directly to USB storage, bypassing SD card
- **Append Mode**: Multiple service restarts append to existing daily log
- **Atomic Operations**: Log rotation uses atomic file operations
- **Error Recovery**: Graceful handling of USB storage interruptions

## Usage Examples and Best Practices

### Development and Testing
```bash
# Enable debug logging for development
# Edit config: "log_level": "DEBUG", "performance_logging": true

# Monitor logs in real-time during development
tail -f /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log | grep -E "(ERROR|WARNING|TIMING)"

# Analyze performance during testing
python3 tests/performance_analyzer.py --analyze-logs --verbose
```

### Production Deployment
```bash
# Configure for production efficiency
# Edit config: "log_level": "INFO", "compress_old_logs": true, "cleanup_days": 30

# Monitor system health from logs
python3 tests/system_health_check.py --log-analysis --days 7

# Generate deployment reports
python3 tests/performance_analyzer.py --deployment-report --date 20251105
```

### Troubleshooting Workflows
```bash
# Search for errors in recent logs
find /media/usb/bathyimager/logs/ -name "bathyimager.log" -mtime -7 -exec grep -H "ERROR\|CRITICAL" {} \;

# Analyze timing issues
grep "TIMING\|PERF" /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Check GPS acquisition patterns
grep "GPS" /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log | head -20
```

### Log Maintenance
```bash
# Check log storage usage by date
du -sh /media/usb/bathyimager/logs/*/

# Manual compression of old logs
find /media/usb/bathyimager/logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Automated cleanup (configured in config file)
# cleanup_enabled: true, cleanup_days: 30
```

## Benefits and Advantages

### Operational Benefits
✅ **Deployment Organization**: Each deployment gets its own dated log directory  
✅ **Easy Analysis**: Logs grouped by deployment date match image organization  
✅ **Reduced SD Wear**: USB storage eliminates SD card write cycles  
✅ **Zero Downtime**: Log rotation occurs without service interruption  
✅ **Performance Tracking**: Integrated timing and performance metrics  

### Maintenance Benefits  
✅ **Automated Cleanup**: Configurable automatic cleanup of old logs  
✅ **Storage Efficiency**: Automatic compression and space management  
✅ **Backup Simplicity**: Date-organized logs easy to backup and archive  
✅ **Troubleshooting**: Rapid problem identification and analysis  
✅ **Integration**: Seamless integration with diagnostic and monitoring tools

### Technical Benefits
✅ **Consistency**: Identical organization to image directory structure  
✅ **Reliability**: Robust handling of storage interruptions and recovery  
✅ **Performance**: Minimal overhead on imaging pipeline (<1ms impact)  
✅ **Scalability**: Efficient handling of long-term deployments  
✅ **Compatibility**: Works with existing log analysis tools and workflows

The BathyCat date-stamped logging system provides enterprise-level logging capabilities optimized for autonomous marine deployment environments, ensuring reliable data collection, analysis, and maintenance operations.

## Log Analysis and Monitoring

### Automated Log Analysis
```bash
# Analyze today's logs for issues
python3 tests/system_health_check.py --log-analysis

# Performance analysis from logs  
python3 tests/performance_analyzer.py --analyze-logs --days 7

# Search for specific issues
python3 tests/troubleshoot.py --log-search "ERROR|CRITICAL"

# Generate daily performance report
python3 tests/performance_analyzer.py --daily-report --date 20251105
```

### Real-Time Log Monitoring
```bash
# Monitor current day's log file
tail -f /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Monitor with automatic analysis
python3 tests/system_health_check.py --live-monitor

# Performance monitoring with logs
python3 tests/performance_analyzer.py --monitor --with-logs
```

### Log File Management
```bash
# Check log storage usage
du -sh /media/usb/bathyimager/logs/

# Manual log cleanup (older than 30 days)  
python3 src/storage.py --cleanup-logs --days 30

# Compress old logs manually
find /media/usb/bathyimager/logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Validate log file integrity
python3 tests/test_dated_logging.py --validate-logs
```

### Performance Metrics Integration

The logging system captures detailed performance metrics:

```bash
# View timing statistics from logs
grep "TIMING" /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Extract GPS acquisition times  
grep "GPS_FIX" /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Analyze camera performance metrics
grep "CAPTURE_TIME" /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log
```

## Log Entry Format and Structure

### Standard Log Entry Format
```
2025-11-05 14:32:15,123 - INFO - main - Image captured: /media/usb/bathyimager/images/20251105/IMG_20251105_143215_123.jpg [GPS: 40.7128,-74.0060] [TIMING: 0.0087s]
2025-11-05 14:32:15,128 - DEBUG - camera - Camera capture completed in 0.0045s
2025-11-05 14:32:15,135 - DEBUG - image_processor - EXIF metadata embedded in 0.0032s  
2025-11-05 14:32:15,142 - DEBUG - storage - Image written to USB storage in 0.0019s
2025-11-05 14:32:16,001 - INFO - gps - GPS fix quality: 3D fix, 8 satellites, HDOP: 1.2
```

### Structured JSON Format (Optional)
When `structured_logging` is enabled:
```json
{
  "timestamp": "2025-11-05T14:32:15.123Z",
  "level": "INFO",
  "component": "main",
  "message": "Image captured",
  "metadata": {
    "image_path": "/media/usb/bathyimager/images/20251105/IMG_20251105_143215_123.jpg",
    "gps_coordinates": [40.7128, -74.0060],
    "timing": {
      "total_capture_time": 0.0087,
      "camera_capture": 0.0045,
      "exif_processing": 0.0032,
      "storage_write": 0.0019
    },
    "gps_info": {
      "fix_quality": "3D",
      "satellite_count": 8,
      "hdop": 1.2
    }
  }
}
```

### Performance Metrics Logging
```
2025-11-05 14:32:15,123 - PERF - timing - CAPTURE_PIPELINE_START
2025-11-05 14:32:15,128 - PERF - camera - CAMERA_CAPTURE_TIME: 0.0045s
2025-11-05 14:32:15,135 - PERF - processor - EXIF_EMBED_TIME: 0.0032s
2025-11-05 14:32:15,142 - PERF - storage - USB_WRITE_TIME: 0.0019s
2025-11-05 14:32:15,143 - PERF - timing - CAPTURE_PIPELINE_END: 0.0087s
```

### Log Entry Components
Each log entry contains:
- **Timestamp**: High-precision timestamp with milliseconds
- **Log Level**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Component**: Source component (main, camera, gps, storage, etc.)
- **Message**: Human-readable message
- **Metadata**: Structured data (GPS coordinates, timing, file paths)
- **Performance Data**: Timing measurements and performance metrics
- **Timestamp**: ISO format with timezone
- **Logger Name**: Module or component name
- **Level**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Message**: Descriptive log message

**Example entries:**
```
2025-11-04 14:25:30,123 - main - INFO - 📝 Date-stamped logging enabled: /media/usb/bathyimager/logs/20251104/bathyimager.log
2025-11-04 14:25:30,456 - camera - INFO - Camera initialized: 1920x1080 @ 30fps
2025-11-04 14:25:31,789 - gps - INFO - GPS fix acquired: 40.123456°N, 74.654321°W
2025-11-04 14:25:32,012 - main - DEBUG - 🚀 Pipeline timing: Total=45.2ms (Capture=12.1ms, GPS=3.2ms, Process=25.8ms, Save=4.1ms)
```

## Performance Impact

### Timing Measurements
The new logging system includes detailed performance monitoring:

- **Pipeline Timing**: Total capture time and breakdown by stage
- **Processing Timing**: Detailed image processing performance metrics
- **Component Health**: Regular system health checks and diagnostics

### Storage Efficiency
- **USB Storage**: Prevents SD card wear and performance degradation
- **Date Organization**: Makes log analysis and cleanup easier
- **Append Mode**: Efficient file handling for multiple service restarts

## Troubleshooting

### Common Issues

1. **Log Directory Not Created**
   - Check USB storage mount status
   - Verify permissions on `/media/usb/bathyimager/`
   - Check available disk space

2. **Logs Not Rotating**
   - Verify system date/time is correct
   - Check GPS time synchronization status
   - Review main loop operation in debug logs

3. **Performance Impact**
   - Log rotation check occurs only during health checks (every 30 seconds)
   - Minimal CPU overhead for date comparison
   - File operations are atomic and non-blocking

### Monitoring Commands

```bash
# Check current log directory
ls -la /media/usb/bathyimager/logs/

# View today's logs
tail -f /media/usb/bathyimager/logs/$(date +%Y%m%d)/bathyimager.log

# Check log directory sizes
du -sh /media/usb/bathyimager/logs/*/

# Monitor log rotation
watch "ls -la /media/usb/bathyimager/logs/"
```

## Migration Notes

### From Previous Version
- Existing logs remain in their original location
- New logs automatically use date-stamped structure
- No manual migration required

### Backward Compatibility
- Configuration format remains unchanged
- Console logging behavior unchanged
- Log level and formatting preserved

## Benefits

1. **Consistency**: Matches image directory structure exactly
2. **Organization**: Easy to find logs for specific deployment dates
3. **Performance**: USB storage reduces SD card wear
4. **Reliability**: Automatic rotation prevents large single files
5. **Analysis**: Grouped logs simplify troubleshooting and analysis
6. **Backup**: Date-based structure simplifies archival procedures

This implementation provides robust, organized logging that scales with system usage while maintaining excellent performance characteristics.