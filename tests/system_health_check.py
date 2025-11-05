#!/usr/bin/env python3
"""
BathyCat System Health Check
===========================

This script provides comprehensive system health analysis and troubleshooting
recommendations for the BathyCat Seabed Imager system.

Features:
- Service status monitoring
- Hardware component testing  
- Configuration validation
- Performance analysis
- Automated fix recommendations

Usage: python3 system_health_check.py [--detailed] [--auto-fix]
"""

import subprocess
import os
import sys
import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path for BathyCat modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_service_status():
    """Check BathyCat service status with enhanced analysis."""
    print("🔍 SERVICE STATUS")
    print("=" * 50)
    
    try:
        # Check service status
        result = subprocess.run(['systemctl', 'is-active', 'bathyimager'], 
                               capture_output=True, text=True)
        status = result.stdout.strip()
        print(f"📊 Service status: {status}")
        
        if status == "active":
            # Get detailed service info
            result = subprocess.run(['systemctl', 'show', 'bathyimager', '--no-pager'],
                                   capture_output=True, text=True)
            service_info = result.stdout
            
            # Extract start time and memory usage
            start_time_match = re.search(r'ExecMainStartTimestamp=(.+)', service_info)
            memory_match = re.search(r'MemoryCurrent=(\d+)', service_info)
            
            if start_time_match:
                print(f"🕐 Started: {start_time_match.group(1)}")
            if memory_match:
                memory_mb = int(memory_match.group(1)) / (1024 * 1024)
                print(f"💾 Memory usage: {memory_mb:.1f} MB")
            
            # Get recent logs for analysis
            result = subprocess.run(['journalctl', '-u', 'bathyimager', '--since', '10 minutes ago', '--no-pager'],
                                   capture_output=True, text=True)
            logs = result.stdout
            
            # Analyze logs for performance and issues
            issues = []
            
            # Check for timing optimization logs
            timing_matches = re.findall(r'🚀 Pipeline timing: Total=([\d.]+)ms', logs)
            if timing_matches:
                avg_timing = sum(float(t) for t in timing_matches[-10:]) / min(len(timing_matches), 10)
                print(f"⏱️  Average pipeline time: {avg_timing:.1f}ms")
                if avg_timing > 100:  # More than 100ms is concerning
                    issues.append(f"Slow pipeline performance: {avg_timing:.1f}ms")
            
            # Check for image processing timing
            process_matches = re.findall(r'Image processing timing: Total=([\d.]+)ms', logs)
            if process_matches:
                avg_process = sum(float(t) for t in process_matches[-10:]) / min(len(process_matches), 10)
                print(f"🖼️  Average processing time: {avg_process:.1f}ms")
            
            # Check capture rate
            captures_in_logs = len(re.findall(r'Image captured:', logs))
            if captures_in_logs > 0:
                minutes_analyzed = 10
                estimated_rate = captures_in_logs / minutes_analyzed * 60  # per hour
                print(f"📸 Recent capture activity: ~{estimated_rate:.0f} images/hour")
            
            # Check for common issues
            if "Failed to capture camera frame" in logs:
                issues.append("Camera capture failures detected")
            if "GPS not available" in logs:
                issues.append("GPS connectivity issues")
            if "Storage not available" in logs:
                issues.append("USB storage problems")
            if "Log rotated to new date" in logs:
                print("📝 Log rotation working correctly")
                
            return status, issues
        else:
            return status, ["Service not running - use 'sudo systemctl start bathyimager'"]
            
    except Exception as e:
        print(f"❌ Failed to check service status: {e}")
        return "unknown", ["Cannot check service status - ensure systemctl is available"]

def check_camera_devices():
    """Check camera device availability."""
    print("\n=== CAMERA DEVICES ===")
    
    # Check USB devices
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        usb_output = result.stdout
        
        camera_devices = []
        for line in usb_output.split('\n'):
            if any(keyword in line.lower() for keyword in ['camera', 'webcam', 'video', 'microdia']):
                camera_devices.append(line.strip())
        
        if camera_devices:
            print("USB camera devices found:")
            for device in camera_devices:
                print(f"  {device}")
        else:
            print("No USB camera devices found in lsusb")
    except:
        print("Could not check USB devices")
    
    # Check video devices
    video_devices = []
    for i in range(10):
        if os.path.exists(f"/dev/video{i}"):
            video_devices.append(f"/dev/video{i}")
    
    if video_devices:
        print(f"Video devices: {', '.join(video_devices)}")
        
        # Check permissions
        video0_stat = None
        try:
            stat_result = subprocess.run(['ls', '-la', '/dev/video0'], 
                                       capture_output=True, text=True)
            video0_stat = stat_result.stdout.strip()
            print(f"Video0 permissions: {video0_stat}")
            
            if 'video' not in video0_stat:
                print("⚠️  Video device may not have correct group permissions")
        except:
            pass
            
        return len(video_devices) > 0, video0_stat
    else:
        print("No video devices found")
        return False, None

def check_config():
    """Check configuration file."""
    print("\n=== CONFIGURATION ===")
    
    config_path = "/home/bathyimager/BathyCat-Seabed-Imager/config/bathyimager_config.json"
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print(f"Configuration loaded: {config_path}")
            print(f"  Capture FPS: {config.get('capture_fps', 'NOT SET')}")
            print(f"  Camera auto exposure: {config.get('camera_auto_exposure', 'NOT SET')}")
            print(f"  Camera auto WB: {config.get('camera_auto_white_balance', 'NOT SET')}")
            print(f"  Enable metadata: {config.get('enable_metadata', 'NOT SET')}")
            
            return config
        else:
            print(f"Configuration file not found: {config_path}")
            return None
            
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return None

