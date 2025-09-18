#!/usr/bin/env python3
"""
Advanced NumPy Boolean Debug Tool
================================

This script adds comprehensive debugging to identify exactly where
the NumPy boolean evaluation error is occurring.
"""

import traceback
import sys
from pathlib import Path

def add_detailed_debugging():
    """Add line-by-line debugging to the capture loop."""
    
    bathycat_file = Path("src/bathycat_imager.py")
    
    if not bathycat_file.exists():
        print("Error: src/bathycat_imager.py not found")
        return False
    
    # Read current content
    with open(bathycat_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = f"src/bathycat_imager.py.debug_backup"
    with open(backup_file, 'w') as f:
        f.write(content)
    
    # Replace the capture loop with a heavily debugged version
    old_loop = """    async def _capture_loop(self):
        \"\"\"Main image capture loop.\"\"\"
        frame_interval = 1.0 / self.config.capture_fps
        next_capture = time.time()
        
        self.logger.debug(f"Starting capture loop with {self.config.capture_fps} FPS")
        
        while self.running and self.capture_active:
            try:
                current_time = time.time()
                
                if current_time >= next_capture:
                    self.logger.debug("Attempting image capture...")
                    
                    # Capture image
                    image_data = self.camera.capture_image()
                    self.logger.debug(f"Capture result type: {type(image_data)}")
                    
                    # Fix: Use 'is not None' instead of truthiness check for NumPy arrays
                    if image_data is not None:
                        self.logger.debug(f"Image captured successfully: {image_data.shape}")
                        
                        # Get current GPS data
                        gps_data = self.gps.get_current_position()
                        self.logger.debug(f"GPS data retrieved: {type(gps_data)}")
                        
                        # Process and save image
                        self.logger.debug("Processing image...")
                        await self.processor.process_image(
                            image_data, gps_data, current_time
                        )
                        self.logger.debug("Image processing complete")
                        
                        self.stats['images_captured'] += 1
                        
                        # Update next capture time
                        next_capture += frame_interval
                        
                        # Prevent drift by checking if we're behind
                        if next_capture < current_time:
                            next_capture = current_time + frame_interval
                    
                    else:
                        self.logger.warning("Failed to capture image - camera returned None")
                        self.stats['errors'] += 1
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                import traceback
                self.logger.debug(f"Capture loop traceback: {traceback.format_exc()}")
                self.stats['errors'] += 1
                await asyncio.sleep(0.1)"""

    new_loop = """    async def _capture_loop(self):
        \"\"\"Main image capture loop with detailed debugging.\"\"\"
        frame_interval = 1.0 / self.config.capture_fps
        next_capture = time.time()
        
        self.logger.info(f"[DEBUG] Starting capture loop with {self.config.capture_fps} FPS")
        
        while self.running and self.capture_active:
            try:
                self.logger.debug("[DEBUG] Loop iteration start")
                current_time = time.time()
                
                if current_time >= next_capture:
                    self.logger.info("[DEBUG] Time for capture")
                    
                    # Step 1: Capture image
                    self.logger.info("[DEBUG] About to call camera.capture_image()")
                    image_data = self.camera.capture_image()
                    self.logger.info(f"[DEBUG] Camera returned: type={type(image_data)}")
                    
                    # Step 2: Check image data (this is where error likely occurs)
                    self.logger.info("[DEBUG] About to check image_data is not None")
                    if image_data is not None:
                        self.logger.info(f"[DEBUG] Image OK: shape={image_data.shape if hasattr(image_data, 'shape') else 'no shape'}")
                        
                        # Step 3: Get GPS data
                        self.logger.info("[DEBUG] About to get GPS data")
                        gps_data = self.gps.get_current_position()
                        self.logger.info(f"[DEBUG] GPS data: type={type(gps_data)}")
                        
                        # Step 4: Process image (another potential error location)
                        self.logger.info("[DEBUG] About to process image")
                        try:
                            await self.processor.process_image(
                                image_data, gps_data, current_time
                            )
                            self.logger.info("[DEBUG] Image processing complete")
                        except Exception as process_error:
                            self.logger.error(f"[DEBUG] Error in process_image: {process_error}")
                            import traceback
                            self.logger.error(f"[DEBUG] Process traceback: {traceback.format_exc()}")
                            raise process_error
                        
                        self.stats['images_captured'] += 1
                        
                        # Update next capture time
                        next_capture += frame_interval
                        
                        # Prevent drift by checking if we're behind
                        if next_capture < current_time:
                            next_capture = current_time + frame_interval
                    
                    else:
                        self.logger.warning("[DEBUG] Camera returned None")
                        self.stats['errors'] += 1
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"[DEBUG] Error in capture loop: {e}")
                import traceback
                tb_str = traceback.format_exc()
                self.logger.error(f"[DEBUG] Full traceback: {tb_str}")
                
                # Try to identify the exact line causing the issue
                tb_lines = tb_str.split('\\n')
                for line in tb_lines:
                    if 'bathycat_imager.py' in line or 'camera_controller.py' in line or 'image_processor.py' in line:
                        self.logger.error(f"[DEBUG] Problem line: {line}")
                
                self.stats['errors'] += 1
                await asyncio.sleep(0.1)"""

    # Replace the content
    new_content = content.replace(old_loop, new_loop)
    
    if new_content == content:
        print("Error: Could not find capture loop to replace")
        return False
    
    # Write the new content
    with open(bathycat_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Added detailed debugging to capture loop")
    print(f"✅ Backup saved to: {backup_file}")
    return True

def main():
    print("Advanced NumPy Boolean Debug Tool")
    print("=" * 40)
    
    if add_detailed_debugging():
        print()
        print("Debug version created successfully!")
        print()
        print("Next steps:")
        print("1. Push this debug version to your Pi")
        print("2. Run: ./scripts/start_capture.sh")
        print("3. Check the logs for '[DEBUG]' entries to see exactly where it fails")
        print("4. The error should now show the exact line and context")
        print()
        print("To restore original:")
        print("cp src/bathycat_imager.py.debug_backup src/bathycat_imager.py")
    else:
        print("❌ Failed to add debugging")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
