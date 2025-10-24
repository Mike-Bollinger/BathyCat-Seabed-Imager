# GPS Time Synchronization for BathyCat Seabed Imager

## Overview

The BathyCat seabed imager includes comprehensive GPS time synchronization to ensure accurate timestamps on captured images. This system uses GPS time to set and maintain the Raspberry Pi system clock in UTC.

## Architecture

The GPS time synchronization system consists of:

1. **Boot-Time Sync Service**: Synchronizes system clock once per boot when GPS fix is acquired
2. **Periodic Sync Timer**: Refreshes time sync every 30 minutes to prevent clock drift
3. **Enhanced GPS Class**: Improved time sync methods in existing GPS functionality  
4. **UTC-Only Operation**: System always operates in UTC time regardless of location
5. **Systemd Integration**: Proper service ordering and dependency management

## Key Features

- **Automatic Boot-Time Sync**: Synchronizes system clock with GPS time once per boot cycle
- **Periodic Refresh**: Re-syncs time every 30 minutes to prevent drift during long operations
- **UTC-Only Operation**: System always uses UTC time regardless of geographic location
- **Non-Blocking Boot**: GPS sync runs independently and doesn't delay system boot
- **Enhanced Error Handling**: Robust error recovery and logging
- **Preserves Existing Functionality**: Image geotagging continues to work unchanged
- **Multiple Fallback Methods**: Uses timedatectl and falls back to date command

## System Components

### 1. GPS Time Sync Script (`gps_time_sync.py`)

The main Python script that handles GPS time synchronization:

```python
python3 gps_time_sync.py --boot      # Boot-time sync (one-shot)
python3 gps_time_sync.py --periodic  # Periodic sync (called by timer)
```

**Key Features:**
- Automatic GPS device detection on multiple serial ports
- NMEA sentence parsing for accurate time extraction
- Always sets system timezone to UTC
- Fast GPS fix acquisition (2-minute timeout for boot, 30 seconds for periodic)
- Comprehensive error handling and logging
- Creates sync marker to prevent multiple boot syncs

### 2. Systemd Services

**Boot Sync Service (`gps-boot-sync.service`)**:
- Runs once per boot after system is ready
- Does not block boot process or other services
- 3-minute timeout for GPS acquisition
- Creates marker file to prevent duplicate runs

**Periodic Sync Service (`gps-periodic-sync.service`)**:
- Called by systemd timer every 30 minutes
- Quick 2-minute timeout for faster operation
- Runs in background without affecting main operation

**Periodic Sync Timer (`gps-periodic-sync.timer`)**:
- Starts 10 minutes after boot
- Runs every 30 minutes thereafter
- Persistent across reboots

### 3. Service Integration

The GPS time sync integrates with existing services:

```
Boot Sequence:
1. System boots and reaches multi-user.target
2. GPS boot sync service starts (non-blocking)
3. BathyImager service starts normally
4. GPS periodic timer starts 10 minutes after boot
5. Timer triggers GPS sync every 30 minutes
```

## Installation

The GPS time synchronization is installed automatically via `install.sh`:

```bash
sudo ./scripts/install.sh
```

This installs:
- GPS time sync Python script
- Systemd service and timer files
- Required dependencies (systemd-timesyncd, tzdata)
- Enables and starts all services

## Configuration

### GPS Settings

Configure GPS settings in `config/bathycat_config.json`:

```json
{
  "gps_port": "/dev/ttyUSB0",
  "gps_baudrate": 9600,
  "gps_timeout": 1.0,
  "gps_time_sync": true
}
```

### Service Settings

No additional configuration needed - services use optimal defaults:

- **Boot sync timeout**: 2 minutes (fast boot, adequate for most GPS devices)
- **Periodic sync timeout**: 30 seconds (GPS should already have fix)
- **Periodic interval**: 30 minutes (prevents drift without excessive GPS usage)
- **Timezone**: Always UTC (no location-based timezone detection)

## Operation

### Boot-Time Synchronization

1. System boots normally without waiting for GPS
2. GPS boot sync service starts independently
3. Service detects GPS device and waits for fix
4. When GPS fix acquired, system time set to GPS time in UTC
5. Sync marker created to prevent duplicate runs
6. Service completes and exits

### Periodic Synchronization

1. Timer triggers GPS periodic sync every 30 minutes
2. Service quickly connects to GPS (which should have fix already)
3. System time updated with current GPS time
4. Service completes quickly (usually under 30 seconds)

### Time Zone Handling

- System timezone always set to UTC
- No coordinate-based timezone detection
- All timestamps in logs and images use UTC
- Simplifies time handling and avoids timezone complexities

## Monitoring and Troubleshooting

### Check Service Status

```bash
# Check boot sync service
sudo systemctl status gps-boot-sync

# Check periodic sync timer
sudo systemctl status gps-periodic-sync.timer

# Check recent periodic sync runs
sudo systemctl status gps-periodic-sync
```

### View Logs

```bash
# View GPS sync logs
sudo journalctl -u gps-boot-sync -f
sudo journalctl -u gps-periodic-sync -f

# View all GPS-related logs
sudo journalctl -u 'gps-*' -f

# View time sync log file
sudo tail -f /var/log/bathyimager/gps_time_sync.log
```

### Check Time Status