def analyze_recent_images():
    """Analyze recent images for issues."""
    print("\n=== RECENT IMAGES ===")
    
    # Look for recent images
    storage_path = "/media/usb/bathyimager"
    
    try:
        if os.path.exists(storage_path):
            # Find most recent images
            recent_images = []
            for root, dirs, files in os.walk(storage_path):
                for file in files:
                    if file.endswith('.jpg'):
                        filepath = os.path.join(root, file)
                        mtime = os.path.getmtime(filepath)
                        recent_images.append((filepath, mtime))
            
            if recent_images:
                recent_images.sort(key=lambda x: x[1], reverse=True)
                latest_images = recent_images[:3]
                
                print(f"Found {len(recent_images)} total images")
                print("Most recent 3 images:")
                
                for filepath, mtime in latest_images:
                    timestamp = datetime.fromtimestamp(mtime)
                    filename = os.path.basename(filepath)
                    size = os.path.getsize(filepath)
                    
                    print(f"  {filename} ({timestamp.strftime('%H:%M:%S')}) - {size} bytes")
                    
                    # Check if image is suspiciously small (might be white/black)
                    if size < 50000:  # Less than 50KB might indicate solid color
                        print(f"    ⚠️  Small file size - possible solid color image")
                
                return len(recent_images), latest_images
            else:
                print("No images found in storage")
                return 0, []
        else:
            print(f"Storage path not found: {storage_path}")
            return 0, []
            
    except Exception as e:
        print(f"Failed to analyze images: {e}")
        return 0, []

def generate_recommendations(service_status, issues, has_camera, config, image_count):
    """Generate specific fix recommendations."""
    print("\n" + "="*50)
    print("RECOMMENDATIONS")
    print("="*50)
    
    priority_fixes = []
    
    # Camera access issues
    if not has_camera or "Camera access problems" in issues:
        priority_fixes.append({
            'priority': 1,
            'issue': 'Camera Access Problems',
            'commands': [
                'sudo systemctl stop bathyimager',
                'python3 tests/simple_camera_test.py',
                'sudo usermod -a -G video bathyimager',
                'sudo systemctl start bathyimager'
            ],
            'explanation': 'OpenCV cannot access camera with V4L2 backend. Test with different backends.'
        })
    
    # Frame rate issues
    if "Low frame rate" in str(issues):
        priority_fixes.append({
            'priority': 2,
            'issue': 'Low Frame Rate',
            'commands': [
                'sudo journalctl -u bathyimager | grep -E "(brightness|exposure|OVEREXPOSED)"',
                '# If overexposure detected, camera processing is slowing down capture'
            ],
            'explanation': 'Frame rate drop may be caused by camera processing delays or overexposure correction.'
        })
    
    # Overexposure issues
    if "overexposure" in str(issues).lower():
        priority_fixes.append({
            'priority': 1,
            'issue': 'Camera Overexposure (White Images)', 
            'commands': [
                'sudo systemctl stop bathyimager',
                'python3 tests/simple_camera_test.py',
                '# Check test images for white/overexposed content',
                '# If overexposed, may need manual exposure or lighting adjustment'
            ],
            'explanation': 'Camera is severely overexposed. May need lighting control or manual exposure settings.'
        })
    
    # Configuration issues
    if config is None:
        priority_fixes.append({
            'priority': 3,
            'issue': 'Configuration Problems',
            'commands': [
                'cd ~/BathyCat-Seabed-Imager',
                'ls -la config/',
                'cp config/bathyimager_config.json config/bathyimager_config.json.backup',
                '# Check config file exists and is readable'
            ],
            'explanation': 'Configuration file may be missing or corrupted.'
        })
    
    # Sort by priority
    priority_fixes.sort(key=lambda x: x['priority'])
    
    # Display recommendations
    if priority_fixes:
        for i, fix in enumerate(priority_fixes, 1):
            print(f"\n{i}. {fix['issue']} (Priority {fix['priority']})")
            print(f"   {fix['explanation']}")
            print("   Commands to run:")
            for cmd in fix['commands']:
                print(f"   $ {cmd}")
    else:
        print("\n✓ No critical issues detected!")
        print("Current status appears normal for indoor testing.")
    
    # General recommendations
    print(f"\nGENERAL NEXT STEPS:")
    print(f"1. Run simple camera test: python3 tests/simple_camera_test.py")
    print(f"2. Check service logs: sudo journalctl -u bathyimager -f")
    print(f"3. Test outdoors for GPS functionality")
    if image_count > 0:
        print(f"4. Check image quality in latest captures")

def main():
    """Run comprehensive diagnostic."""
    print("BathyCat Service Diagnostic")
    print("=" * 30)
    
    # Check service status
    service_status, issues = check_service_status()
    
    # Check camera hardware
    has_camera, camera_perms = check_camera_devices()
    
    # Check configuration
    config = check_config()
    
    # Analyze recent images
    image_count, recent_images = analyze_recent_images()
    
    # Generate recommendations
    generate_recommendations(service_status, issues, has_camera, config, image_count)

if __name__ == "__main__":
    main()