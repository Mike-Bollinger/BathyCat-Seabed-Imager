# BathyCat Testing and Troubleshooting Tools

This directory contains the core troubleshooting and testing tools for the BathyCat Seabed Imager system. All scripts have been modernized and optimized for the current system configuration.

## 🛠️ Core Troubleshooting Tools

### `troubleshoot.py` - Master Troubleshooting Tool
**Primary entry point for all troubleshooting activities.**

```bash
# Full system health check
python3 troubleshoot.py

# Quick health check only  
python3 troubleshoot.py --quick

# Component-specific tests
python3 troubleshoot.py --component camera
python3 troubleshoot.py --component gps

# Performance analysis only
python3 troubleshoot.py --performance

# Network connectivity tests
python3 troubleshoot.py --network
```

### `system_health_check.py` - System Health Analysis
**Comprehensive system status monitoring and analysis.**

Features:
- Service status and performance metrics
- Memory and CPU usage analysis  
- Log analysis for timing and errors
- Component health verification
- Automated issue detection

```bash
python3 system_health_check.py
```

### `camera_troubleshoot.py` - Camera Diagnostics
**Complete camera system testing and troubleshooting.**

Features:
- Multiple backend testing (V4L2, GStreamer, FFmpeg)
- Resolution and framerate validation
- Exposure control testing
- Image quality analysis
- Performance benchmarking

```bash
python3 camera_troubleshoot.py
python3 camera_troubleshoot.py --detailed --benchmark
```

### `gps_troubleshoot.py` - GPS System Diagnostics
**GPS connectivity, timing, and metadata validation.**

Features:
- GPS device detection and connection testing
- NMEA sentence parsing validation
- GPS time synchronization verification
- Coordinate accuracy testing
- EXIF metadata validation

```bash
python3 gps_troubleshoot.py
python3 gps_troubleshoot.py --detailed --port /dev/ttyUSB0
```

### `performance_analyzer.py` - Performance Analysis
**Detailed performance profiling and optimization recommendations.**

Features:
- Pipeline timing analysis
- Component performance benchmarking
- Memory and CPU usage monitoring
- Storage performance testing
- Real-time performance monitoring

```bash
python3 performance_analyzer.py
python3 performance_analyzer.py --monitor --benchmark --report
```

### `system_validation.py` - System Validation Tests
**Core functionality validation using unittest framework.**

Features:
- Configuration validation
- Module import testing
- Basic functionality tests
- Dependency verification

```bash
python3 system_validation.py
```

## 🌐 Network Testing

### `network_test.sh` - Network Connectivity Testing
**Comprehensive network connectivity testing for dual Ethernet + WiFi setup.**

```bash
# Basic network test
./network_test.sh

# Test specific interface
./network_test.sh --interface eth0

# Continuous monitoring
./network_test.sh --continuous
```

## 📁 Specialized Tools

### `test_dated_logging.py` - Logging System Validation
**Tests the new date-stamped logging system functionality.**

```bash
python3 test_dated_logging.py
```

## 🚀 Quick Start Guide

### For System Issues:
```bash
# Run comprehensive diagnostic
python3 troubleshoot.py

# Quick health check
python3 troubleshoot.py --quick
```

### For Performance Issues:
```bash
# Full performance analysis
python3 troubleshoot.py --performance

# Real-time monitoring
python3 performance_analyzer.py --monitor
```

### For Component-Specific Issues:
```bash
# Camera problems
python3 troubleshoot.py --component camera

# GPS problems  
python3 troubleshoot.py --component gps

# Network problems
python3 troubleshoot.py --network
```

## 📊 Output and Reporting

All tools provide:
- **Colored output** for easy issue identification
- **Detailed timing metrics** for performance analysis
- **Specific recommendations** for identified issues
- **Exit codes** for automation (0 = success, 1 = issues found)

## 🔧 Common Issues and Solutions

### Service Not Running
```bash
sudo systemctl start bathyimager
sudo systemctl status bathyimager
```

### Performance Issues
```bash
# Check recent logs
sudo journalctl -u bathyimager --since "1 hour ago"

# Run performance analysis
python3 performance_analyzer.py --benchmark
```

### Camera Issues
```bash
# Test camera directly
python3 camera_troubleshoot.py --detailed

# Check USB devices
lsusb | grep -i camera
```

### GPS Issues
```bash
# Test GPS connection
python3 gps_troubleshoot.py --port /dev/ttyUSB0

# Check GPS time sync
sudo journalctl -u bathyimager | grep "GPS time"
```

### Storage Issues
```bash
# Check USB storage
df -h /media/usb/bathyimager
ls -la /media/usb/bathyimager/
```

## 📝 Notes

- All scripts work with the current configuration format
- Scripts automatically detect virtual environment vs system Python
- Network tests require root privileges for some operations
- Performance monitoring can run continuously for long-term analysis
- All timing optimizations from recent updates are validated

## 🔄 Maintenance

These tools are designed to be:
- **Self-contained** - minimal external dependencies
- **Robust** - handle missing components gracefully  
- **Informative** - provide actionable recommendations
- **Current** - work with latest system configuration

Run `python3 troubleshoot.py` regularly to ensure system health.