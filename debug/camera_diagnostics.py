#!/usr/bin/env python3
"""
Camera Diagnostics Script for BathyCat
Comprehensive camera device testing and troubleshooting
"""

import cv2
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def check_device_permissions():
    """Check camera device permissions and access"""
    print("=== Camera Device Analysis ===")
    
    # List all video devices
    retcode, stdout, stderr = run_command("ls -la /dev/video*")
    if retcode == 0:
        print("📹 Video devices found:")
        print(stdout)
    else:
        print("❌ No video devices found or permission denied")
        print(f"Error: {stderr}")
    
    # Check current user and groups
    retcode, stdout, stderr = run_command("whoami")
    current_user = stdout.strip() if retcode == 0 else "unknown"
    print(f"\n👤 Current user: {current_user}")
    
    retcode, stdout, stderr = run_command("groups")
    if retcode == 0:
        print(f"👥 User groups: {stdout}")
    
    # Check if user is in video group
    retcode, stdout, stderr = run_command("groups | grep video")
    if retcode == 0:
        print("✅ User is in 'video' group")
    else:
        print("❌ User is NOT in 'video' group - this is likely the issue!")
        print("   Fix with: sudo usermod -a -G video $USER")
    
    return current_user

def test_v4l2_tools():
    """Test Video4Linux tools"""
    print("\n=== V4L2 Tools Testing ===")
    
    # Check if v4l2-ctl exists
    retcode, stdout, stderr = run_command("which v4l2-ctl")
    if retcode != 0:
        print("❌ v4l2-ctl not found - install with: sudo apt install v4l-utils")
        return
    
    # List devices with v4l2-ctl
    retcode, stdout, stderr = run_command("v4l2-ctl --list-devices")
    if retcode == 0:
        print("📹 V4L2 devices:")
        print(stdout)
    else:
        print(f"❌ v4l2-ctl failed: {stderr}")
    
    # Get detailed info for /dev/video0
    retcode, stdout, stderr = run_command("v4l2-ctl -d /dev/video0 --all")
    if retcode == 0:
        print("\n📹 /dev/video0 detailed info:")
        print(stdout[:1000] + "..." if len(stdout) > 1000 else stdout)
    else:
        print(f"❌ Cannot access /dev/video0: {stderr}")

def test_fswebcam():
    """Test fswebcam functionality"""
    print("\n=== fswebcam Testing ===")
    
    # Check if fswebcam exists
    retcode, stdout, stderr = run_command("which fswebcam")
    if retcode != 0:
        print("❌ fswebcam not found")
        return
    
    # Test fswebcam with device info
    test_image = "/tmp/camera_diagnostic_test.jpg"
    retcode, stdout, stderr = run_command(f"fswebcam -d /dev/video0 --no-banner -r 1920x1080 {test_image}")
    if retcode == 0:
        print("✅ fswebcam works successfully")
        # Check if file was created
        if os.path.exists(test_image):
            file_size = os.path.getsize(test_image)
            print(f"📷 Test image created: {file_size} bytes")
            os.remove(test_image)  # Clean up
        else:
            print("❌ fswebcam ran but no image file created")
    else:
        print(f"❌ fswebcam failed: {stderr}")

def test_opencv_methods():
    """Test different OpenCV camera access methods"""
    print("\n=== OpenCV Camera Access Testing ===")
    
    methods_to_test = [
        ("Index 0", 0),
        ("Device path", "/dev/video0"),
        ("V4L2 backend index", cv2.CAP_V4L2 + 0),
        ("V4L2 backend path", cv2.CAP_V4L2, "/dev/video0"),
    ]
    
    for name, *args in methods_to_test:
        print(f"\n--- Testing {name} ---")
        try:
            if len(args) == 1:
                cap = cv2.VideoCapture(args[0])
            else:
                cap = cv2.VideoCapture(args[1], args[0])
            
            if cap.isOpened():
                print(f"✅ {name} - Camera opened successfully")
                
                # Get camera properties
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"   Resolution: {int(width)}x{int(height)}")
                print(f"   FPS: {fps}")
                
                # Try to read a frame
                ret, frame = cap.read()
                if ret:
                    print(f"✅ Frame capture successful: {frame.shape}")
                else:
                    print("❌ Frame capture failed")
                
                cap.release()
            else:
                print(f"❌ {name} - Failed to open camera")
                
        except Exception as e:
            print(f"❌ {name} - Exception: {e}")

def check_camera_processes():
    """Check for processes using the camera"""
    print("\n=== Camera Process Check ===")
    
    # Check for processes using video devices
    retcode, stdout, stderr = run_command("lsof /dev/video* 2>/dev/null")
    if retcode == 0 and stdout:
        print("🔒 Processes using video devices:")
        print(stdout)
    else:
        print("✅ No processes currently using video devices")
    
    # Check for BathyCat processes
    retcode, stdout, stderr = run_command("ps aux | grep -i bathycat | grep -v grep")
    if retcode == 0 and stdout:
        print("\n🔍 BathyCat processes running:")
        print(stdout)
    else:
        print("\n✅ No BathyCat processes running")

def suggest_fixes(current_user):
    """Suggest potential fixes based on findings"""
    print("\n=== Suggested Fixes ===")
    
    print("1. Add user to video group:")
    print(f"   sudo usermod -a -G video {current_user}")
    print("   Then log out and back in")
    
    print("\n2. Set camera device permissions:")
    print("   sudo chmod 666 /dev/video0")
    
    print("\n3. Check if camera is bound to correct driver:")
    print("   dmesg | grep -i usb | grep -i video")
    
    print("\n4. Install missing tools if needed:")
    print("   sudo apt update")
    print("   sudo apt install v4l-utils fswebcam")
    
    print("\n5. Reboot system if permissions don't take effect:")
    print("   sudo reboot")

def main():
    """Main diagnostic routine"""
    print("🔍 BathyCat Camera Diagnostic Tool")
    print("=" * 50)
    
    current_user = check_device_permissions()
    test_v4l2_tools()
    test_fswebcam()
    check_camera_processes()
    test_opencv_methods()
    suggest_fixes(current_user)
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostic complete!")

if __name__ == "__main__":
    main()
