#!/usr/bin/env python3
"""
OpenCV vs fswebcam Comparison Test
Detailed analysis of why fswebcam works but OpenCV doesn't
"""

import cv2
import subprocess
import sys

def get_opencv_info():
    """Get detailed OpenCV build information"""
    print("=== OpenCV Build Information ===")
    print(f"OpenCV Version: {cv2.__version__}")
    print(f"OpenCV Build Info:")
    print(cv2.getBuildInformation())

def test_basic_opencv():
    """Test basic OpenCV functionality"""
    print("\n=== Basic OpenCV Tests ===")
    
    # Test if OpenCV can list video backends
    backends = []
    for backend_name, backend_id in [
        ("V4L2", cv2.CAP_V4L2),
        ("GSTREAMER", cv2.CAP_GSTREAMER),
        ("FFMPEG", cv2.CAP_FFMPEG),
        ("ANY", cv2.CAP_ANY),
    ]:
        try:
            # Try to create a dummy capture to test backend
            cap = cv2.VideoCapture()
            if cap.open(0, backend_id):
                backends.append(f"✅ {backend_name} (ID: {backend_id})")
                cap.release()  # Don't leave it open
            else:
                backends.append(f"❌ {backend_name} (ID: {backend_id})")
        except Exception as e:
            backends.append(f"❌ {backend_name} - Exception: {e}")
    
    print("📹 Available backends:")
    for backend in backends:
        print(f"   {backend}")

def compare_device_access():
    """Compare different device access methods"""
    print("\n=== Device Access Comparison ===")
    
    # Check device file directly
    try:
        with open("/dev/video0", "rb") as f:
            print("✅ Can open /dev/video0 for reading")
    except PermissionError:
        print("❌ Permission denied to read /dev/video0")
    except Exception as e:
        print(f"❌ Cannot open /dev/video0: {e}")
    
    # Test fswebcam verbose
    print("\n--- fswebcam detailed test ---")
    cmd = ["fswebcam", "-d", "/dev/video0", "--verbose", "--list-formats"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("fswebcam --list-formats output:")
        print(result.stdout)
        if result.stderr:
            print("fswebcam stderr:")
            print(result.stderr)
    except Exception as e:
        print(f"fswebcam error: {e}")

def test_opencv_debug():
    """Test OpenCV with maximum debugging"""
    print("\n=== OpenCV Debug Test ===")
    
    # Enable OpenCV debug logging
    cv2.setLogLevel(cv2.LOG_LEVEL_DEBUG)
    
    print("🔍 Testing with debug logging enabled...")
    
    # Try the simplest possible OpenCV access
    try:
        print("Attempting cv2.VideoCapture('/dev/video0')...")
        cap = cv2.VideoCapture("/dev/video0")
        
        print(f"isOpened(): {cap.isOpened()}")
        
        if cap.isOpened():
            print("✅ OpenCV opened camera successfully!")
            
            # Get properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  
            fps = cap.get(cv2.CAP_PROP_FPS)
            format_val = cap.get(cv2.CAP_PROP_FOURCC)
            
            print(f"Properties: {width}x{height}, {fps} FPS, format: {format_val}")
            
            # Try to read
            ret, frame = cap.read()
            print(f"Frame read: ret={ret}, frame shape={frame.shape if ret else 'None'}")
            
        else:
            print("❌ OpenCV failed to open camera")
        
        cap.release()
        
    except Exception as e:
        print(f"❌ OpenCV exception: {e}")
        import traceback
        traceback.print_exc()

def suggest_solutions():
    """Suggest potential solutions based on findings"""
    print("\n=== Potential Solutions ===")
    
    solutions = [
        "1. Use fswebcam wrapper (call fswebcam from Python)",
        "2. Rebuild OpenCV with proper V4L2 support",
        "3. Install different OpenCV version (opencv-python vs opencv-contrib-python)",
        "4. Use different camera access library (v4l2py, pyv4l2)",
        "5. Create GStreamer pipeline that works",
        "6. Check if camera needs specific kernel module or firmware"
    ]
    
    for solution in solutions:
        print(solution)

def main():
    print("🔍 OpenCV vs fswebcam Deep Analysis")
    print("=" * 60)
    
    get_opencv_info()
    test_basic_opencv()
    compare_device_access()
    test_opencv_debug()
    suggest_solutions()
    
    print("\n" + "=" * 60)
    print("🏁 Analysis complete!")

if __name__ == "__main__":
    main()
