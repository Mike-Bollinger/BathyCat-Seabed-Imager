#!/usr/bin/env python3
"""
Camera Format Analysis for BathyCat
Test different formats and methods to match fswebcam success
"""

import cv2
import subprocess
import sys
import time

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def test_fswebcam_formats():
    """Test what formats fswebcam is using"""
    print("=== fswebcam Format Analysis ===")
    
    # Get detailed fswebcam info
    retcode, stdout, stderr = run_command("fswebcam -d /dev/video0 --list-formats")
    if retcode == 0:
        print("📹 Available formats from fswebcam:")
        print(stdout)
    else:
        print(f"❌ fswebcam format listing failed: {stderr}")
    
    # Test fswebcam with verbose output
    print("\n--- fswebcam verbose test ---")
    retcode, stdout, stderr = run_command("fswebcam -d /dev/video0 --verbose --no-banner -r 640x480 /tmp/fswebcam_test.jpg")
    if retcode == 0:
        print("✅ fswebcam verbose output:")
        print(stdout)
        print(stderr if stderr else "No stderr")
    else:
        print(f"❌ fswebcam verbose failed: {stderr}")

def test_v4l2_formats():
    """Get detailed format information from v4l2"""
    print("\n=== V4L2 Format Analysis ===")
    
    # List supported formats
    retcode, stdout, stderr = run_command("v4l2-ctl -d /dev/video0 --list-formats-ext")
    if retcode == 0:
        print("📹 Supported formats:")
        print(stdout)
    else:
        print(f"❌ v4l2 format listing failed: {stderr}")

def test_opencv_with_formats():
    """Test OpenCV with specific formats and settings"""
    print("\n=== OpenCV Format Testing ===")
    
    # Common formats to test
    formats_to_test = [
        ("MJPG", cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')),
        ("YUYV", cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV')),
        ("H264", cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264')),
        ("Default", None, None),
    ]
    
    resolutions_to_test = [
        (640, 480),
        (1280, 720),
        (1920, 1080),
    ]
    
    for fmt_name, prop, fourcc in formats_to_test:
        print(f"\n--- Testing format: {fmt_name} ---")
        
        for width, height in resolutions_to_test:
            print(f"  🔍 Resolution: {width}x{height}")
            
            try:
                # Try different access methods
                for method_name, device, backend in [
                    ("Device path", "/dev/video0", None),
                    ("Device path V4L2", "/dev/video0", cv2.CAP_V4L2),
                    ("Index", 0, None),
                    ("Index V4L2", 0, cv2.CAP_V4L2),
                ]:
                    try:
                        if backend is not None:
                            cap = cv2.VideoCapture(device, backend)
                        else:
                            cap = cv2.VideoCapture(device)
                        
                        if cap.isOpened():
                            # Set format if specified
                            if prop and fourcc:
                                cap.set(prop, fourcc)
                            
                            # Set resolution
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                            
                            # Try to read a frame
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                actual_width = frame.shape[1]
                                actual_height = frame.shape[0]
                                print(f"    ✅ {method_name}: {actual_width}x{actual_height}")
                                cap.release()
                                return True  # Success! Stop testing
                            else:
                                print(f"    ❌ {method_name}: Opened but no frame")
                        else:
                            print(f"    ❌ {method_name}: Failed to open")
                        
                        cap.release()
                        
                    except Exception as e:
                        print(f"    ❌ {method_name}: Exception {e}")
                        
            except Exception as e:
                print(f"  ❌ Format {fmt_name} exception: {e}")
    
    return False

def test_gstreamer_pipeline():
    """Test if GStreamer pipeline works with OpenCV"""
    print("\n=== GStreamer Pipeline Testing ===")
    
    # Common GStreamer pipelines for USB cameras
    pipelines = [
        "v4l2src device=/dev/video0 ! videoconvert ! appsink",
        "v4l2src device=/dev/video0 ! video/x-raw,format=YUY2,width=640,height=480 ! videoconvert ! appsink",
        "v4l2src device=/dev/video0 ! video/x-raw,format=MJPG,width=640,height=480 ! jpegdec ! videoconvert ! appsink",
        "v4l2src device=/dev/video0 ! image/jpeg,width=640,height=480 ! jpegdec ! videoconvert ! appsink",
    ]
    
    for pipeline in pipelines:
        print(f"🔍 Testing pipeline: {pipeline}")
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ GStreamer success: {frame.shape}")
                    cap.release()
                    return pipeline
                else:
                    print("❌ GStreamer: Opened but no frame")
            else:
                print("❌ GStreamer: Failed to open")
            cap.release()
        except Exception as e:
            print(f"❌ GStreamer: Exception {e}")
    
    return None

def suggest_fix():
    """Suggest a fix based on findings"""
    print("\n=== Suggested Solution ===")
    print("Based on the analysis, try these solutions in BathyCat:")
    print("1. Force MJPEG format in camera initialization")
    print("2. Use GStreamer pipeline if available")
    print("3. Try lower resolution first (640x480)")
    print("4. Use device path instead of index")

def main():
    print("🔍 BathyCat Camera Format Analysis")
    print("=" * 50)
    
    test_fswebcam_formats()
    test_v4l2_formats()
    
    success = test_opencv_with_formats()
    if not success:
        working_pipeline = test_gstreamer_pipeline()
        if working_pipeline:
            print(f"\n✅ Working GStreamer pipeline found: {working_pipeline}")
        else:
            print("\n❌ No working OpenCV method found")
    
    suggest_fix()
    
    print("\n" + "=" * 50)
    print("🏁 Format analysis complete!")

if __name__ == "__main__":
    main()
