#!/usr/bin/env python3
"""
Targeted Camera Fix for H264 USB Camera
This script tests specific solutions for H264 USB cameras that work with fswebcam but not OpenCV
"""

import cv2
import sys
import os

def test_mjpeg_format():
    """Test forcing MJPEG format which is more compatible with OpenCV"""
    print("=== Testing MJPEG Format Fix ===")
    
    try:
        # Try device path with MJPEG format
        cap = cv2.VideoCapture("/dev/video0")
        if cap.isOpened():
            print("✅ Camera opened with device path")
            
            # Force MJPEG format
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            # Set lower resolution first
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Verify settings
            actual_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            fourcc_str = "".join([chr((actual_fourcc >> 8 * i) & 0xFF) for i in range(4)])
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"📹 Camera settings:")
            print(f"   Format: {fourcc_str}")
            print(f"   Resolution: {width}x{height}")
            print(f"   FPS: {fps}")
            
            # Try to capture frames
            print("\n🔍 Testing frame capture...")
            for i in range(5):
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ Frame {i+1}: {frame.shape} - Success!")
                    if i == 0:  # Save first frame for verification
                        cv2.imwrite("/tmp/opencv_test_frame.jpg", frame)
                        print("💾 Test frame saved to /tmp/opencv_test_frame.jpg")
                else:
                    print(f"❌ Frame {i+1}: Failed")
                    break
            
            cap.release()
            return True
            
        else:
            print("❌ Failed to open camera with device path")
            return False
            
    except Exception as e:
        print(f"❌ Exception during MJPEG test: {e}")
        return False

def test_gstreamer_solution():
    """Test GStreamer pipeline solution"""
    print("\n=== Testing GStreamer Solution ===")
    
    # Test if GStreamer is available
    try:
        pipeline = "v4l2src device=/dev/video0 ! video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! videoconvert ! appsink"
        print(f"🔍 Testing pipeline: {pipeline}")
        
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            print("✅ GStreamer pipeline opened successfully")
            
            # Test frame capture
            for i in range(3):
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ GStreamer frame {i+1}: {frame.shape}")
                    if i == 0:
                        cv2.imwrite("/tmp/gstreamer_test_frame.jpg", frame)
                        print("💾 GStreamer test frame saved")
                else:
                    print(f"❌ GStreamer frame {i+1}: Failed")
                    break
            
            cap.release()
            return pipeline
        else:
            print("❌ GStreamer pipeline failed to open")
            return None
            
    except Exception as e:
        print(f"❌ GStreamer exception: {e}")
        return None

def create_updated_camera_config():
    """Create camera configuration based on successful method"""
    print("\n=== Creating Camera Configuration ===")
    
    # Test MJPEG first
    mjpeg_works = test_mjpeg_format()
    
    # Test GStreamer as fallback
    gstreamer_pipeline = test_gstreamer_solution()
    
    if mjpeg_works:
        print("\n✅ MJPEG solution works! Update camera_controller.py:")
        print("""
# In camera_controller.py, replace camera initialization with:
def _open_camera_with_mjpeg(self):
    try:
        self.camera = cv2.VideoCapture("/dev/video0")
        if self.camera.isOpened():
            # Force MJPEG format
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)
            return True
        return False
    except Exception as e:
        self.logger.error(f"MJPEG camera open failed: {e}")
        return False
        """)
        return "mjpeg"
        
    elif gstreamer_pipeline:
        print(f"\n✅ GStreamer solution works! Update camera_controller.py:")
        print(f"""
# In camera_controller.py, replace camera initialization with:
GSTREAMER_PIPELINE = "{gstreamer_pipeline}"

def _open_camera_with_gstreamer(self):
    try:
        self.camera = cv2.VideoCapture(GSTREAMER_PIPELINE, cv2.CAP_GSTREAMER)
        return self.camera.isOpened()
    except Exception as e:
        self.logger.error(f"GStreamer camera open failed: {{e}}")
        return False
        """)
        return "gstreamer"
    else:
        print("\n❌ No working solution found")
        return None

def main():
    print("🔧 BathyCat H264 USB Camera Fix")
    print("=" * 50)
    
    solution = create_updated_camera_config()
    
    if solution:
        print(f"\n🎉 Solution found: {solution}")
        print("\nNext steps:")
        print("1. Apply the suggested code changes to camera_controller.py")
        print("2. Test with: python3 debug/simple_camera_test.py")
        print("3. Run BathyCat: python3 src/bathycat_imager.py --config /etc/bathycat/config.json --verbose")
    else:
        print("\n❌ No solution found. The camera may need different drivers or settings.")
    
    print("\n" + "=" * 50)
    print("🏁 Camera fix analysis complete!")

if __name__ == "__main__":
    main()
