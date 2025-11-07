#!/usr/bin/env python3
"""
GPS HAT and PPS Integration Test
===============================

Comprehensive test for Adafruit Ultimate GPS HAT with PPS timing integration.
Tests GPS HAT communication, PPS signal detection, and nanosecond timing accuracy.

Hardware Requirements:
- Adafruit Ultimate GPS HAT installed on Raspberry Pi
- GPS HAT configured with GPIO 4 PPS and /dev/ttyAMA0 UART
- PPS kernel module loaded and /dev/pps0 device available

Usage: python3 test_gps_hat_pps.py
"""

import sys
import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from gps import GPS, GPSError
    from pps_interface import GPSPPSInterface, PPSError
    from config import load_config
except ImportError as e:
    print(f"❌ Failed to import BathyCat modules: {e}")
    print("Make sure you're running from the BathyCat project directory")
    sys.exit(1)


class GPSHATTestSuite:
    """Comprehensive test suite for GPS HAT and PPS integration."""
    
    def __init__(self):
        """Initialize test suite."""
        self.logger = logging.getLogger(__name__)
        self.config = {}
        self.gps = None
        self.pps_interface = None
        self.test_results = {}
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def load_test_config(self) -> bool:
        """Load GPS HAT configuration for testing."""
        try:
            # Load BathyCat configuration
            self.config = load_config()
            
            # Ensure GPS HAT configuration is present
            gps_config_required = {
                'gps_port': '/dev/ttyAMA0',
                'pps_enabled': True,
                'pps_gpio_pin': 4,
                'pps_device': '/dev/pps0'
            }
            
            for key, expected_value in gps_config_required.items():
                if key not in self.config:
                    self.config[key] = expected_value
                    self.logger.warning(f"Added missing config: {key} = {expected_value}")
            
            self.logger.info("GPS HAT test configuration loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def test_hardware_detection(self) -> bool:
        """Test GPS HAT hardware detection."""
        self.logger.info("🔍 Testing GPS HAT hardware detection...")
        
        hardware_checks = {
            'uart_device': '/dev/ttyAMA0',
            'pps_device': '/dev/pps0',
            'gpio_mem': '/dev/gpiomem'
        }
        
        all_present = True
        
        for name, device_path in hardware_checks.items():
            if os.path.exists(device_path):
                self.logger.info(f"✅ {name}: {device_path} found")
            else:
                self.logger.error(f"❌ {name}: {device_path} not found")
                all_present = False
        
        # Check PPS module
        try:
            with open('/proc/modules', 'r') as f:
                modules = f.read()
                if 'pps_gpio' in modules:
                    self.logger.info("✅ pps-gpio kernel module loaded")
                else:
                    self.logger.error("❌ pps-gpio kernel module not loaded")
                    all_present = False
        except Exception as e:
            self.logger.error(f"❌ Failed to check kernel modules: {e}")
            all_present = False
        
        self.test_results['hardware_detection'] = all_present
        return all_present
    
    def test_pps_interface(self) -> bool:
        """Test PPS interface initialization and configuration."""
        self.logger.info("⚡ Testing PPS interface...")
        
        try:
            # Initialize PPS interface
            self.pps_interface = GPSPPSInterface(self.config)
            
            # Check PPS support
            pps_status = self.pps_interface.check_pps_support()
            
            self.logger.info(f"PPS device exists: {pps_status['pps_device_exists']}")
            self.logger.info(f"PPS module loaded: {pps_status['pps_module_loaded']}")
            self.logger.info(f"GPIO overlay enabled: {pps_status['gpio_overlay_enabled']}")
            self.logger.info(f"Hardware ready: {pps_status['hardware_ready']}")
            
            # Print configuration suggestions if needed
            if pps_status['config_suggestions']:
                self.logger.warning("PPS configuration suggestions:")
                for suggestion in pps_status['config_suggestions']:
                    self.logger.warning(f"  💡 {suggestion}")
            
            # Initialize PPS interface
            pps_initialized = self.pps_interface.initialize()
            
            if pps_initialized:
                self.logger.info("✅ PPS interface initialized successfully")
            else:
                self.logger.warning("⚠️  PPS interface initialization failed")
            
            self.test_results['pps_interface'] = pps_initialized
            return pps_initialized
            
        except Exception as e:
            self.logger.error(f"❌ PPS interface test failed: {e}")
            self.test_results['pps_interface'] = False
            return False
    
    def test_gps_connection(self) -> bool:
        """Test GPS HAT connection and communication."""
        self.logger.info("📡 Testing GPS HAT connection...")
        
        try:
            # Initialize GPS with HAT configuration
            self.gps = GPS(self.config)
            
            # Test connection
            if not self.gps.connect():
                self.logger.error("❌ Failed to connect to GPS HAT")
                self.test_results['gps_connection'] = False
                return False
            
            self.logger.info("✅ GPS HAT connection established")
            
            # Start reading GPS data
            if not self.gps.start_reading():
                self.logger.error("❌ Failed to start GPS reading")
                self.test_results['gps_connection'] = False
                return False
            
            self.logger.info("✅ GPS reading started")
            
            # Wait for GPS data and test fix acquisition
            self.logger.info("🛰️  Waiting for GPS fix (30 seconds)...")
            fix_acquired = False
            
            for i in range(30):
                time.sleep(1)
                fix = self.gps.get_current_fix()
                
                if fix and fix.is_valid:
                    self.logger.info(f"✅ GPS fix acquired!")
                    self.logger.info(f"   📍 Location: {fix.latitude:.6f}, {fix.longitude:.6f}")
                    self.logger.info(f"   🛰️  Satellites: {fix.satellites}")
                    self.logger.info(f"   📶 Quality: {fix.fix_quality}")
                    fix_acquired = True
                    break
                elif fix:
                    self.logger.info(f"   ⏳ Searching... Satellites: {fix.satellites}, Quality: {fix.fix_quality}")
                else:
                    self.logger.info(f"   ⏳ Waiting for GPS data... ({i+1}/30)")
            
            if not fix_acquired:
                self.logger.warning("⚠️  GPS fix not acquired within timeout")
                self.logger.warning("   This may be normal indoors or without clear sky view")
            
            self.test_results['gps_connection'] = True
            self.test_results['gps_fix_acquired'] = fix_acquired
            return True
            
        except Exception as e:
            self.logger.error(f"❌ GPS connection test failed: {e}")
            self.test_results['gps_connection'] = False
            return False
    
    def test_pps_timing(self) -> bool:
        """Test PPS timing accuracy and hardware timestamps."""
        self.logger.info("⏱️  Testing PPS timing and hardware timestamps...")
        
        if not self.pps_interface or not self.pps_interface.is_available:
            self.logger.warning("⚠️  PPS interface not available - skipping timing test")
            self.test_results['pps_timing'] = False
            return False
        
        try:
            # Test hardware timestamp acquisition
            timestamp_tests = []
            
            for i in range(10):
                hw_timestamp = self.pps_interface.get_hardware_timestamp()
                sw_timestamp = time.time_ns()
                
                if hw_timestamp is not None:
                    timestamp_tests.append({
                        'hardware': hw_timestamp,
                        'software': sw_timestamp,
                        'diff_ns': abs(hw_timestamp - sw_timestamp)
                    })
                    self.logger.info(f"   #{i+1}: HW timestamp available, diff: {abs(hw_timestamp - sw_timestamp)/1_000_000:.3f}ms")
                else:
                    self.logger.warning(f"   #{i+1}: Hardware timestamp not available")
                
                time.sleep(0.1)
            
            if timestamp_tests:
                avg_diff = sum(t['diff_ns'] for t in timestamp_tests) / len(timestamp_tests)
                max_diff = max(t['diff_ns'] for t in timestamp_tests)
                min_diff = min(t['diff_ns'] for t in timestamp_tests)
                
                self.logger.info(f"✅ Hardware timestamps available")
                self.logger.info(f"   📊 Average difference: {avg_diff/1_000_000:.3f}ms")
                self.logger.info(f"   📊 Max difference: {max_diff/1_000_000:.3f}ms")
                self.logger.info(f"   📊 Min difference: {min_diff/1_000_000:.3f}ms")
                
                # Consider timing successful if average difference is reasonable
                timing_good = avg_diff < 100_000_000  # Less than 100ms average difference
                
                self.test_results['pps_timing'] = timing_good
                return timing_good
            else:
                self.logger.warning("⚠️  No hardware timestamps available")
                self.test_results['pps_timing'] = False
                return False
            
        except Exception as e:
            self.logger.error(f"❌ PPS timing test failed: {e}")
            self.test_results['pps_timing'] = False
            return False
    
    def test_chrony_integration(self) -> bool:
        """Test Chrony NTP integration with GPS HAT."""
        self.logger.info("🕒 Testing Chrony NTP integration...")
        
        if not self.pps_interface:
            self.logger.warning("⚠️  PPS interface not available - skipping Chrony test")
            self.test_results['chrony_integration'] = False
            return False
        
        try:
            # Check Chrony configuration status
            chrony_status = self.pps_interface.configure_chrony_ntp()
            
            self.logger.info(f"Chrony installed: {chrony_status['chrony_installed']}")
            self.logger.info(f"Config exists: {chrony_status['config_exists']}")
            self.logger.info(f"PPS configured: {chrony_status['pps_configured']}")
            self.logger.info(f"Ready for NTP: {chrony_status['ready_for_ntp']}")
            
            # Print configuration suggestions
            if chrony_status['config_suggestions']:
                self.logger.info("Chrony configuration suggestions:")
                for suggestion in chrony_status['config_suggestions']:
                    self.logger.info(f"  💡 {suggestion}")
            
            chrony_ready = chrony_status['ready_for_ntp']
            self.test_results['chrony_integration'] = chrony_ready
            
            if chrony_ready:
                self.logger.info("✅ Chrony NTP integration ready")
            else:
                self.logger.warning("⚠️  Chrony NTP integration needs configuration")
            
            return chrony_ready
            
        except Exception as e:
            self.logger.error(f"❌ Chrony integration test failed: {e}")
            self.test_results['chrony_integration'] = False
            return False
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete GPS HAT and PPS test suite."""
        self.logger.info("🚀 Starting GPS HAT and PPS Integration Test Suite")
        self.logger.info("=" * 60)
        
        # Load configuration
        if not self.load_test_config():
            return {'success': False, 'error': 'Configuration loading failed'}
        
        # Run all tests
        tests = [
            ('Hardware Detection', self.test_hardware_detection),
            ('PPS Interface', self.test_pps_interface),
            ('GPS Connection', self.test_gps_connection),
            ('PPS Timing', self.test_pps_timing),
            ('Chrony Integration', self.test_chrony_integration)
        ]
        
        for test_name, test_func in tests:
            self.logger.info(f"\n🧪 Running {test_name} Test...")
            try:
                test_func()
            except Exception as e:
                self.logger.error(f"❌ {test_name} test failed with exception: {e}")
                self.test_results[test_name.lower().replace(' ', '_')] = False
        
        # Cleanup
        try:
            if self.gps:
                self.gps.disconnect()
            if self.pps_interface:
                self.pps_interface.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
        
        # Generate test report
        return self.generate_test_report()
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📋 GPS HAT and PPS Integration Test Report")
        self.logger.info("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"{status} {test_name.replace('_', ' ').title()}")
        
        self.logger.info(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        # Overall assessment
        critical_tests = ['hardware_detection', 'pps_interface', 'gps_connection']
        critical_passed = all(self.test_results.get(test, False) for test in critical_tests)
        
        if critical_passed:
            self.logger.info("🎉 GPS HAT integration is working correctly!")
        else:
            self.logger.warning("⚠️  GPS HAT integration has issues that need attention")
        
        return {
            'success': critical_passed,
            'test_results': self.test_results,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'success_rate': success_rate
        }


def main():
    """Main test function."""
    print("GPS HAT and PPS Integration Test")
    print("=" * 40)
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' not in cpuinfo:
                print("⚠️  Warning: Not running on Raspberry Pi - some tests may fail")
    except:
        print("⚠️  Warning: Could not detect Raspberry Pi - some tests may fail")
    
    # Run test suite
    test_suite = GPSHATTestSuite()
    results = test_suite.run_full_test_suite()
    
    # Exit with appropriate code
    if results['success']:
        print("\n🎉 All critical tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some critical tests failed - check logs above")
        sys.exit(1)


if __name__ == '__main__':
    main()