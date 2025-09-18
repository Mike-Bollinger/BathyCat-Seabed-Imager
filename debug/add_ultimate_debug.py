#!/usr/bin/env python3
"""
Ultimate NumPy Boolean Debug Tool
================================

This script adds comprehensive line-by-line debugging with stack traces
to identify exactly where the NumPy boolean evaluation error is occurring.
"""

import traceback
import sys
from pathlib import Path


def add_ultimate_debugging():
    """Add comprehensive debugging to all potential problem areas."""
    
    bathycat_file = Path("src/bathycat_imager.py")
    
    if not bathycat_file.exists():
        print("Error: src/bathycat_imager.py not found")
        return False
    
    # Read current content
    with open(bathycat_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = f"src/bathycat_imager.py.ultimate_debug_backup"
    with open(backup_file, 'w') as f:
        f.write(content)
    
    # Replace the capture loop with an ultra-detailed debug version
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
        \"\"\"Main image capture loop with ULTIMATE debugging.\"\"\"
        frame_interval = 1.0 / self.config.capture_fps
        next_capture = time.time()
        
        self.logger.error(f"[ULTIMATE] Starting capture loop with {self.config.capture_fps} FPS")
        
        while self.running and self.capture_active:
            try:
                self.logger.error("[ULTIMATE] === LOOP ITERATION START ===")
                current_time = time.time()
                
                if current_time >= next_capture:
                    self.logger.error("[ULTIMATE] Time for capture")
                    
                    # Step 1: Capture image - MOST DETAILED
                    self.logger.error("[ULTIMATE] STEP 1: About to call camera.capture_image()")
                    try:
                        image_data = self.camera.capture_image()
                        self.logger.error(f"[ULTIMATE] STEP 1 RESULT: type={type(image_data)}, shape={getattr(image_data, 'shape', 'NO_SHAPE')}")
                    except Exception as cam_error:
                        self.logger.error(f"[ULTIMATE] STEP 1 ERROR: {cam_error}")
                        import traceback
                        self.logger.error(f"[ULTIMATE] STEP 1 TRACEBACK: {traceback.format_exc()}")
                        raise cam_error
                    
                    # Step 2: Check image data - MOST DETAILED
                    self.logger.error("[ULTIMATE] STEP 2: About to check 'image_data is not None'")
                    try:
                        is_not_none = (image_data is not None)
                        self.logger.error(f"[ULTIMATE] STEP 2 RESULT: is_not_none={is_not_none}")
                    except Exception as check_error:
                        self.logger.error(f"[ULTIMATE] STEP 2 ERROR: {check_error}")
                        import traceback
                        self.logger.error(f"[ULTIMATE] STEP 2 TRACEBACK: {traceback.format_exc()}")
                        raise check_error
                    
                    if image_data is not None:
                        self.logger.error(f"[ULTIMATE] STEP 3: Image OK, getting shape...")
                        try:
                            shape_info = image_data.shape if hasattr(image_data, 'shape') else 'no shape'
                            self.logger.error(f"[ULTIMATE] STEP 3 RESULT: shape={shape_info}")
                        except Exception as shape_error:
                            self.logger.error(f"[ULTIMATE] STEP 3 ERROR: {shape_error}")
                            import traceback
                            self.logger.error(f"[ULTIMATE] STEP 3 TRACEBACK: {traceback.format_exc()}")
                            raise shape_error
                        
                        # Step 4: Get GPS data - MOST DETAILED
                        self.logger.error("[ULTIMATE] STEP 4: About to call gps.get_current_position()")
                        try:
                            gps_data = self.gps.get_current_position()
                            self.logger.error(f"[ULTIMATE] STEP 4 RESULT: type={type(gps_data)}")
                        except Exception as gps_error:
                            self.logger.error(f"[ULTIMATE] STEP 4 ERROR: {gps_error}")
                            import traceback
                            self.logger.error(f"[ULTIMATE] STEP 4 TRACEBACK: {traceback.format_exc()}")
                            raise gps_error
                        
                        # Step 5: Process image - MOST DETAILED
                        self.logger.error("[ULTIMATE] STEP 5: About to call processor.process_image()")
                        try:
                            await self.processor.process_image(
                                image_data, gps_data, current_time
                            )
                            self.logger.error("[ULTIMATE] STEP 5 RESULT: Image processing complete")
                        except Exception as process_error:
                            self.logger.error(f"[ULTIMATE] STEP 5 ERROR: {process_error}")
                            import traceback
                            tb_str = traceback.format_exc()
                            self.logger.error(f"[ULTIMATE] STEP 5 TRACEBACK: {tb_str}")
                            
                            # Analyze the traceback line by line
                            tb_lines = tb_str.split('\\n')
                            for i, line in enumerate(tb_lines):
                                if 'bathycat' in line.lower() or 'image_processor' in line or 'camera_controller' in line or 'gps_controller' in line:
                                    self.logger.error(f"[ULTIMATE] PROBLEM LINE {i}: {line}")
                            
                            raise process_error
                        
                        self.stats['images_captured'] += 1
                        
                        # Update next capture time
                        next_capture += frame_interval
                        
                        # Prevent drift by checking if we're behind
                        if next_capture < current_time:
                            next_capture = current_time + frame_interval
                    
                    else:
                        self.logger.error("[ULTIMATE] Camera returned None")
                        self.stats['errors'] += 1
                
                # Short sleep to prevent CPU spinning
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"[ULTIMATE] MAIN LOOP ERROR: {e}")
                import traceback
                tb_str = traceback.format_exc()
                self.logger.error(f"[ULTIMATE] MAIN LOOP TRACEBACK: {tb_str}")
                
                # Find the exact problematic line
                tb_lines = tb_str.split('\\n')
                for i, line in enumerate(tb_lines):
                    if ('bathycat' in line.lower() or 
                        'image_processor' in line or 
                        'camera_controller' in line or 
                        'gps_controller' in line or
                        'truth value' in line.lower() or
                        'ambiguous' in line.lower()):
                        self.logger.error(f"[ULTIMATE] CRITICAL LINE {i}: {line}")
                
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
    
    print("✅ Added ULTIMATE debugging to capture loop")
    print(f"✅ Backup saved to: {backup_file}")
    return True


def main():
    print("Ultimate NumPy Boolean Debug Tool")
    print("=" * 50)
    print()
    print("This will add EXTREMELY VERBOSE debugging that logs")
    print("every single step in the capture loop to identify")
    print("exactly where the NumPy boolean evaluation error occurs.")
    print()
    
    if add_ultimate_debugging():
        print()
        print("🔥 ULTIMATE DEBUG VERSION CREATED! 🔥")
        print()
        print("WARNING: This will generate A LOT of log output!")
        print()
        print("Next steps:")
        print("1. Push this debug version to your Pi")
        print("2. Run manually: ./scripts/start_capture.sh")
        print("3. Look for '[ULTIMATE]' in the logs")
        print("4. The error will show EXACTLY which step fails")
        print("5. Send me the '[ULTIMATE]' log lines around the error")
        print()
        print("To restore original:")
        print("cp src/bathycat_imager.py.ultimate_debug_backup src/bathycat_imager.py")
        print()
        print("This debug version will pinpoint the EXACT source!")
    else:
        print("❌ Failed to add ultimate debugging")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
