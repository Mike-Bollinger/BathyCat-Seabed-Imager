#!/usr/bin/env python3
"""
BathyCat Camera Test Stream
==========================

Test script that mirrors the camera controller setup and streams images
for verification over SSH connection. Displays image info and optionally
saves test images.

Usage:
    python camera_test_stream.py [options]
    
Options:
    --save-images    Save test images to /tmp/camera_test/
    --duration SEC   Test duration in seconds (default: 30)
    --fps RATE       Capture rate in Hz (default: 4)
    --verbose        Show detailed frame information
"""

import asyncio
import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from config import Config
    from camera_controller import CameraController
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the BathyCat project directory")
    sys.exit(1)


class CameraTestStreamer:
    """Test camera streaming with detailed diagnostics."""
    
    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Test parameters
        self.duration = args.duration
        self.fps = args.fps
        self.frame_interval = 1.0 / self.fps
        self.save_images = args.save_images
        
        # Statistics
        self.stats = {
            'total_frames': 0,
            'valid_frames': 0,
            'blank_frames': 0,
            'error_frames': 0,
            'start_time': None,
            'frame_sizes': [],
            'frame_times': []
        }
        
        # Setup save directory if needed
        if self.save_images:
            self.save_dir = Path("/tmp/camera_test")
            self.save_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 Saving test images to: {self.save_dir}")
    
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.args.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def analyze_frame(self, frame):
        """Analyze frame properties and return diagnostics."""
        if frame is None:
            return {"valid": False, "reason": "None frame"}
        
        try:
            info = {
                "valid": True,
                "shape": frame.shape,
                "dtype": str(frame.dtype),
                "size_bytes": frame.nbytes,
                "channels": frame.shape[2] if len(frame.shape) > 2 else 1,
                "min_val": int(frame.min()),
                "max_val": int(frame.max()),
                "mean_val": float(frame.mean()),
                "is_blank": frame.max() == 0,
                "is_uniform": frame.std() < 1.0
            }
            
            # Check if image has reasonable content
            if info["is_blank"]:
                info["valid"] = False
                info["reason"] = "Completely black frame"
            elif info["is_uniform"]:
                info["valid"] = False
                info["reason"] = f"Uniform frame (std: {frame.std():.2f})"
            elif info["max_val"] < 10:
                info["valid"] = False
                info["reason"] = f"Very dark frame (max: {info['max_val']})"
            
            return info
            
        except Exception as e:
            return {"valid": False, "reason": f"Analysis error: {e}"}
    
    def print_frame_info(self, frame_num, frame_info, capture_time):
        """Print detailed frame information."""
        status = "✅" if frame_info["valid"] else "❌"
        
        if frame_info["valid"]:
            shape_str = f"{frame_info['shape']}"
            stats_str = f"min/max/mean: {frame_info['min_val']}/{frame_info['max_val']}/{frame_info['mean_val']:.1f}"
            size_str = f"{frame_info['size_bytes']/1024:.1f}KB"
            
            print(f"{status} Frame {frame_num:3d}: {shape_str} {stats_str} ({size_str}) [{capture_time:.3f}s]")
            
            if self.args.verbose:
                print(f"    Channels: {frame_info['channels']}, dtype: {frame_info['dtype']}")
                print(f"    Std dev: {frame_info.get('std_dev', 'N/A'):.2f}")
        else:
            print(f"{status} Frame {frame_num:3d}: INVALID - {frame_info['reason']} [{capture_time:.3f}s]")
    
    def save_test_frame(self, frame, frame_num, frame_info):
        """Save frame for inspection."""
        if not self.save_images or not frame_info["valid"]:
            return
        
        try:
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            filename = f"test_frame_{frame_num:03d}_{timestamp}.jpg"
            filepath = self.save_dir / filename
            
            # Save with high quality for inspection
            cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            if frame_num % 10 == 1:  # Log every 10th save
                self.logger.info(f"💾 Saved frame {frame_num} to {filename}")
                
        except Exception as e:
            self.logger.error(f"Failed to save frame {frame_num}: {e}")
    
    async def run_camera_test(self):
        """Run the camera test stream."""
        self.logger.info("🎬 Starting BathyCat Camera Test Stream")
        self.logger.info(f"📊 Test parameters: {self.fps} Hz for {self.duration}s")
        
        try:
            # Load config and setup camera
            config = Config()
            self.logger.info("✅ Configuration loaded")
            
            camera = CameraController(config)
            self.logger.info("✅ Camera controller created")
            
            # Initialize camera
            if not await camera.initialize():
                self.logger.error("❌ Camera initialization failed")
                return False
            
            self.logger.info("✅ Camera initialized - starting capture test")
            self.logger.info(f"🎯 Target: {self.fps} Hz ({self.frame_interval:.3f}s interval)")
            print("=" * 80)
            
            # Start capture loop
            self.stats['start_time'] = time.time()
            next_capture = self.stats['start_time']
            frame_num = 0
            
            while time.time() - self.stats['start_time'] < self.duration:
                current_time = time.time()
                
                if current_time >= next_capture:
                    frame_start = time.time()
                    frame_num += 1
                    
                    # Capture frame using same method as main app
                    frame = camera.capture_image()
                    capture_duration = time.time() - frame_start
                    
                    # Analyze frame
                    frame_info = self.analyze_frame(frame)
                    
                    # Update statistics
                    self.stats['total_frames'] += 1
                    self.stats['frame_times'].append(capture_duration)
                    
                    if frame_info["valid"]:
                        self.stats['valid_frames'] += 1
                        self.stats['frame_sizes'].append(frame_info['size_bytes'])
                    elif frame_info.get("is_blank"):
                        self.stats['blank_frames'] += 1
                    else:
                        self.stats['error_frames'] += 1
                    
                    # Print frame info
                    self.print_frame_info(frame_num, frame_info, capture_duration)
                    
                    # Save frame if requested
                    self.save_test_frame(frame, frame_num, frame_info)
                    
                    # Print periodic stats
                    if frame_num % 20 == 0:
                        elapsed = current_time - self.stats['start_time']
                        actual_fps = self.stats['total_frames'] / elapsed
                        valid_pct = (self.stats['valid_frames'] / self.stats['total_frames']) * 100
                        
                        print("=" * 80)
                        print(f"📊 Stats after {frame_num} frames ({elapsed:.1f}s):")
                        print(f"    Actual FPS: {actual_fps:.2f} (target: {self.fps})")
                        print(f"    Valid frames: {self.stats['valid_frames']}/{self.stats['total_frames']} ({valid_pct:.1f}%)")
                        print(f"    Blank frames: {self.stats['blank_frames']}")
                        print(f"    Error frames: {self.stats['error_frames']}")
                        if self.stats['frame_times']:
                            avg_capture_time = sum(self.stats['frame_times'][-20:]) / min(20, len(self.stats['frame_times']))
                            print(f"    Avg capture time: {avg_capture_time*1000:.1f}ms")
                        print("=" * 80)
                    
                    # Schedule next capture
                    next_capture += self.frame_interval
                
                # Small sleep for timing
                await asyncio.sleep(0.001)
            
            # Final statistics
            await self.print_final_stats()
            
            # Cleanup
            await camera.shutdown()
            self.logger.info("✅ Camera test completed successfully")
            return True
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Test interrupted by user")
            return True
        except Exception as e:
            self.logger.error(f"❌ Camera test failed: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def print_final_stats(self):
        """Print comprehensive final statistics."""
        total_time = time.time() - self.stats['start_time']
        actual_fps = self.stats['total_frames'] / total_time
        
        print("\n" + "=" * 80)
        print("🎉 CAMERA TEST RESULTS")
        print("=" * 80)
        print(f"Test Duration:     {total_time:.2f} seconds")
        print(f"Target FPS:        {self.fps}")
        print(f"Actual FPS:        {actual_fps:.2f}")
        print(f"Performance:       {(actual_fps/self.fps)*100:.1f}% of target")
        print()
        print(f"Total Frames:      {self.stats['total_frames']}")
        print(f"Valid Frames:      {self.stats['valid_frames']} ({(self.stats['valid_frames']/self.stats['total_frames'])*100:.1f}%)")
        print(f"Blank Frames:      {self.stats['blank_frames']}")
        print(f"Error Frames:      {self.stats['error_frames']}")
        print()
        
        if self.stats['frame_times']:
            avg_time = sum(self.stats['frame_times']) / len(self.stats['frame_times'])
            min_time = min(self.stats['frame_times'])
            max_time = max(self.stats['frame_times'])
            print(f"Capture Time:      avg={avg_time*1000:.1f}ms, min={min_time*1000:.1f}ms, max={max_time*1000:.1f}ms")
        
        if self.stats['frame_sizes']:
            avg_size = sum(self.stats['frame_sizes']) / len(self.stats['frame_sizes'])
            print(f"Avg Frame Size:    {avg_size/1024:.1f} KB")
        
        print("=" * 80)
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if self.stats['valid_frames'] / self.stats['total_frames'] < 0.8:
            print("⚠️  Low valid frame rate - check camera connection and settings")
        if actual_fps < self.fps * 0.9:
            print("⚠️  Below target FPS - consider reducing capture rate or optimizing code")
        if self.stats['blank_frames'] > 0:
            print("⚠️  Blank frames detected - camera may need warm-up time or buffer adjustment")
        if actual_fps >= self.fps * 0.95 and self.stats['valid_frames'] / self.stats['total_frames'] > 0.95:
            print("✅ Excellent performance - camera is working optimally!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BathyCat Camera Test Stream",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python camera_test_stream.py                    # Basic 30s test at 4 Hz
    python camera_test_stream.py --save-images      # Save test images
    python camera_test_stream.py --fps 2 --duration 60  # 2 Hz for 60 seconds
    python camera_test_stream.py --verbose          # Detailed frame info
        """
    )
    
    parser.add_argument(
        "--save-images", 
        action="store_true",
        help="Save test images to /tmp/camera_test/"
    )
    parser.add_argument(
        "--duration", 
        type=float, 
        default=30.0,
        help="Test duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--fps", 
        type=float, 
        default=4.0,
        help="Capture rate in Hz (default: 4)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed frame information"
    )
    
    args = parser.parse_args()
    
    # Create and run test
    streamer = CameraTestStreamer(args)
    
    print(f"""
🎬 BathyCat Camera Test Stream
=============================
Duration: {args.duration}s
FPS: {args.fps} Hz
Save Images: {'Yes' if args.save_images else 'No'}
Verbose: {'Yes' if args.verbose else 'No'}

Starting in 2 seconds... (Ctrl+C to stop early)
""")
    
    try:
        time.sleep(2)
        success = asyncio.run(streamer.run_camera_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()