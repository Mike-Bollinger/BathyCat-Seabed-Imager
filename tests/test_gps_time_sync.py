#!/usr/bin/env python3
"""
GPS Time Sync Debug Test
========================

This script tests the GPS time sync functionality step by step to identify
exactly where the failure is occurring.
"""

import sys
import os
import json
import subprocess
import logging
from datetime import datetime, timezone
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def setup_logging():
    """Setup debug logging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_gps_script_direct():
    """Test the GPS time sync script directly"""
    print("\n=== DIRECT GPS SCRIPT TEST ===")
    
    script_path = "../scripts/gps_set_time.sh"
    if not os.path.exists(script_path):
        print(f"❌ GPS script not found: {script_path}")
        return False
        
    if not os.access(script_path, os.X_OK):
        print(f"❌ GPS script not executable: {script_path}")
        return False
        
    print(f"✅ GPS script found and executable: {script_path}")
    
    # Test with current time
    test_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Testing with time: {test_time} UTC")
    
    try:
        # Run the script with sudo
        cmd = ["sudo", script_path, test_time]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ GPS script test: SUCCESS")
            return True
        else:
            print("❌ GPS script test: FAILED")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ GPS script test: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ GPS script test: ERROR - {e}")
        return False

def test_gps_module():
    """Test the GPS module directly"""
    print("\n=== GPS MODULE TEST ===")
    
    try:
        from gps import GPS
        from config import BathyImagerConfig
        
        # Load config
        config = BathyImagerConfig("../config/bathyimager_config.json")
        print(f"✅ Config loaded")
        print(f"   GPS port: {config.gps_port}")
        print(f"   GPS time sync: {config.gps_time_sync}")
        
        # Create GPS instance
        logger = setup_logging()
        gps = GPS(config, logger)
        print(f"✅ GPS instance created")
        
        # Start GPS
        gps.start()
        print(f"✅ GPS started")
        
        # Wait for fix
        print("Waiting up to 30 seconds for GPS fix...")
        start_time = time.time()
        fix_obtained = False
        
        for i in range(30):
            if gps.has_fix():
                fix = gps.get_current_fix()
                if fix:
                    print(f"✅ GPS fix obtained after {i+1} seconds")
                    print(f"   Coordinates: {fix.latitude}, {fix.longitude}")
                    print(f"   GPS time: {fix.timestamp}")
                    print(f"   Satellites: {fix.satellites}")
                    fix_obtained = True
                    break
            time.sleep(1)
            print(f"   Waiting... ({i+1}/30)")
        
        if not fix_obtained:
            print("❌ No GPS fix obtained within 30 seconds")
            
        # Test time sync method directly
        if hasattr(gps, '_synchronize_system_time'):
            print("\n--- Testing time sync method directly ---")
            try:
                # Create a fake fix for testing time sync logic
                class TestFix:
                    def __init__(self):
                        self.timestamp = datetime.now(timezone.utc)
                
                test_fix = TestFix()
                print(f"Testing time sync with fake GPS time: {test_fix.timestamp}")
                
                # Call the private method directly for testing
                gps._synchronize_system_time(test_fix)
                print("✅ Time sync method completed (check logs for details)")
                
            except Exception as e:
                print(f"❌ Time sync method failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Stop GPS
        gps.stop()
        print("✅ GPS stopped")
        
        return fix_obtained
        
    except ImportError as e:
        print(f"❌ Failed to import GPS modules: {e}")
        return False
    except Exception as e:
        print(f"❌ GPS module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_system_permissions():
    """Test system permissions and configuration"""
    print("\n=== SYSTEM PERMISSIONS TEST ===")
    
    # Check sudo access
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        if result.returncode == 0:
            print("✅ Passwordless sudo available")
        else:
            print("❌ Passwordless sudo not available")
            print("   This may require manual password entry for time sync")
    except Exception as e:
        print(f"❌ Sudo test failed: {e}")
    
    # Check timedatectl
    try:
        result = subprocess.run(["timedatectl", "status"], capture_output=True, text=True)
        print(f"✅ Timedatectl available")
        print("Current time status:")
        for line in result.stdout.split('\n')[:8]:  # First 8 lines
            if line.strip():
                print(f"   {line}")
    except Exception as e:
        print(f"❌ Timedatectl test failed: {e}")
    
    # Check NTP status
    try:
        result = subprocess.run(["timedatectl", "status"], capture_output=True, text=True)
        if "NTP service: active" in result.stdout:
            print("⚠️  NTP service is active")
            print("   This may interfere with manual time setting")
            print("   GPS script should handle this automatically")
        else:
            print("✅ NTP service is not active")
    except Exception as e:
        print(f"❌ NTP status check failed: {e}")

def main():
    """Main test function"""
    print("🧪 GPS Time Sync Debug Test")
    print("============================")
    
    # Change to project directory if needed
    if os.path.basename(os.getcwd()) == "tests":
        os.chdir("..")
    
    print(f"Working directory: {os.getcwd()}")
    
    # Run all tests
    tests_passed = 0
    total_tests = 3
    
    if test_system_permissions():
        tests_passed += 1
        
    if test_gps_script_direct():
        tests_passed += 1
        
    if test_gps_module():
        tests_passed += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed!")
        print("\n💡 If GPS time sync is still failing in the service:")
        print("   • Check service logs: sudo journalctl -u bathyimager -f")
        print("   • Verify GPS device connection: lsusb | grep -i gps")
        print("   • Run service in debug mode: LOG_LEVEL=DEBUG ./run_bathyimager.sh")
    else:
        print("❌ Some tests failed!")
        print("\n🔧 Recommended fixes:")
        print("   • Run: sudo ./tests/fix_gps_time_sync.sh")
        print("   • Check GPS device connection")
        print("   • Verify script permissions")
    
    print(f"\n📊 Real-time monitoring:")
    print(f"   • GPS status: ./tests/quick_gps_check.py")
    print(f"   • Service logs: sudo journalctl -u bathyimager -f")
    print(f"   • Time sync test: sudo ./scripts/gps_set_time.sh \"$(date -u '+%Y-%m-%d %H:%M:%S')\"")

if __name__ == "__main__":
    main()