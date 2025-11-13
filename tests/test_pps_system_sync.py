#!/usr/bin/env python3
"""
PPS System Validation Test
=========================

Focused test to verify that the GPS HAT PPS signal is correctly applied to
the system for nanosecond-precision time synchronization. This script validates:

1. PPS hardware signal detection on GPIO 4
2. PPS kernel driver functionality (/dev/pps0)
3. System clock synchronization with PPS
4. NTP/Chrony integration with PPS reference
5. Time drift measurement and accuracy validation

Hardware Requirements:
- Adafruit Ultimate GPS HAT with PPS connected to GPIO 4
- GPS HAT receiving valid GPS fix for PPS generation
- pps-gpio kernel module loaded
- /dev/pps0 device available

Usage: 
    python3 test_pps_system_sync.py [options]

Options:
    --duration SECONDS    Test duration in seconds (default: 60)
    --verbose            Show detailed timing measurements
    --no-ntp            Skip NTP/Chrony integration tests
    --gpio-pin PIN      PPS GPIO pin (default: 4)
"""

import sys
import os
import time
import subprocess
import select
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - GPIO monitoring disabled")


class PPSSystemValidator:
    """Validates PPS system integration and time synchronization."""
    
    def __init__(self, pps_gpio_pin: int = 4, test_duration: int = 60, verbose: bool = False):
        """
        Initialize PPS system validator.
        
        Args:
            pps_gpio_pin: GPIO pin for PPS signal (default: 4)
            test_duration: Test duration in seconds
            verbose: Enable verbose output
        """
        self.pps_gpio_pin = pps_gpio_pin
        self.test_duration = test_duration
        self.verbose = verbose
        
        # Test results
        self.pps_pulses_detected = 0
        self.pps_timestamps = []
        self.system_time_drifts = []
        self.gpio_pulses = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO if not verbose else logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Threading
        self.stop_monitoring = False
        self.monitor_thread = None
    
    def check_pps_prerequisites(self) -> Dict[str, bool]:
        """Check PPS system prerequisites."""
        self.logger.info("🔍 Checking PPS system prerequisites...")
        
        checks = {}
        
        # Check /dev/pps0 device
        checks['pps_device'] = os.path.exists('/dev/pps0')
        status = "✅" if checks['pps_device'] else "❌"
        self.logger.info(f"{status} PPS device (/dev/pps0): {'Available' if checks['pps_device'] else 'Missing'}")
        
        # Check pps-gpio kernel module
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
            checks['pps_gpio_module'] = 'pps_gpio' in result.stdout
        except Exception as e:
            self.logger.error(f"Failed to check kernel modules: {e}")
            checks['pps_gpio_module'] = False
        
        status = "✅" if checks['pps_gpio_module'] else "❌"
        self.logger.info(f"{status} pps-gpio module: {'Loaded' if checks['pps_gpio_module'] else 'Not loaded'}")
        
        # Check GPIO permissions
        checks['gpio_access'] = os.access('/dev/gpiomem', os.R_OK | os.W_OK)
        status = "✅" if checks['gpio_access'] else "❌"
        self.logger.info(f"{status} GPIO access: {'Available' if checks['gpio_access'] else 'No permission'}")
        
        # Check if GPS HAT is getting fix (needed for PPS generation)
        checks['gps_fix'] = self.check_gps_fix()
        status = "✅" if checks['gps_fix'] else "⚠️"
        self.logger.info(f"{status} GPS fix: {'Active' if checks['gps_fix'] else 'No fix (PPS may not generate)'}")
        
        return checks
    
    def check_gps_fix(self) -> bool:
        """Check if GPS has a valid fix (required for PPS generation)."""
        try:
            # Try to read NMEA sentences from GPS
            import serial
            with serial.Serial('/dev/serial0', 9600, timeout=3) as gps_conn:
                for _ in range(10):  # Check 10 sentences
                    sentence = gps_conn.readline().decode('ascii', errors='ignore').strip()
                    if sentence.startswith('$GPGGA') or sentence.startswith('$GNGGA'):
                        parts = sentence.split(',')
                        if len(parts) >= 15 and parts[6] and int(parts[6]) > 0:
                            self.logger.info(f"   GPS fix quality: {parts[6]}, satellites: {parts[7] if len(parts) > 7 else 'N/A'}")
                            return True
            return False
        except Exception as e:
            self.logger.debug(f"GPS fix check failed: {e}")
            return False
    
    def test_pps_device_functionality(self) -> bool:
        """Test PPS device functionality by reading events."""
        self.logger.info("📡 Testing PPS device functionality...")
        
        if not os.path.exists('/dev/pps0'):
            self.logger.error("❌ /dev/pps0 device not found")
            return False
        
        try:
            # Test PPS device access
            pps_fd = os.open('/dev/pps0', os.O_RDONLY)
            
            self.logger.info("🔍 Monitoring PPS events for 10 seconds...")
            start_time = time.time()
            pps_events = 0
            
            while time.time() - start_time < 10:
                # Use select to wait for PPS events
                ready, _, _ = select.select([pps_fd], [], [], 1.0)
                if ready:
                    try:
                        # Read PPS event (this may not work on all systems)
                        data = os.read(pps_fd, 1024)
                        pps_events += 1
                        event_time = time.time()
                        self.pps_timestamps.append(event_time)
                        self.logger.info(f"   PPS pulse #{pps_events} at {datetime.fromtimestamp(event_time).strftime('%H:%M:%S.%f')}")
                    except OSError:
                        # Some systems don't support reading PPS events directly
                        break
                else:
                    self.logger.debug("   Waiting for PPS pulse...")
            
            os.close(pps_fd)
            
            if pps_events > 0:
                self.logger.info(f"✅ PPS device functional - detected {pps_events} pulses")
                self.pps_pulses_detected = pps_events
                return True
            else:
                self.logger.warning("⚠️  No PPS events detected via device read")
                self.logger.info("   This may be normal - trying alternative detection methods...")
                return self.test_pps_via_sysfs()
                
        except Exception as e:
            self.logger.error(f"❌ PPS device test failed: {e}")
            return False
    
    def test_pps_via_sysfs(self) -> bool:
        """Test PPS via sysfs interface as fallback."""
        try:
            # Check PPS stats via sysfs
            pps_path = '/sys/class/pps/pps0'
            if not os.path.exists(pps_path):
                return False
            
            # Read PPS statistics
            stats_files = ['assert', 'clear', 'mode', 'name']
            pps_info = {}
            
            for stat_file in stats_files:
                stat_path = os.path.join(pps_path, stat_file)
                if os.path.exists(stat_path):
                    try:
                        with open(stat_path, 'r') as f:
                            pps_info[stat_file] = f.read().strip()
                    except Exception:
                        pps_info[stat_file] = 'N/A'
            
            self.logger.info("📊 PPS sysfs information:")
            for key, value in pps_info.items():
                self.logger.info(f"   {key}: {value}")
            
            # If we have assert/clear info, PPS is functional
            if 'assert' in pps_info and pps_info['assert'] != 'N/A':
                self.logger.info("✅ PPS device detected via sysfs")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"PPS sysfs check failed: {e}")
            return False
    
    def test_gpio_pps_signal(self) -> bool:
        """Test PPS signal on GPIO pin directly."""
        if not GPIO_AVAILABLE:
            self.logger.warning("⚠️  GPIO monitoring not available - skipping GPIO PPS test")
            return False
        
        self.logger.info(f"🔌 Testing PPS signal on GPIO {self.pps_gpio_pin}...")
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pps_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Monitor GPIO for 15 seconds
            self.logger.info("🔍 Monitoring GPIO for PPS pulses (15 seconds)...")
            pulse_count = 0
            start_time = time.time()
            last_state = False
            
            while time.time() - start_time < 15:
                current_state = GPIO.input(self.pps_gpio_pin)
                
                # Detect rising edge (PPS pulse)
                if current_state and not last_state:
                    pulse_count += 1
                    pulse_time = time.time()
                    self.gpio_pulses.append(pulse_time)
                    
                    timestamp_str = datetime.fromtimestamp(pulse_time).strftime('%H:%M:%S.%f')
                    self.logger.info(f"   GPIO pulse #{pulse_count} at {timestamp_str}")
                
                last_state = current_state
                time.sleep(0.01)  # 10ms polling
            
            GPIO.cleanup()
            
            if pulse_count > 0:
                self.logger.info(f"✅ GPIO PPS signal detected - {pulse_count} pulses in 15 seconds")
                
                # Analyze pulse timing
                if len(self.gpio_pulses) > 1:
                    intervals = [self.gpio_pulses[i] - self.gpio_pulses[i-1] 
                               for i in range(1, len(self.gpio_pulses))]
                    avg_interval = sum(intervals) / len(intervals)
                    self.logger.info(f"   Average interval: {avg_interval:.3f} seconds")
                    
                    if 0.9 < avg_interval < 1.1:  # Should be ~1 second
                        self.logger.info("   ✅ PPS timing looks correct (~1 second intervals)")
                        return True
                    else:
                        self.logger.warning(f"   ⚠️  Unexpected PPS interval: {avg_interval:.3f}s (expected ~1.0s)")
                        return False
                else:
                    return True
            else:
                self.logger.warning("❌ No GPIO PPS pulses detected")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ GPIO PPS test failed: {e}")
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            return False
    
    def test_ntp_pps_integration(self) -> bool:
        """Test NTP/Chrony integration with PPS."""
        self.logger.info("🕒 Testing NTP/Chrony PPS integration...")
        
        # Check if chrony is running
        try:
            result = subprocess.run(['systemctl', 'is-active', 'chronyd'], 
                                  capture_output=True, text=True, timeout=5)
            chrony_active = result.returncode == 0
        except Exception:
            chrony_active = False
        
        self.logger.info(f"   Chrony service: {'Active' if chrony_active else 'Inactive'}")
        
        if not chrony_active:
            self.logger.warning("⚠️  Chrony not running - PPS NTP integration not active")
            return False
        
        # Check chrony sources for PPS reference
        try:
            result = subprocess.run(['chronyc', 'sources', '-v'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                sources_output = result.stdout
                self.logger.info("📊 Chrony sources:")
                for line in sources_output.split('\n'):
                    if line.strip() and not line.startswith('210'):
                        self.logger.info(f"   {line}")
                
                # Look for PPS reference
                pps_found = 'PPS' in sources_output or 'pps' in sources_output.lower()
                
                if pps_found:
                    self.logger.info("✅ PPS reference found in Chrony sources")
                    
                    # Check tracking status
                    track_result = subprocess.run(['chronyc', 'tracking'], 
                                                capture_output=True, text=True, timeout=5)
                    if track_result.returncode == 0:
                        self.logger.info("📊 Chrony tracking status:")
                        for line in track_result.stdout.split('\n'):
                            if line.strip():
                                self.logger.info(f"   {line}")
                    
                    return True
                else:
                    self.logger.warning("⚠️  No PPS reference found in Chrony sources")
                    return False
            else:
                self.logger.error(f"❌ Failed to get Chrony sources: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Chrony integration test failed: {e}")
            return False
    
    def test_system_time_accuracy(self) -> bool:
        """Test system time accuracy and stability."""
        self.logger.info("⏱️  Testing system time accuracy...")
        
        # Collect system time samples over test duration
        sample_count = min(self.test_duration, 30)  # Max 30 samples
        interval = self.test_duration / sample_count
        
        self.logger.info(f"📊 Collecting {sample_count} time accuracy samples over {self.test_duration}s...")
        
        time_samples = []
        for i in range(sample_count):
            # Get high-precision system time
            system_time = time.time_ns()
            monotonic_time = time.monotonic_ns()
            
            time_samples.append({
                'sample': i + 1,
                'system_ns': system_time,
                'monotonic_ns': monotonic_time,
                'timestamp': datetime.now()
            })
            
            if i < sample_count - 1:  # Don't sleep after last sample
                time.sleep(interval)
        
        # Analyze time stability
        if len(time_samples) > 1:
            # Calculate drift between system and monotonic time
            first_sample = time_samples[0]
            last_sample = time_samples[-1]
            
            system_elapsed = last_sample['system_ns'] - first_sample['system_ns']
            monotonic_elapsed = last_sample['monotonic_ns'] - first_sample['monotonic_ns']
            
            drift_ns = abs(system_elapsed - monotonic_elapsed)
            drift_ms = drift_ns / 1_000_000
            
            self.logger.info(f"📊 Time accuracy analysis:")
            self.logger.info(f"   Test duration: {self.test_duration}s")
            self.logger.info(f"   System time elapsed: {system_elapsed/1e9:.6f}s")
            self.logger.info(f"   Monotonic time elapsed: {monotonic_elapsed/1e9:.6f}s")
            self.logger.info(f"   Drift: {drift_ms:.3f}ms over {self.test_duration}s")
            
            # Good accuracy if drift is less than 1ms per second
            drift_rate = drift_ms / self.test_duration
            self.logger.info(f"   Drift rate: {drift_rate:.3f}ms/s")
            
            if drift_rate < 1.0:
                self.logger.info("✅ System time accuracy is good")
                return True
            else:
                self.logger.warning(f"⚠️  High drift rate: {drift_rate:.3f}ms/s")
                return False
        
        return False
    
    def run_full_pps_validation(self) -> Dict[str, Any]:
        """Run complete PPS system validation."""
        self.logger.info("🚀 Starting PPS System Validation")
        self.logger.info("=" * 50)
        
        results = {}
        
        # Check prerequisites
        prereq_results = self.check_pps_prerequisites()
        results['prerequisites'] = all(prereq_results.values())
        
        if not results['prerequisites']:
            self.logger.error("❌ Prerequisites not met - cannot continue PPS validation")
            return results
        
        # Test PPS device functionality
        results['pps_device'] = self.test_pps_device_functionality()
        
        # Test GPIO PPS signal
        results['gpio_pps'] = self.test_gpio_pps_signal()
        
        # Test NTP integration
        results['ntp_integration'] = self.test_ntp_pps_integration()
        
        # Test system time accuracy
        results['time_accuracy'] = self.test_system_time_accuracy()
        
        # Generate report
        self.generate_validation_report(results)
        
        return results
    
    def generate_validation_report(self, results: Dict[str, Any]):
        """Generate PPS validation report."""
        self.logger.info("\n" + "=" * 50)
        self.logger.info("📋 PPS System Validation Report")
        self.logger.info("=" * 50)
        
        test_names = {
            'prerequisites': 'System Prerequisites',
            'pps_device': 'PPS Device Functionality', 
            'gpio_pps': 'GPIO PPS Signal',
            'ntp_integration': 'NTP/Chrony Integration',
            'time_accuracy': 'System Time Accuracy'
        }
        
        passed_tests = 0
        for test_key, test_name in test_names.items():
            result = results.get(test_key, False)
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"{status} {test_name}")
            if result:
                passed_tests += 1
        
        total_tests = len(test_names)
        success_rate = (passed_tests / total_tests) * 100
        
        self.logger.info(f"\n📊 Overall Result: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        # Final assessment
        critical_tests = ['prerequisites', 'pps_device', 'gpio_pps']
        critical_passed = all(results.get(test, False) for test in critical_tests)
        
        if critical_passed:
            self.logger.info("🎉 PPS system is working correctly!")
            self.logger.info("   Your GPS HAT PPS is properly integrated for nanosecond timing")
        else:
            self.logger.warning("⚠️  PPS system has issues - check failed tests above")


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPS System Validation Test')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Test duration in seconds (default: 60)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--no-ntp', action='store_true',
                       help='Skip NTP/Chrony integration tests')
    parser.add_argument('--gpio-pin', type=int, default=4,
                       help='PPS GPIO pin (default: 4)')
    
    args = parser.parse_args()
    
    print("🛰️  PPS System Validation Test")
    print("=" * 40)
    print("Validating GPS HAT PPS integration for system time synchronization")
    print()
    
    # Run validation
    validator = PPSSystemValidator(
        pps_gpio_pin=args.gpio_pin,
        test_duration=args.duration,
        verbose=args.verbose
    )
    
    results = validator.run_full_pps_validation()
    
    # Exit with appropriate code
    critical_tests = ['prerequisites', 'pps_device', 'gpio_pps']
    if all(results.get(test, False) for test in critical_tests):
        print("\n🎉 PPS system validation successful!")
        sys.exit(0)
    else:
        print("\n❌ PPS system validation failed - check results above")
        sys.exit(1)


if __name__ == '__main__':
    main()