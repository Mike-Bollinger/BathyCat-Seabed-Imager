#!/usr/bin/env python3
"""
BathyCat System Test Script
==========================

Quick test to verify all components are working properly.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}")
            return True
        else:
            print(f"❌ {description}: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description}: {e}")
        return False

def test_python_imports():
    """Test Python module imports."""
    print("\n📦 Testing Python Dependencies...")
    
    modules = ['cv2', 'numpy', 'serial', 'PIL', 'psutil']
    all_passed = True
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            all_passed = False
    
    return all_passed

def test_hardware():
    """Test hardware components."""
    print("\n🔌 Testing Hardware...")
    
    tests = [
        ("lsusb | grep -i camera", "USB Camera detection"),
        ("ls /dev/video* 2>/dev/null", "Video devices"),
        ("ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null", "USB Serial devices (GPS)"),
        ("lsblk | grep -E 'sd[a-z]'", "USB Storage devices")
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    return any(results)  # At least one hardware component should be present

def test_usb_storage():
    """Test USB storage setup."""
    print("\n💾 Testing USB Storage...")
    
    mount_point = Path("/media/usb-storage")
    bathycat_dir = mount_point / "bathycat"
    
    if not mount_point.exists():
        print("❌ USB storage mount point not found")
        return False
    
    if not bathycat_dir.exists():
        print("❌ BathyCat directory structure not found")
        return False
    
    # Test write access
    test_file = bathycat_dir / ".test_write"
    try:
        test_file.write_text("test")
        test_file.unlink()
        print("✅ USB storage write access")
        return True
    except Exception as e:
        print(f"❌ USB storage write access: {e}")
        return False

def test_bathycat_modules():
    """Test BathyCat module imports."""
    print("\n🐱 Testing BathyCat Modules...")
    
    # Add src to path
    src_dir = Path(__file__).parent / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
    
    modules = [
        'config',
        'camera_controller',
        'gps_controller', 
        'image_processor',
        'storage_manager',
        'bathycat_imager'
    ]
    
    all_passed = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            all_passed = False
    
    return all_passed

def test_service():
    """Test systemd service."""
    print("\n🔧 Testing Service...")
    
    tests = [
        ("systemctl status bathycat-imager", "Service status"),
        ("ls /etc/systemd/system/bathycat-imager.service", "Service file exists")
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    return any(results)  # At least one should pass

def test_camera_fswebcam():
    """Test camera with fswebcam."""
    print("\n📷 Testing Camera with fswebcam...")
    
    test_image = "/tmp/bathycat_camera_test.jpg"
    cmd = f"fswebcam -d /dev/video0 --no-banner -r 640x480 {test_image}"
    
    if run_command(cmd, "fswebcam capture"):
        if os.path.exists(test_image):
            os.unlink(test_image)  # Clean up
            return True
        else:
            print("❌ fswebcam: No image file created")
            return False
    else:
        print("❌ fswebcam: Command failed")
        return False

def main():
    """Run all tests."""
    print("🧪 BathyCat System Test")
    print("=" * 30)
    
    tests = [
        ("Python Dependencies", test_python_imports),
        ("Hardware Components", test_hardware),
        ("USB Storage", test_usb_storage),
        ("BathyCat Modules", test_bathycat_modules),
        ("System Service", test_service),
        ("Camera (fswebcam)", test_camera_fswebcam)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}: Test failed with error: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 20)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed >= len(results) - 1:  # Allow one failure
        print("\n🎉 System is ready! BathyCat should work properly.")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())