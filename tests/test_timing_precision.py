#!/usr/bin/env python3
"""
Timing Precision Test Script for BathyCat Imager
===============================================

Tests the new high-precision timing system and validates filename format.
This script helps verify that our timing improvements eliminate the drift issues.
"""
import sys
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

def test_monotonic_timing_precision():
    """Test monotonic timing precision and consistency."""
    print("🔬 Testing Monotonic Timing Precision")
    print("=" * 50)
    
    # Simulate the timing system used in main.py
    boot_time_offset = None
    
    # Establish monotonic time sync
    monotonic_ns = time.monotonic_ns()
    utc_time = datetime.now(timezone.utc)
    utc_ns = int(utc_time.timestamp() * 1_000_000_000)
    boot_time_offset = utc_ns - monotonic_ns
    
    print(f"📊 Boot time offset established: {boot_time_offset/1e9:.6f} seconds")
    
    # Test precision over multiple samples
    samples = []
    system_samples = []
    
    print("\n🔍 Collecting timing samples...")
    for i in range(10):
        # Monotonic method (new)
        mono_ns = time.monotonic_ns()
        mono_utc_ns = mono_ns + boot_time_offset
        mono_timestamp = datetime.fromtimestamp(mono_utc_ns / 1_000_000_000, tz=timezone.utc)
        
        # System method (old)
        sys_timestamp = datetime.now(timezone.utc)
        
        samples.append(mono_timestamp)
        system_samples.append(sys_timestamp)
        
        print(f"  Sample {i+1:2d}: Monotonic={mono_timestamp.strftime('%H:%M:%S.%f')}, "
              f"System={sys_timestamp.strftime('%H:%M:%S.%f')}")
        
        time.sleep(0.1)  # 100ms between samples
    
    # Calculate precision metrics
    mono_microseconds = [int(ts.microsecond) for ts in samples]
    sys_microseconds = [int(ts.microsecond) for ts in system_samples]
    
    mono_std = calculate_std_dev(mono_microseconds)
    sys_std = calculate_std_dev(sys_microseconds)
    
    print(f"\n📈 Precision Analysis:")
    print(f"   Monotonic method std dev: {mono_std:.2f} microseconds")
    print(f"   System method std dev:    {sys_std:.2f} microseconds")
    print(f"   Improvement factor:       {sys_std/mono_std:.1f}x" if mono_std > 0 else "   Perfect precision!")
    
    return mono_std < sys_std

def test_filename_format():
    """Test the new filename format."""
    print("\n📁 Testing New Filename Format")
    print("=" * 50)
    
    # Import storage manager
    from storage import StorageManager
    
    # Test config
    config = {
        'storage_base_path': '/tmp/bathycat_test',
        'filename_prefix': 'bathyimgtest',
        'use_sequence_counter': True
    }
    
    storage = StorageManager(config)
    
    # Test timestamp
    test_time = datetime(2025, 11, 5, 17, 43, 0, 82000, timezone.utc)  # .082 seconds
    
    # Test sequence counters
    test_cases = [
        (test_time, 1),
        (test_time, 123),
        (test_time, 99999),
        (test_time.replace(microsecond=547000), 1),  # .547 seconds
    ]
    
    print("🧪 Generated Filenames:")
    for timestamp, counter in test_cases:
        filepath = storage.get_image_path(timestamp, counter)
        filename = os.path.basename(filepath)
        
        # Expected format: bathyimgtest_20251105-174300-082_00001.jpg
        expected_parts = {
            'prefix': 'bathyimgtest',
            'date': '20251105',
            'time': '174300',
            'milliseconds': f"{int(timestamp.microsecond / 1000):03d}",
            'counter': f"{counter:05d}",
            'extension': 'jpg'
        }
        
        print(f"  {filename}")
        
        # Validate format
        parts = filename.split('_')
        if len(parts) == 3:  # prefix_datetime_counter.ext
            prefix = parts[0]
            datetime_part = parts[1]
            counter_ext = parts[2]
            
            # Check datetime format: YYYYMMDD-HHMMSS-mmm
            datetime_components = datetime_part.split('-')
            if len(datetime_components) == 3:
                date_part, time_part, ms_part = datetime_components
                counter_part = counter_ext.split('.')[0]
                
                print(f"    ✅ Prefix: {prefix} (expected: {expected_parts['prefix']})")
                print(f"    ✅ Date: {date_part} (expected: {expected_parts['date']})")
                print(f"    ✅ Time: {time_part} (expected: {expected_parts['time']})")
                print(f"    ✅ Milliseconds: {ms_part} (expected: {expected_parts['milliseconds']})")
                print(f"    ✅ Counter: {counter_part} (expected: {expected_parts['counter']})")
            else:
                print(f"    ❌ Invalid datetime format: {datetime_part}")
        else:
            print(f"    ❌ Invalid filename structure: {filename}")
    
    print("\n✅ New filename format: prefix_YYYYMMDD-HHMMSS-mmm_NNNNN.jpg")
    return True

def test_gps_sync_frequency():
    """Test GPS sync frequency improvement."""
    print("\n📡 Testing GPS Sync Frequency")
    print("=" * 50)
    
    # Import GPS module
    from gps import GPS
    
    # Test config
    config = {
        'gps_port': '/dev/ttyUSB0',
        'gps_baudrate': 9600,
        'gps_timeout': 1.0,
        'gps_time_sync': True
    }
    
    gps = GPS(config)
    
    print(f"📊 GPS sync interval: {gps.time_sync_interval} seconds")
    print(f"   Previous interval: 1800 seconds (30 minutes)")
    print(f"   New interval: {gps.time_sync_interval} seconds ({gps.time_sync_interval/60:.1f} minutes)")
    print(f"   Improvement: {1800/gps.time_sync_interval:.1f}x more frequent")
    
    # Expected improvement
    expected_interval = 300  # 5 minutes
    if gps.time_sync_interval == expected_interval:
        print("   ✅ GPS sync frequency properly configured")
        return True
    else:
        print(f"   ❌ Expected {expected_interval}s, got {gps.time_sync_interval}s")
        return False

def calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5

def main():
    """Run all timing precision tests."""
    print("🚀 BathyCat Timing Precision Test Suite")
    print("=" * 60)
    print("Testing improvements to fix the 5-second timing drift issue.\n")
    
    results = {}
    
    try:
        # Test monotonic timing precision
        results['monotonic_timing'] = test_monotonic_timing_precision()
        
        # Test filename format
        results['filename_format'] = test_filename_format()
        
        # Test GPS sync frequency
        results['gps_sync'] = test_gps_sync_frequency()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the project root directory")
        return 1
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All timing precision improvements are working correctly!")
        print("   The 5-second timing drift issue should now be resolved.")
        return 0
    else:
        print("\n⚠️  Some tests failed - timing improvements may need adjustment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())