```bash
# Check current time and timezone
timedatectl status

# Check if GPS sync marker exists
ls -la /var/run/gps_time_synced

# Check timer next run time
systemctl list-timers gps-periodic-sync.timer
```

### Manual Operations

```bash
# Manual boot sync
sudo systemctl start gps-boot-sync

# Manual periodic sync  
sudo systemctl start gps-periodic-sync

# Force timer to run now
sudo systemctl start gps-periodic-sync.timer

# Check GPS device
ls -la /dev/tty{USB,ACM,AMA}*

# Test GPS time sync directly
sudo python3 /home/bathyimager/BathyCat-Seabed-Imager/src/gps_time_sync.py --boot
```

### Common Issues and Solutions

**Issue: GPS device not detected**
```bash
# Check for GPS devices
ls -la /dev/tty{USB,ACM,AMA}*

# Check device permissions
sudo usermod -a -G dialout root

# Check GPS device is working
sudo timeout 10 cat /dev/ttyUSB0
```

**Issue: GPS sync taking too long**
```bash
# Check GPS signal strength (if device supports it)
# Move device to location with clear sky view
# Check GPS antenna connection

# Review GPS sync logs for timeout issues
sudo journalctl -u gps-boot-sync --since "1 hour ago"
```

**Issue: Time not syncing**
```bash
# Check if timedatectl is available
which timedatectl

# Check system permissions for time setting
# Ensure service runs as root

# Test manual time setting
sudo timedatectl set-time "2024-01-01 12:00:00"
```

**Issue: Periodic sync not running**
```bash
# Check if timer is enabled
sudo systemctl is-enabled gps-periodic-sync.timer

# Check timer status
sudo systemctl status gps-periodic-sync.timer

# Check timer logs
sudo journalctl -u gps-periodic-sync.timer
```

## Testing

Use the comprehensive test suite:

```bash
# Run all tests
sudo ./scripts/test_gps_time_sync.sh --full

# Run only simulation tests (no GPS required)
sudo ./scripts/test_gps_time_sync.sh --simulate

# Run manual GPS tests (requires GPS device)
sudo ./scripts/test_gps_time_sync.sh --manual
```

### Test Categories

1. **Service Installation Tests**: Verify all service files installed correctly
2. **GPS Device Detection Tests**: Test GPS device detection logic
3. **Time Sync Function Tests**: Test time synchronization functions (simulation)
4. **Integration Tests**: Test systemd service integration
5. **Manual GPS Tests**: Test with real GPS hardware

## Performance Impact

The GPS time synchronization system is designed for minimal performance impact:

- **Boot Impact**: No delay - GPS sync runs independently after boot
- **Runtime Impact**: Periodic sync uses GPS for ~30 seconds every 30 minutes
- **Resource Usage**: Minimal CPU and memory usage
- **GPS Usage**: Does not interfere with main imaging GPS usage
- **Power Usage**: Negligible additional power consumption

## Security Considerations

- Services run as root (required for time setting)
- Limited systemd security restrictions due to hardware access needs
- GPS time sync only affects system time, not configuration
- No network access required - purely GPS-based
- Log files created with appropriate permissions

## Maintenance

### Regular Maintenance

- Monitor GPS sync logs for any recurring issues
- Verify GPS device connection and antenna condition
- Check GPS sync marker file is being created/updated
- Ensure GPS device has clear sky view for optimal operation

### Updates

GPS time sync components are updated automatically with system updates:

```bash
cd /home/bathyimager/BathyCat-Seabed-Imager
git pull
sudo ./scripts/install.sh --update
```

### Backup

Important configuration files to backup:
- `/etc/systemd/system/gps-boot-sync.service`
- `/etc/systemd/system/gps-periodic-sync.service`
- `/etc/systemd/system/gps-periodic-sync.timer`
- `/home/bathyimager/BathyCat-Seabed-Imager/config/bathycat_config.json`

## Integration with Existing System

The GPS time synchronization integrates seamlessly with existing BathyImager functionality:

### Image Geotagging
- Existing GPS class continues to work unchanged
- Images still tagged with GPS coordinates as before
- More accurate timestamps due to GPS time sync

### GPS Usage
- Boot and periodic sync use GPS briefly
- Main imaging GPS usage unaffected
- GPS device shared between time sync and imaging

### Service Dependencies
- GPS time sync runs before main BathyImager service
- BathyImager can start even if GPS sync fails
- No blocking dependencies that could prevent imaging

## Technical Details

### NMEA Sentence Processing

The system processes standard NMEA sentences for time extraction:

- **RMC (Recommended Minimum)**: Primary source for time and date
- **GGA (Global Positioning System Fix Data)**: Backup position data
- Handles various GPS coordinate formats and directions
- Validates GPS fix quality before using time data

### Time Setting Methods

1. **Primary**: `timedatectl set-time` (systemd method)
2. **Fallback**: `date` command (traditional method)
3. **Always UTC**: No timezone conversion or detection

### Error Handling

- GPS device detection failures: Try multiple serial ports
- GPS fix timeout: Log warning but don't fail service
- Time setting failures: Try fallback method, log errors
- Configuration errors: Use safe defaults, continue operation

This comprehensive GPS time synchronization ensures accurate timestamps for all captured seabed imagery while maintaining system reliability and performance.