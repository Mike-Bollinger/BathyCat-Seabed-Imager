# Date-Stamped Logging System Documentation

## Overview

The BathyCat system now implements a date-stamped logging structure that mirrors the image directory organization. This ensures consistent file organization and makes log analysis easier by grouping logs by deployment date.

## Directory Structure

### Before (Single Log File)
```
/media/usb/bathyimager/logs/
└── bathyimager.log                    # All logs in one file
```

### After (Date-Stamped Structure)
```
/media/usb/bathyimager/logs/
├── 20251104/
│   └── bathyimager.log               # Logs for November 4, 2025
├── 20251105/
│   └── bathyimager.log               # Logs for November 5, 2025
└── 20251106/
    └── bathyimager.log               # Logs for November 6, 2025
```

## Features

### 1. **Date-Stamped Directory Structure**
- Each day gets its own log directory in `YYYYMMDD` format
- Matches the image directory structure exactly: `/media/usb/bathyimager/images/YYYYMMDD/`
- Maintains consistency across the entire system

### 2. **Automatic Daily Rotation**
- New log files are created automatically when the date changes
- No service restart required for log rotation
- Logs from multiple service restarts on the same day are appended to the same file

### 3. **Append Mode Operation**
- Multiple deployments on the same day append to the existing log file
- Preserves chronological order of log entries
- No data loss when service restarts

### 4. **USB Storage Integration**
- Logs are written to USB storage, not SD card
- Reduces SD card wear and prevents storage corruption
- Matches image storage location for easy backup

## Configuration

The logging system is configured in `bathyimager_config.json`:

```json
{
  "log_level": "INFO",
  "log_to_file": true,
  "log_file_path": "/media/usb/bathyimager/logs/bathyimager.log",
  "log_max_size_mb": 100,
  "log_backup_count": 5
}
```

### Configuration Parameters

- **`log_file_path`**: Base path for log files (date directory will be added automatically)
- **`log_to_file`**: Enable/disable file logging (console logging always active)
- **`log_level`**: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **`log_max_size_mb`**: Maximum size per log file before rotation
- **`log_backup_count`**: Number of backup files to keep

## Implementation Details

### Log Path Generation

The system generates date-stamped paths using the `_get_dated_log_path()` method:

```python
def _get_dated_log_path(self, base_log_path: str, timestamp: Optional[datetime] = None) -> str:
    """Generate date-stamped log path similar to image directory structure."""
```

**Example transformation:**
- Base path: `/media/usb/bathyimager/logs/bathyimager.log`
- Dated path: `/media/usb/bathyimager/logs/20251104/bathyimager.log`

### Automatic Rotation

The system checks for date changes in the main loop and rotates logs automatically:

```python
def _rotate_log_if_needed(self) -> None:
    """Rotate log file to new date if date has changed since initialization."""
```

### Timing Integration

Log rotation is checked periodically in the main capture loop, ensuring minimal performance impact.

## Log Entry Format

Each log entry includes:
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