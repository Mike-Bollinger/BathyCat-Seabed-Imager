#!/usr/bin/env python3
"""
BathyCat System Check
====================

Quick system diagnostic to check hardware availability on Raspberry Pi.
Run this before the camera capture test.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, capture_output=True):
    """Run a shell command and return result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_python_packages():
    """Check if required Python packages are available"""
    print("Checking Python packages...")
    
    packages = ['cv2', 'numpy', 'PIL']
    results = {}
    
    for package in packages:
        try:
            __import__(package)
            results[package] = "✅ Available"
            print(f"  {package}: ✅ Available")
        except ImportError:
            results[package] = "❌ Missing"
            print(f"  {package}: ❌ Missing")
    
    return results

def check_cameras():
    """Check for available cameras"""
    print("\nChecking cameras...")
    
    # Check /dev/video* devices
    video_devices = list(Path("/dev").glob("video*"))
    if video_devices:
        print(f"  Found video devices: {[str(d) for d in video_devices]}")
    else:
        print("  No /dev/video* devices found")
    
    # Check lsusb for cameras
    success, stdout, stderr = run_command("lsusb")
    if success:
        camera_lines = [line for line in stdout.split('\n') if 'camera' in line.lower() or 'webcam' in line.lower()]
        if camera_lines:
            print("  USB cameras found:")
            for line in camera_lines:
                print(f"    {line}")
        else:
            print("  No USB cameras found in lsusb")
    else:
        print("  Could not run lsusb command")
    
    return len(video_devices) > 0

def check_storage():
    """Check storage availability"""
    print("\nChecking storage...")
    
    # Check for USB storage mount points
    usb_storage_found = False
    usb_paths = [
        "/media/usb-storage",
        "/media/bathycat", 
        "/mnt/usb",
        "/media/pi"  # Common Pi automount location
    ]
    
    for mount_point in usb_paths:
        path = Path(mount_point)
        if path.exists() and path.is_dir():
            print(f"  ✅ USB mount point found: {mount_point}")
            usb_storage_found = True
            
            # Check space on USB storage
            try:
                stat = os.statvfs(mount_point)
                free_bytes = stat.f_bavail * stat.f_frsize
                total_bytes = stat.f_blocks * stat.f_frsize
                free_gb = free_bytes / (1024**3)
                total_gb = total_bytes / (1024**3)
                used_percent = ((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                
                print(f"    Space: {free_gb:.2f}GB free of {total_gb:.2f}GB ({used_percent:.1f}% used)")
                
                if free_gb < 1:
                    print(f"    ⚠️  WARNING: Less than 1GB free space")
                
                # Test write permission
                test_file = path / "bathycat_test_write.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    print(f"    ✅ Write permission OK")
                except Exception as e:
                    print(f"    ❌ Cannot write: {e}")
                    
            except Exception as e:
                print(f"    Could not check disk space: {e}")
            break
    
    if not usb_storage_found:
        print("  ⚠️  No USB storage mount points found")
        print("  Will use local directory for testing")
    
    # Check current directory space as fallback
    current_dir = Path.cwd()
    try:
        stat = os.statvfs(current_dir)
        free_bytes = stat.f_bavail * stat.f_frsize
        free_gb = free_bytes / (1024**3)
        print(f"  Current directory free space: {free_gb:.2f} GB")
        
        if free_gb < 0.5:
            print(f"  ⚠️  WARNING: Less than 0.5GB free space in current directory")
            
    except Exception as e:
        print(f"  Could not check current directory space: {e}")
        free_gb = 1  # Assume OK if we can't check
    
    return usb_storage_found or free_gb > 0.5

def check_permissions():
    """Check file permissions"""
    print("\nChecking permissions...")
    
    # Check if we can write to current directory
    test_file = Path("test_write.tmp")
    try:
        test_file.write_text("test")
        test_file.unlink()
        print("  ✅ Write permission in current directory")
        write_ok = True
    except Exception as e:
        print(f"  ❌ Cannot write to current directory: {e}")
        write_ok = False
    
    # Check video device permissions
    video_devices = list(Path("/dev").glob("video*"))
    for device in video_devices:
        try:
            access_ok = os.access(device, os.R_OK)
            print(f"  {device}: {'✅ Readable' if access_ok else '❌ Not readable'}")
        except Exception as e:
            print(f"  {device}: ❌ Cannot check ({e})")
    
    return write_ok

def check_system_info():
    """Get basic system information"""
    print("\nSystem Information:")
    
    # OS info
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
        name_line = [line for line in os_info.split('\n') if line.startswith('PRETTY_NAME=')]
        if name_line:
            os_name = name_line[0].split('=')[1].strip('"')
            print(f"  OS: {os_name}")
    except:
        print("  OS: Unknown")
    
    # Python version
    print(f"  Python: {sys.version}")
    
    # CPU info
    success, stdout, stderr = run_command("cat /proc/cpuinfo | grep 'model name' | head -1")
    if success and stdout:
        cpu = stdout.split(':')[1].strip() if ':' in stdout else stdout
        print(f"  CPU: {cpu}")
    
    # Memory info
    success, stdout, stderr = run_command("free -h | grep Mem:")
    if success and stdout:
        mem_info = stdout.split()
        if len(mem_info) >= 2:
            total_mem = mem_info[1]
            print(f"  Memory: {total_mem}")

def create_test_config():
    """Create a test configuration file"""
    print("\nCreating test configuration...")
    
    config = {
        "test_mode": True,
        "gps_enabled": False,
        "camera": {
            "device_index": 0,
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "quality": 95
        },
        "capture": {
            "target_fps": 2.0,
            "duration": 30
        },
        "storage": {
            "base_path": "./test_images",
            "create_session_dirs": False
        }
    }
    
    config_file = Path("test_config.json")
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"  ✅ Created: {config_file.absolute()}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create config: {e}")
        return False

def main():
    print("BathyCat System Check")
    print("====================")
    
    # Run all checks
    python_ok = all("Available" in status for status in check_python_packages().values())
    camera_ok = check_cameras()
    storage_ok = check_storage()
    permissions_ok = check_permissions()
    
    check_system_info()
    config_ok = create_test_config()
    
    # Summary
    print("\n" + "="*50)
    print("SYSTEM CHECK SUMMARY")
    print("="*50)
    
    checks = [
        ("Python packages", python_ok),
        ("Camera devices", camera_ok),
        ("Storage space", storage_ok),
        ("Permissions", permissions_ok),
        ("Test config", config_ok)
    ]
    
    all_good = True
    for check_name, status in checks:
        icon = "✅" if status else "❌"
        print(f"{icon} {check_name}")
        if not status:
            all_good = False
    
    print("\n" + "="*50)
    
    if all_good:
        print("🎉 System ready for camera testing!")
        print("\nNext steps:")
        print("1. Run camera test: python3 scripts/test_camera_capture.py")
        print("2. Check captured images in: ./test_images/")
    else:
        print("⚠️  Some issues found. Please address them before testing.")
        print("\nCommon fixes:")
        if not python_ok:
            print("- Install missing packages: pip install opencv-python numpy pillow")
        if not camera_ok:
            print("- Connect a USB camera")
            print("- Check camera permissions: sudo usermod -a -G video $USER")
        if not permissions_ok:
            print("- Add user to video group: sudo usermod -a -G video $USER")
            print("- Logout and login again")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
